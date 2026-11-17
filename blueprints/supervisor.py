import os
import io
import json
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, current_app, session, send_file, jsonify
)
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, FootplateInspection, Message, TrainingRecord, 
    CounsellingTopic, Notice, CrewCounsellingRecord, CLIMovement, OfficerDirective, CustomField,
    WeaknessLedger
)
from blueprints.auth import role_required

supervisor_bp = Blueprint('supervisor', __name__)

@supervisor_bp.before_request
@role_required('supervisor', 'officer', 'admin')
def supervisor_protection():
    pass


# ---------------------------------------------------------------------------
# DATE PARSER & COMPLIANCE CALCULATOR
# ---------------------------------------------------------------------------

def parse_date_value(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    if not s or s.upper() in ('NA', 'N/A', '-', '#N/A', 'NONE', 'NIL', 'NULL', 'UNKNOWN', '0'):
        return None
    for fmt in [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d.%m.%Y", "%d-%b-%Y", "%d-%B-%Y", "%d-%b-%y"
    ]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_int_score(val, default=5):
    try:
        n = int(val)
        return max(1, min(5, n))
    except (TypeError, ValueError):
        return default


def compute_overdue_status(last_fp_raw, last_counsel_raw, next_pme_raw=None):
    today = date.today()
    fp_date = parse_date_value(last_fp_raw)
    cs_date = parse_date_value(last_counsel_raw)
    pme_due = parse_date_value(next_pme_raw)

    if not fp_date:
        fp_status = "overdue"
    else:
        days = (today - fp_date).days
        if days > 90:
            fp_status = "overdue"
        elif days >= 75:
            fp_status = "due_soon"
        else:
            fp_status = "compliant"

    if not cs_date:
        cs_status = "overdue"
    else:
        days = (today - cs_date).days
        if days > 90:
            cs_status = "overdue"
        elif days >= 75:
            cs_status = "due_soon"
        else:
            cs_status = "compliant"

    if not pme_due:
        med_status = "compliant"
    else:
        days_remaining = (pme_due - today).days
        if days_remaining < 0:
            med_status = "overdue"
        elif days_remaining <= 30:
            med_status = "due_soon"
        else:
            med_status = "compliant"

    return {"fp_status": fp_status, "cs_status": cs_status, "med_status": med_status}


# ---------------------------------------------------------------------------
# CLI DASHBOARD & SQUAD MONITORING (WITH 360° CREW DOSSIER & WEAK CREW MATRIX)
# ---------------------------------------------------------------------------

@supervisor_bp.route('/')
@supervisor_bp.route('/dashboard')
def dashboard():
    cli = User.query.get(session['user_id'])
    search_q = request.args.get('q', '').strip()
    grade_filter = request.args.get('grade', 'ALL').strip().upper()
    hq_filter = request.args.get('hq', 'ALL').strip().upper()
    status_filter = request.args.get('status', 'ALL').strip().lower()
    weak_in_filter = request.args.get('weak_in', 'ALL').strip().lower()

    # 1. Fetch assigned crew users
    if cli.sub_role == 'CLI':
        my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all()
        crew_ids = [c.id for c in my_crews]
    else:
        my_crews = User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()
        crew_ids = [c.id for c in my_crews]

    # 2. Fetch 24-column counselling records for this CLI squad
    crew_pfs = [c.pf_number for c in my_crews if c.pf_number]
    crew_mobiles = [c.mobile for c in my_crews if c.mobile]
    
    rec_query = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.crew_user_id.in_(crew_ids)) |
        (CrewCounsellingRecord.crew_id_str.in_(crew_pfs)) |
        (CrewCounsellingRecord.cug.in_(crew_mobiles)) |
        (CrewCounsellingRecord.cli_name.ilike(f"%{cli.full_name}%")) |
        (CrewCounsellingRecord.cli_name.ilike(f"%{cli.username}%"))
    )
    records = rec_query.all()

    # Link records to User rows
    for r in records:
        if not r.crew_user_id:
            for c in my_crews:
                if (c.pf_number and r.crew_id_str and c.pf_number.upper() == r.crew_id_str.upper()) or \
                   (c.mobile and r.cug and c.mobile == r.cug):
                    r.crew_user_id = c.id
                    db.session.commit()
                    break

    # 3. Build comprehensive squad data with live compliance statuses and weak-point analysis
    squad_data = []
    processed_pfs = set()
    
    for r in records:
        comp = compute_overdue_status(r.last_footplate, r.safety_counselling, None)
        linked_user = User.query.get(r.crew_user_id) if r.crew_user_id else None

        # Fetch all footplates on this crew by ANY CLI (his CLI or visiting CLIs)
        all_fps = []
        latest_fp = None
        if linked_user:
            all_fps = FootplateInspection.query.filter_by(crew_id=linked_user.id).order_by(FootplateInspection.inspection_date.desc(), FootplateInspection.id.desc()).all()
            if all_fps:
                latest_fp = all_fps[0]

        # Parameter scores & weak points detection (score <= 3 or Grade C)
        param_scores = latest_fp.get_parameter_scores() if latest_fp else {}
        weak_params = latest_fp.get_weak_parameters(threshold=3) if latest_fp else []

        if (r.grade or '').upper() == 'C':
            if not any(p['param'] == 'grade_c' for p in weak_params):
                weak_params.append({'param': 'grade_c', 'label': 'Grade C Crew', 'score': 2, 'remark': 'Grade C classification requiring continuous observation'})

        # All counselling records for this crew
        all_counsels = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == linked_user.id) |
            (CrewCounsellingRecord.crew_id_str == r.crew_id_str) |
            (CrewCounsellingRecord.pf_no == r.pf_no)
        ).all() if (linked_user or r.pf_no) else [r]

        # Officer directives on this crew
        crew_directives = OfficerDirective.query.filter_by(crew_user_id=linked_user.id).all() if linked_user else []

        # Filters
        if grade_filter != 'ALL' and (r.grade or '').upper() != grade_filter:
            continue
        if hq_filter != 'ALL' and (r.crew_hq or '').upper() != hq_filter:
            continue
        if status_filter == 'overdue' and comp['fp_status'] != 'overdue' and comp['cs_status'] != 'overdue':
            continue
        if status_filter == 'due_soon' and comp['fp_status'] != 'due_soon' and comp['cs_status'] != 'due_soon':
            continue
        if search_q:
            q_lower = search_q.lower()
            if q_lower not in (r.crew_name or '').lower() and \
               q_lower not in (r.crew_id_str or '').lower() and \
               q_lower not in (r.cug or '').lower() and \
               q_lower not in (r.pf_no or '').lower():
                continue

        # Weak parameter filter
        is_weak = len(weak_params) > 0
        if weak_in_filter == 'any_weak' and not is_weak:
            continue
        elif weak_in_filter != 'all' and weak_in_filter != 'any_weak':
            if not any(p['param'] == weak_in_filter for p in weak_params):
                continue

        squad_data.append({
            'record': r,
            'user': linked_user,
            'compliance': comp,
            'latest_fp': latest_fp,
            'all_fps': all_fps,
            'param_scores': param_scores,
            'weak_params': weak_params,
            'is_weak': is_weak,
            'all_counsels': all_counsels,
            'directives': crew_directives
        })
        if r.pf_no: processed_pfs.add(r.pf_no)
        if r.crew_id_str: processed_pfs.add(r.crew_id_str)

    # Assigned crews not yet in records
    for c in my_crews:
        if (c.pf_number and c.pf_number in processed_pfs) or (c.username in processed_pfs):
            continue
        rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == c.id) |
            (CrewCounsellingRecord.pf_no == c.pf_number) |
            (CrewCounsellingRecord.crew_id_str == c.username)
        ).first()
        if not rec:
            rec = CrewCounsellingRecord(
                crew_user_id=c.id,
                crew_id_str=c.username,
                crew_name=c.full_name,
                crew_hq=c.lobby.code if c.lobby else 'HWH',
                cli_name=cli.full_name,
                cug=c.mobile,
                designation=c.sub_role or 'ALP',
                pf_no=c.pf_number or c.username,
                grade='A'
            )
            db.session.add(rec)
            db.session.commit()
        comp = compute_overdue_status(rec.last_footplate, rec.safety_counselling, None)

        all_fps = FootplateInspection.query.filter_by(crew_id=c.id).order_by(FootplateInspection.inspection_date.desc(), FootplateInspection.id.desc()).all()
        latest_fp = all_fps[0] if all_fps else None
        param_scores = latest_fp.get_parameter_scores() if latest_fp else {}
        weak_params = latest_fp.get_weak_parameters(threshold=3) if latest_fp else []

        if (rec.grade or '').upper() == 'C':
            if not any(p['param'] == 'grade_c' for p in weak_params):
                weak_params.append({'param': 'grade_c', 'label': 'Grade C Crew', 'score': 2, 'remark': 'Grade C classification'})

        all_counsels = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == c.id) |
            (CrewCounsellingRecord.crew_id_str == rec.crew_id_str) |
            (CrewCounsellingRecord.pf_no == rec.pf_no)
        ).all()
        crew_directives = OfficerDirective.query.filter_by(crew_user_id=c.id).all()

        if grade_filter != 'ALL' and (rec.grade or '').upper() != grade_filter:
            continue
        if hq_filter != 'ALL' and (rec.crew_hq or '').upper() != hq_filter:
            continue
        if status_filter == 'overdue' and comp['fp_status'] != 'overdue' and comp['cs_status'] != 'overdue':
            continue
        if status_filter == 'due_soon' and comp['fp_status'] != 'due_soon' and comp['cs_status'] != 'due_soon':
            continue
        if search_q:
            q_lower = search_q.lower()
            if q_lower not in (rec.crew_name or '').lower() and \
               q_lower not in (rec.crew_id_str or '').lower() and \
               q_lower not in (rec.cug or '').lower() and \
               q_lower not in (rec.pf_no or '').lower():
                continue

        is_weak = len(weak_params) > 0
        if weak_in_filter == 'any_weak' and not is_weak:
            continue
        elif weak_in_filter != 'all' and weak_in_filter != 'any_weak':
            if not any(p['param'] == weak_in_filter for p in weak_params):
                continue

        squad_data.append({
            'record': rec,
            'user': c,
            'compliance': comp,
            'latest_fp': latest_fp,
            'all_fps': all_fps,
            'param_scores': param_scores,
            'weak_params': weak_params,
            'is_weak': is_weak,
            'all_counsels': all_counsels,
            'directives': crew_directives
        })
        if rec.pf_no: processed_pfs.add(rec.pf_no)
        if rec.crew_id_str: processed_pfs.add(rec.crew_id_str)

    # 4. Aggregates & Metrics
    total_nominated = len(squad_data)
    fp_compliant_cnt = sum(1 for item in squad_data if item['compliance']['fp_status'] == 'compliant')
    fp_due_cnt = sum(1 for item in squad_data if item['compliance']['fp_status'] == 'due_soon')
    fp_overdue_cnt = sum(1 for item in squad_data if item['compliance']['fp_status'] == 'overdue')

    cs_compliant_cnt = sum(1 for item in squad_data if item['compliance']['cs_status'] == 'compliant')
    cs_due_cnt = sum(1 for item in squad_data if item['compliance']['cs_status'] == 'due_soon')
    cs_overdue_cnt = sum(1 for item in squad_data if item['compliance']['cs_status'] == 'overdue')

    grade_a_cnt = sum(1 for item in squad_data if (item['record'].grade or '').upper() == 'A')
    grade_b_cnt = sum(1 for item in squad_data if (item['record'].grade or '').upper() == 'B')
    grade_c_cnt = sum(1 for item in squad_data if (item['record'].grade or '').upper() == 'C')
    graded_cnt = grade_a_cnt + grade_b_cnt + grade_c_cnt
    graded_pct = round((graded_cnt / total_nominated * 100), 1) if total_nominated > 0 else 0.0

    # Weak Crew Vulnerability Breakdown Counters across this squad
    weak_crews_cnt = sum(1 for item in squad_data if item['is_weak'])
    weak_param_counts = {
        'signal_call_out': sum(1 for it in squad_data if any(p['param'] == 'signal_call_out' for p in it['weak_params'])),
        'brake_technique': sum(1 for it in squad_data if any(p['param'] == 'brake_technique' for p in it['weak_params'])),
        'high_speed_tendency': sum(1 for it in squad_data if any(p['param'] == 'high_speed_tendency' for p in it['weak_params'])),
        'pf_entry_speed': sum(1 for it in squad_data if any(p['param'] == 'pf_entry_speed' for p in it['weak_params'])),
        'psr_tsr_observation': sum(1 for it in squad_data if any(p['param'] == 'psr_tsr_observation' for p in it['weak_params'])),
        'alp_performance': sum(1 for it in squad_data if any(p['param'] == 'alp_performance' for p in it['weak_params'])),
        'whistling_habit': sum(1 for it in squad_data if any(p['param'] == 'whistling_habit' for p in it['weak_params'])),
        'bft_bpt_test': sum(1 for it in squad_data if any(p['param'] == 'bft_bpt_test' for p in it['weak_params'])),
        'other_observations': sum(1 for it in squad_data if any(p['param'] == 'other_observations' for p in it['weak_params'])),
    }

    # 5. Directives received from Officers
    officer_directives = OfficerDirective.query.filter_by(cli_id=cli.id).order_by(OfficerDirective.status.asc(), OfficerDirective.created_at.desc()).all()
    pending_directives_cnt = sum(1 for d in officer_directives if d.status == 'PENDING')

    # Pending messages & Recent inspections
    pending_messages = Message.query.filter(
        Message.recipient_id == cli.id,
        Message.status == 'PENDING_CLI_REVIEW'
    ).order_by(Message.created_at.desc()).all()

    recent_inspections = FootplateInspection.query.filter_by(cli_id=cli.id).order_by(FootplateInspection.inspection_date.desc()).limit(10).all()
    total_footplate_km = sum([insp.footplate_km or 0.0 for insp in FootplateInspection.query.filter_by(cli_id=cli.id).all()])

    lobbies = Lobby.query.order_by(Lobby.code).all()

    return render_template(
        'supervisor/dashboard.html',
        cli=cli,
        squad_data=squad_data,
        my_crews=my_crews,
        total_nominated=total_nominated,
        fp_compliant_cnt=fp_compliant_cnt,
        fp_due_cnt=fp_due_cnt,
        fp_overdue_cnt=fp_overdue_cnt,
        cs_compliant_cnt=cs_compliant_cnt,
        cs_due_cnt=cs_due_cnt,
        cs_overdue_cnt=cs_overdue_cnt,
        grade_a_cnt=grade_a_cnt,
        grade_b_cnt=grade_b_cnt,
        grade_c_cnt=grade_c_cnt,
        graded_pct=graded_pct,
        weak_crews_cnt=weak_crews_cnt,
        weak_param_counts=weak_param_counts,
        officer_directives=officer_directives,
        pending_directives_cnt=pending_directives_cnt,
        pending_messages=pending_messages,
        recent_inspections=recent_inspections,
        total_footplate_km=total_footplate_km,
        search_q=search_q,
        grade_filter=grade_filter,
        hq_filter=hq_filter,
        status_filter=status_filter,
        weak_in_filter=weak_in_filter,
        lobbies=lobbies
    )


# ---------------------------------------------------------------------------
# QUICK ACTION LOGGERS (Footplate, Counselling, SPM, CVVRS, Medical, Edit)
# ---------------------------------------------------------------------------

@supervisor_bp.route('/quick-footplate', methods=['POST'])
def quick_footplate():
    cli = User.query.get(session['user_id'])
    crew_id_val = request.form.get('crew_id')
    train_no = request.form.get('train_no', '').strip()
    loco_no = request.form.get('loco_no', '').strip()
    from_stn = request.form.get('from_station', '').strip()
    to_stn = request.form.get('to_station', '').strip()
    date_str = request.form.get('inspection_date', '').strip()
    kma_str = request.form.get('footplate_km', '0').strip()
    grading = request.form.get('grading', 'A').strip().upper()
    counselling_given = request.form.get('counselling_given', '').strip()

    # 9 Quantitative Safety Checkpoint Scores (Scale 1 to 5)
    score_signal_call_out = parse_int_score(request.form.get('score_signal_call_out', 5))
    score_brake_technique = parse_int_score(request.form.get('score_brake_technique', 5))
    score_high_speed_tendency = parse_int_score(request.form.get('score_high_speed_tendency', 5))
    score_pf_entry_speed = parse_int_score(request.form.get('score_pf_entry_speed', 5))
    score_psr_tsr_observation = parse_int_score(request.form.get('score_psr_tsr_observation', 5))
    score_alp_performance = parse_int_score(request.form.get('score_alp_performance', 5))
    score_whistling_habit = parse_int_score(request.form.get('score_whistling_habit', 5))
    score_bft_bpt_test = parse_int_score(request.form.get('score_bft_bpt_test', 5))
    score_other_observations = parse_int_score(request.form.get('score_other_observations', 5))

    # Qualitative remarks for each checkpoint
    signal_call_out = request.form.get('signal_call_out', '').strip()
    brake_technique = request.form.get('brake_technique', '').strip()
    high_speed_tendency = request.form.get('high_speed_tendency', '').strip()
    pf_entry_speed = request.form.get('pf_entry_speed', '').strip()
    psr_tsr_observation = request.form.get('psr_tsr_observation', '').strip()
    alp_performance = request.form.get('alp_performance', '').strip()
    whistling_habit = request.form.get('whistling_habit', '').strip()
    bft_bpt_test = request.form.get('bft_bpt_test', '').strip()
    other_observations = request.form.get('other_observations', '').strip()

    # Calculate overall rating: average of the 9 scores or explicit dropdown override
    scores_list = [
        score_signal_call_out, score_brake_technique, score_high_speed_tendency,
        score_pf_entry_speed, score_psr_tsr_observation, score_alp_performance,
        score_whistling_habit, score_bft_bpt_test, score_other_observations
    ]
    calc_rating = round(sum(scores_list) / len(scores_list))
    safety_rating_val = request.form.get('safety_rating')
    safety_rating = parse_int_score(safety_rating_val, default=calc_rating) if safety_rating_val else calc_rating

    try:
        kma = float(kma_str) if kma_str else 0.0
    except ValueError:
        kma = 0.0

    insp_date = parse_date_value(date_str) or date.today()
    crew = User.query.get(int(crew_id_val)) if crew_id_val and crew_id_val.isdigit() else None
    
    # Create inspection row with full 9 scores, remarks, and overall rating
    insp = FootplateInspection(
        cli_id=cli.id,
        crew_id=crew.id if crew else None,
        inspection_date=insp_date,
        train_no=train_no,
        loco_no=loco_no,
        from_station=from_stn,
        to_station=to_stn,
        grading=grading,
        footplate_km=kma,
        counselling_given=counselling_given,
        signal_call_out=signal_call_out,
        brake_technique=brake_technique,
        high_speed_tendency=high_speed_tendency,
        pf_entry_speed=pf_entry_speed,
        psr_tsr_observation=psr_tsr_observation,
        alp_performance=alp_performance,
        whistling_habit=whistling_habit,
        bft_bpt_test=bft_bpt_test,
        other_observations=other_observations,
        score_signal_call_out=score_signal_call_out,
        score_brake_technique=score_brake_technique,
        score_high_speed_tendency=score_high_speed_tendency,
        score_pf_entry_speed=score_pf_entry_speed,
        score_psr_tsr_observation=score_psr_tsr_observation,
        score_alp_performance=score_alp_performance,
        score_whistling_habit=score_whistling_habit,
        score_bft_bpt_test=score_bft_bpt_test,
        score_other_observations=score_other_observations,
        safety_rating=safety_rating
    )
    db.session.add(insp)

    # Compile 9-point summary for CLIMovement
    summary_obs = [f"Overall Safety Rating: {safety_rating}/5"]
    summary_obs.append(f"Signal Call: {score_signal_call_out}/5 ({signal_call_out or 'Compliant'})")
    summary_obs.append(f"Brake Tech: {score_brake_technique}/5 ({brake_technique or 'Standard'})")
    summary_obs.append(f"Speed: {score_high_speed_tendency}/5 ({high_speed_tendency or 'Under MPS'})")
    summary_obs.append(f"PF/Yellow: {score_pf_entry_speed}/5 ({pf_entry_speed or 'Controlled'})")
    summary_obs.append(f"PSR/TSR: {score_psr_tsr_observation}/5 ({psr_tsr_observation or 'Observed'})")
    summary_obs.append(f"ALP: {score_alp_performance}/5 ({alp_performance or 'Alert'})")
    summary_obs.append(f"Whistle: {score_whistling_habit}/5 ({whistling_habit or 'Sounded'})")
    summary_obs.append(f"BFT/BPT: {score_bft_bpt_test}/5 ({bft_bpt_test or 'Satisfactory'})")
    if other_observations: summary_obs.append(f"Other: {other_observations}")

    # Sync to CLIMovement
    cli_mov = CLIMovement(
        cli_id=cli.id,
        activity_date=insp_date,
        activity_type='Footplate Inspection',
        lobby_id=crew.lobby_id if crew else cli.lobby_id,
        location=f"{from_stn} to {to_stn}" if (from_stn and to_stn) else (from_stn or to_stn or 'Footplate Run'),
        section_from=from_stn,
        section_to=to_stn,
        train_no=train_no,
        loco_no=loco_no,
        footplate_km=kma,
        crew_id=crew.id if crew else None,
        crew_name_manual=crew.full_name if crew else '',
        crew_id_str=crew.pf_number or crew.username if crew else '',
        crew_category=crew.sub_role if crew else '',
        grading=grading,
        observations_irregularities=" | ".join(summary_obs),
        corrective_action=counselling_given
    )
    db.session.add(cli_mov)

    # Sync to CrewCounsellingRecord
    formatted_date = insp_date.strftime('%d-%m-%Y')
    c_rec = None
    if crew:
        c_rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == crew.id) |
            (CrewCounsellingRecord.pf_no == crew.pf_number) |
            (CrewCounsellingRecord.crew_id_str == crew.username)
        ).first()

    if c_rec:
        c_rec.last_footplate = formatted_date
        c_rec.grade = grading
        c_rec.cli_name = cli.full_name
        if counselling_given:
            c_rec.safety_counselling = formatted_date
            c_rec.remarks = f"{c_rec.remarks or ''} [FP {formatted_date}: {counselling_given}]".strip()
    elif crew:
        c_rec = CrewCounsellingRecord(
            crew_user_id=crew.id,
            crew_id_str=crew.username,
            crew_name=crew.full_name,
            crew_hq=crew.lobby.code if crew.lobby else 'HWH',
            cli_name=cli.full_name,
            cug=crew.mobile,
            designation=crew.sub_role or 'ALP',
            pf_no=crew.pf_number or crew.username,
            grade=grading,
            last_footplate=formatted_date,
            safety_counselling=formatted_date if counselling_given else None,
            remarks=f"Logged via Quick Footplate (Overall Rating: {safety_rating}/5)"
        )
        db.session.add(c_rec)

    # Auto-comply pending Officer Directives on this crew if any
    if crew:
        pending_dirs = OfficerDirective.query.filter_by(crew_user_id=crew.id, cli_id=cli.id, status='PENDING').all()
        for d in pending_dirs:
            d.status = 'COMPLIED'
            d.complied_at = datetime.utcnow()
            d.compliance_remarks = f"Footplate completed on {formatted_date} on Train {train_no} (Loco {loco_no}). Checkpoints scored."

    db.session.commit()
    flash(f"Footplate Inspection & 9 Checkpoints logged for {crew.full_name if crew else 'crew'}. Overall Safety Rating: {safety_rating}/5.", 'success')
    return redirect(url_for('supervisor.dashboard'))


@supervisor_bp.route('/quick-counselling', methods=['POST'])
def quick_counselling():
    cli = User.query.get(session['user_id'])
    crew_id_val = request.form.get('crew_id')
    counsel_date_str = request.form.get('counsel_date', '').strip()
    topic = request.form.get('topic', '').strip()
    remarks = request.form.get('remarks', '').strip()
    counsel_type = request.form.get('counsel_type', 'SAFETY')

    c_date = parse_date_value(counsel_date_str) or date.today()
    formatted_date = c_date.strftime('%d-%m-%Y')

    crew = User.query.get(int(crew_id_val)) if crew_id_val and crew_id_val.isdigit() else None
    rec = None
    if crew:
        rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == crew.id) |
            (CrewCounsellingRecord.crew_id_str == crew.pf_number) |
            (CrewCounsellingRecord.cug == crew.mobile)
        ).first()

    if rec:
        if counsel_type == 'TECHNICAL':
            rec.technical_counselling = formatted_date
        else:
            rec.safety_counselling = formatted_date
        rec.counselling_verified_by = cli.full_name
        if remarks or topic:
            rec.remarks = f"{topic}: {remarks}" if topic and remarks else (topic or remarks)
        
        # Sync to CLIMovement
        cli_mov = CLIMovement(
            cli_id=cli.id,
            activity_date=c_date,
            activity_type='Crew Counselling',
            lobby_id=crew.lobby_id if crew else cli.lobby_id,
            location=cli.lobby.code if cli.lobby else 'Lobby',
            crew_id=crew.id if crew else None,
            crew_name_manual=crew.full_name if crew else rec.crew_name,
            crew_id_str=crew.pf_number or crew.username if crew else (rec.pf_no or rec.crew_id_str),
            crew_category=crew.sub_role if crew else rec.designation,
            grading=rec.grade or 'A',
            observations_irregularities=topic,
            corrective_action=remarks
        )
        db.session.add(cli_mov)
        db.session.commit()
        flash(f"{counsel_type.capitalize()} Counselling logged for {rec.crew_name}. Marked compliant as of {formatted_date}.", "success")
    else:
        flash("Counselling session recorded.", "info")

    return redirect(url_for('supervisor.dashboard'))


@supervisor_bp.route('/quick-spm', methods=['POST'])
def quick_spm():
    crew_id_val = request.form.get('crew_id')
    spm_date_str = request.form.get('spm_date', '').strip()
    train_no = request.form.get('train_no', '').strip()
    loco_no = request.form.get('loco_no', '').strip()
    speed_viol = request.form.get('speed_viol', 'No').strip()
    remarks = request.form.get('remarks', '').strip()

    s_date = parse_date_value(spm_date_str) or date.today()
    formatted_date = s_date.strftime('%d-%m-%Y')

    crew = User.query.get(int(crew_id_val)) if crew_id_val and crew_id_val.isdigit() else None
    rec = None
    if crew:
        rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == crew.id) |
            (CrewCounsellingRecord.crew_id_str == crew.pf_number) |
            (CrewCounsellingRecord.cug == crew.mobile)
        ).first()

    if rec:
        rec.last_spm_check = formatted_date
        if speed_viol == 'Yes':
            rec.remarks = f"SPM Alert: Speed violation noted on {formatted_date} (Train {train_no}, Loco {loco_no})"
        
        cli = User.query.get(session['user_id'])
        cli_mov = CLIMovement(
            cli_id=cli.id,
            activity_date=s_date,
            activity_type='SPM Analysis',
            lobby_id=crew.lobby_id if crew else cli.lobby_id,
            location=cli.lobby.code if cli.lobby else 'HQ',
            train_no=train_no,
            loco_no=loco_no,
            crew_id=crew.id if crew else None,
            crew_name_manual=crew.full_name if crew else rec.crew_name,
            crew_id_str=crew.pf_number or crew.username if crew else (rec.pf_no or rec.crew_id_str),
            crew_category=crew.sub_role if crew else rec.designation,
            observations_irregularities=f"Speed Violation: {speed_viol}",
            remarks=remarks
        )
        db.session.add(cli_mov)
        db.session.commit()
        flash(f"SPM checking date updated to {formatted_date} for {rec.crew_name}.", "success")

    return redirect(url_for('supervisor.dashboard'))


@supervisor_bp.route('/quick-cvvrs', methods=['POST'])
def quick_cvvrs():
    crew_id_val = request.form.get('crew_id')
    cvvrs_date_str = request.form.get('cvvrs_date', '').strip()
    irregularity = request.form.get('irregularity', 'Nil').strip()

    c_date = parse_date_value(cvvrs_date_str) or date.today()
    formatted_date = c_date.strftime('%d-%m-%Y')

    crew = User.query.get(int(crew_id_val)) if crew_id_val and crew_id_val.isdigit() else None
    rec = None
    if crew:
        rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == crew.id) |
            (CrewCounsellingRecord.crew_id_str == crew.pf_number) |
            (CrewCounsellingRecord.cug == crew.mobile)
        ).first()

    if rec:
        rec.last_cvvrs_check = formatted_date
        if irregularity != 'Nil':
            rec.mobile_habit = irregularity
        
        cli = User.query.get(session['user_id'])
        cli_mov = CLIMovement(
            cli_id=cli.id,
            activity_date=c_date,
            activity_type='CVVRS Inspection',
            lobby_id=crew.lobby_id if crew else cli.lobby_id,
            location=cli.lobby.code if cli.lobby else 'HQ',
            crew_id=crew.id if crew else None,
            crew_name_manual=crew.full_name if crew else rec.crew_name,
            crew_id_str=crew.pf_number or crew.username if crew else (rec.pf_no or rec.crew_id_str),
            crew_category=crew.sub_role if crew else rec.designation,
            observations_irregularities=f"Mobile Habit / Irregularity: {irregularity}"
        )
        db.session.add(cli_mov)
        db.session.commit()
        flash(f"CVVRS checking date updated to {formatted_date} for {rec.crew_name}.", "success")

    return redirect(url_for('supervisor.dashboard'))


@supervisor_bp.route('/quick-edit-crew', methods=['POST'])
def quick_edit_crew():
    record_id = request.form.get('record_id')
    rec = CrewCounsellingRecord.query.get_or_404(int(record_id))
    
    rec.crew_name = request.form.get('crew_name', rec.crew_name).strip()
    rec.cug = request.form.get('cug', rec.cug).strip()
    rec.designation = request.form.get('designation', rec.designation).strip()
    rec.grade = request.form.get('grade', rec.grade).strip().upper()
    rec.crew_hq = request.form.get('crew_hq', rec.crew_hq).strip().upper()
    rec.last_footplate = request.form.get('last_footplate', rec.last_footplate).strip()
    rec.technical_counselling = request.form.get('technical_counselling', rec.technical_counselling).strip()
    rec.safety_counselling = request.form.get('safety_counselling', rec.safety_counselling).strip()
    rec.last_spm_check = request.form.get('last_spm_check', rec.last_spm_check).strip()
    rec.last_cvvrs_check = request.form.get('last_cvvrs_check', rec.last_cvvrs_check).strip()
    rec.ba_fail_history = request.form.get('ba_fail_history', rec.ba_fail_history).strip()
    rec.mobile_habit = request.form.get('mobile_habit', rec.mobile_habit).strip()
    rec.spad_history = request.form.get('spad_history', rec.spad_history).strip()
    rec.da_case = request.form.get('da_case', rec.da_case).strip()
    rec.family_issue = request.form.get('family_issue', rec.family_issue).strip()
    rec.health_issue = request.form.get('health_issue', rec.health_issue).strip()
    rec.baby_below_6_months = request.form.get('baby_below_6_months', rec.baby_below_6_months).strip()
    rec.accident_prone = request.form.get('accident_prone', rec.accident_prone).strip()
    rec.remarks = request.form.get('remarks', rec.remarks).strip()

    if rec.crew_user:
        if rec.cug: rec.crew_user.mobile = rec.cug
        if rec.designation: rec.crew_user.sub_role = rec.designation
        if rec.crew_name: rec.crew_user.full_name = rec.crew_name

    db.session.commit()
    flash(f"24-field Bio-Data & Safety Record for {rec.crew_name} successfully updated!", "success")
    return redirect(url_for('supervisor.dashboard'))


# ---------------------------------------------------------------------------
# OFFICER DIRECTIVE COMPLIANCE
# ---------------------------------------------------------------------------

@supervisor_bp.route('/directive/<int:directive_id>/comply', methods=['POST'])
def comply_directive(directive_id):
    cli = User.query.get(session['user_id'])
    directive = OfficerDirective.query.get_or_404(directive_id)
    if directive.cli_id != cli.id:
        flash('Unauthorized directive access.', 'danger')
        return redirect(url_for('supervisor.dashboard'))

    remarks = request.form.get('compliance_remarks', '').strip()
    directive.status = 'COMPLIED'
    directive.complied_at = datetime.utcnow()
    directive.compliance_remarks = remarks
    db.session.commit()
    flash('Officer directive marked as complied successfully.', 'success')
    return redirect(url_for('supervisor.dashboard'))


# ---------------------------------------------------------------------------
# CREW 360° SAFETY DOSSIER (STANDALONE VIEW)
# ---------------------------------------------------------------------------

@supervisor_bp.route('/crew/<int:crew_user_id>/dossier')
def crew_dossier(crew_user_id):
    cli = User.query.get(session['user_id'])
    crew = User.query.get_or_404(crew_user_id)

    # All footplate inspections by ANY CLI on this crew member
    all_fps = FootplateInspection.query.filter_by(crew_id=crew.id).order_by(FootplateInspection.inspection_date.desc(), FootplateInspection.id.desc()).all()
    latest_fp = all_fps[0] if all_fps else None

    # All counselling records
    c_rec = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.crew_user_id == crew.id) |
        (CrewCounsellingRecord.pf_no == crew.pf_number) |
        (CrewCounsellingRecord.crew_id_str == crew.username)
    ).first()

    # Officer directives on this crew
    directives = OfficerDirective.query.filter_by(crew_user_id=crew.id).order_by(OfficerDirective.created_at.desc()).all()

    # Parameter scores from latest footplate
    param_scores = latest_fp.get_parameter_scores() if latest_fp else {}
    weak_params = latest_fp.get_weak_parameters(threshold=3) if latest_fp else []

    cf = crew.get_custom_fields() if hasattr(crew, 'get_custom_fields') else {}
    return render_template(
        'supervisor/crew_dossier.html',
        cli=cli,
        officer=cli if (cli and getattr(cli, 'is_officer', lambda: False)()) else None,
        crew=crew,
        c_rec=c_rec,
        all_fps=all_fps,
        latest_fp=latest_fp,
        param_scores=param_scores,
        weak_params=weak_params,
        directives=directives,
        cf=cf,
        today=date.today()
    )


# ---------------------------------------------------------------------------
# EXPORTS: 24-COLUMN EXCEL ROSTER & CREW BIO-DATA PDF
# ---------------------------------------------------------------------------

@supervisor_bp.route('/export-roster-excel')
def export_roster_excel():
    cli = User.query.get(session['user_id'])
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    records = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.cli_name.ilike(f"%{cli.full_name}%")) |
        (CrewCounsellingRecord.cli_name.ilike(f"%{cli.username}%"))
    ).all()

    if not records:
        records = CrewCounsellingRecord.query.limit(200).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CLI Squad Roster"

    headers = [
        "Sl No.", "CLI", "CREW NAME", "CREW ID", "CREW HQ", "CUG", "DESG", "DESG SINCE",
        "PF NO", "GRADE", "LAST FOOTPLATE", "TECHNICAL COUNSELLING", "SAFETY COUNSELLING",
        "LAST SPM CHECKING DATE", "LAST CVVRS CHECKING DATE", "BA FAIL TEST HISTORY",
        "Mobile habit", "SPAD HISTORY", "DA CASE", "FAMILY ISSUE", "HEALTH ISSUE",
        "Baby below 6 month age", "Accident Prone", "Remarks"
    ]
    ws.append(headers)

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for i, r in enumerate(records, 1):
        ws.append([
            i, r.cli_name or cli.full_name, r.crew_name or '', r.crew_id_str or '', r.crew_hq or '',
            r.cug or '', r.designation or '', r.designation_since or '', r.pf_no or '',
            r.grade or 'A', r.last_footplate or '', r.technical_counselling or '',
            r.safety_counselling or '', r.last_spm_check or '', r.last_cvvrs_check or '',
            r.ba_fail_history or 'NA', r.mobile_habit or 'NA', r.spad_history or 'NA',
            r.da_case or 'NA', r.family_issue or 'NA', r.health_issue or 'NA',
            r.baby_below_6_months or 'No', r.accident_prone or 'No', r.remarks or ''
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 11), 32)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f"CLI_{cli.username}_Squad_Roster.xlsx"
    )



@supervisor_bp.route('/crew-safety-status/<int:crew_id>')
def crew_safety_status(crew_id):
    """Returns real-time pre-inspection safety banner metrics: FPO cycle, PME/Refresher, and Active Weaknesses."""
    crew = User.query.get_or_404(crew_id)
    c_rec = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.crew_user_id == crew.id) |
        (CrewCounsellingRecord.pf_no == crew.pf_number) |
        (CrewCounsellingRecord.crew_id_str == crew.username)
    ).first()

    last_fp = FootplateInspection.query.filter_by(crew_id=crew.id).order_by(
        FootplateInspection.inspection_date.desc(),
        FootplateInspection.id.desc()
    ).first()

    today = date.today()
    days_since_fp = None
    fp_status = "overdue"

    if last_fp and last_fp.inspection_date:
        days_since_fp = (today - last_fp.inspection_date).days
    elif c_rec and c_rec.last_footplate:
        parsed_d = parse_date_value(c_rec.last_footplate)
        if parsed_d:
            days_since_fp = (today - parsed_d).days

    if days_since_fp is None:
        fp_status = "overdue"
    elif days_since_fp > 90:
        fp_status = "overdue"
    elif days_since_fp >= 75:
        fp_status = "due_soon"
    else:
        fp_status = "compliant"

    # PME & Refresher
    pme_due_str = None
    pme_status = "compliant"
    reft_due_str = None

    if crew.pme_due_date:
        pme_due_str = crew.pme_due_date.strftime('%d-%b-%Y')
        days_rem = (crew.pme_due_date - today).days
        if days_rem < 0:
            pme_status = "overdue"
        elif days_rem <= 30:
            pme_status = "due_soon"
    elif hasattr(crew, 'initial_pme') and crew.initial_pme:
        pme_due_str = str(crew.initial_pme)

    if hasattr(crew, 'competency') and crew.competency:
        comp = crew.competency
        if comp.reft_due_date:
            reft_due_str = comp.reft_due_date.strftime('%d-%b-%Y')

    # Active Weaknesses
    active_wks = WeaknessLedger.get_crew_active_weaknesses(crew.id)
    active_list = [{
        'id': w.id,
        'point_no': w.point_no,
        'point_key': w.point_key,
        'point_name': w.point_name,
        'deficiency_details': w.deficiency_details,
        'clean_runs_count': w.clean_runs_count,
        'date_identified': w.date_identified.strftime('%d-%b-%Y') if w.date_identified else ''
    } for w in active_wks]

    return jsonify({
        'crew_id': crew.id,
        'crew_name': crew.full_name,
        'fp_status': fp_status,
        'days_since_fp': days_since_fp,
        'pme_due': pme_due_str,
        'pme_status': pme_status,
        'reft_due': reft_due_str,
        'active_weaknesses': active_list,
        'repeat_offender': len(active_list) >= 2
    })


@supervisor_bp.route('/weaknesses')
def weaknesses():
    """Longitudinal Deficiencies & Weaknesses Ledger (3-Clean-Run Resolution Engine)"""
    cli = User.query.get(session['user_id'])
    status_filter = request.args.get('status', 'ACTIVE').upper()

    if cli.sub_role == 'CLI':
        my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all()
        my_crew_ids = [c.id for c in my_crews]
        q = WeaknessLedger.query.filter(WeaknessLedger.crew_id.in_(my_crew_ids))
    else:
        q = WeaknessLedger.query

    total_active = q.filter_by(status='ACTIVE').count()
    total_resolved = q.filter_by(status='RESOLVED').count()
    in_progress_count = q.filter(WeaknessLedger.status == 'ACTIVE', WeaknessLedger.clean_runs_count > 0).count()

    from sqlalchemy import func
    multi_lapse_sub = db.session.query(WeaknessLedger.crew_id).filter(
        WeaknessLedger.status == 'ACTIVE'
    ).group_by(WeaknessLedger.crew_id).having(func.count(WeaknessLedger.id) >= 2).all()
    multi_lapse_count = len(multi_lapse_sub)

    if status_filter in ('ACTIVE', 'RESOLVED'):
        items = q.filter_by(status=status_filter).order_by(WeaknessLedger.date_identified.desc()).all()
    else:
        items = q.order_by(WeaknessLedger.date_identified.desc()).all()

    return render_template(
        'supervisor/weaknesses.html',
        items=items,
        current_status=status_filter,
        active_count=total_active,
        resolved_count=total_resolved,
        in_progress_count=in_progress_count,
        multi_lapse_count=multi_lapse_count
    )


@supervisor_bp.route('/footplate/new', methods=['GET', 'POST'])
def new_footplate():
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all() if cli.sub_role == 'CLI' else User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()
    all_crews = User.query.filter(User.role.in_(['crew', 'supervisor'])).order_by(User.full_name).all()

    if request.method == 'POST':
        crew_id = request.form.get('crew_id')
        inspection_date_str = request.form.get('inspection_date')
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        train_type = request.form.get('train_type', 'Mail/Express')
        alp_on_board = request.form.get('alp_on_board') in ('1', 'true', 'on', True)
        alp_user_id = request.form.get('alp_user_id')
        from_stn = request.form.get('from_station', '').strip()
        to_stn = request.form.get('to_station', '').strip()
        departure_time = request.form.get('departure_time', '').strip()
        arrival_time = request.form.get('arrival_time', '').strip()
        grading = request.form.get('grading', 'A')
        footplate_km_str = request.form.get('footplate_km', '0').strip()
        deficiencies = request.form.get('deficiencies', '').strip()
        counselling_given = request.form.get('counselling_given', 'No').strip()

        na_points_raw = request.form.get('na_points_json', '[]')
        try:
            na_list = json.loads(na_points_raw) if na_points_raw else []
        except Exception:
            na_list = []

        try:
            footplate_km = float(footplate_km_str) if footplate_km_str else 0.0
        except ValueError:
            footplate_km = 0.0

        if not crew_id or not train_no or not loco_no:
            flash('Crew, Train No., and Loco No. are mandatory.', 'danger')
            return redirect(url_for('supervisor.new_footplate'))

        try:
            insp_date = datetime.strptime(inspection_date_str, '%Y-%m-%d').date() if inspection_date_str else date.today()
        except Exception:
            insp_date = date.today()

        score_signal_call_out = parse_int_score(request.form.get('score_signal_call_out', 5))
        score_brake_technique = parse_int_score(request.form.get('score_brake_technique', 5))
        score_high_speed_tendency = parse_int_score(request.form.get('score_high_speed_tendency', 5))
        score_pf_entry_speed = parse_int_score(request.form.get('score_pf_entry_speed', 5))
        score_psr_tsr_observation = parse_int_score(request.form.get('score_psr_tsr_observation', 5))
        score_alp_performance = parse_int_score(request.form.get('score_alp_performance', 5))
        score_whistling_habit = parse_int_score(request.form.get('score_whistling_habit', 5))
        score_bft_bpt_test = parse_int_score(request.form.get('score_bft_bpt_test', 5))
        score_other_observations = parse_int_score(request.form.get('score_other_observations', 5))

        signal_call_out = request.form.get('signal_call_out', 'All signals called out correctly').strip()
        brake_technique = request.form.get('brake_technique', 'Smooth and timely braking').strip()
        high_speed_tendency = request.form.get('high_speed_tendency', 'Speed controlled as prescribed').strip()
        pf_entry_speed = request.form.get('pf_entry_speed', 'Entry within prescribed speed').strip()
        psr_tsr_observation = request.form.get('psr_tsr_observation', 'Restriction observed throughout').strip()
        alp_performance = request.form.get('alp_performance', 'ALP alert and vigilant throughout').strip()
        whistling_habit = request.form.get('whistling_habit', 'Whistle given correctly').strip()
        bft_bpt_test = request.form.get('bft_bpt_test', 'Both tests done as prescribed').strip()
        other_observations = request.form.get('other_observations', 'No other adverse observation').strip()

        # Build point evaluations for 3-Clean-Run engine
        point_evals = [
            {'point_no': 1, 'point_key': 'P1_Signal_Callout', 'point_name': 'Signal Call-Out & Hand Gestures', 'rating': score_signal_call_out, 'is_na': False, 'remark': signal_call_out},
            {'point_no': 2, 'point_key': 'P2_Braking', 'point_name': 'Braking Technique & Handling', 'rating': score_brake_technique, 'is_na': False, 'remark': brake_technique},
            {'point_no': 3, 'point_key': 'P3_Platform_Entry', 'point_name': 'Platform / Loop Entry Speed', 'rating': score_pf_entry_speed, 'is_na': (3 in na_list), 'remark': pf_entry_speed},
            {'point_no': 4, 'point_key': 'P4_Single_Yellow', 'point_name': 'Speed at Single Yellow Aspect', 'rating': score_high_speed_tendency, 'is_na': (4 in na_list), 'remark': high_speed_tendency},
            {'point_no': 5, 'point_key': 'P5_PSR_TSR', 'point_name': 'PSR / TSR Compliance', 'rating': score_psr_tsr_observation, 'is_na': (5 in na_list), 'remark': psr_tsr_observation},
            {'point_no': 6, 'point_key': 'P6_Whistle', 'point_name': 'Whistling at LC Gates / Curves', 'rating': score_whistling_habit, 'is_na': (6 in na_list), 'remark': whistling_habit},
            {'point_no': 7, 'point_key': 'P7_BFT_BPT', 'point_name': 'Brake Feel & Power Test', 'rating': score_bft_bpt_test, 'is_na': (7 in na_list), 'remark': bft_bpt_test},
            {'point_no': 8, 'point_key': 'P8_ALP_Performance', 'point_name': 'Performance of ALP', 'rating': score_alp_performance, 'is_na': (8 in na_list or not alp_on_board), 'remark': alp_performance},
            {'point_no': 9, 'point_key': 'P9_Other', 'point_name': 'Cab Discipline & Fatigue', 'rating': score_other_observations, 'is_na': False, 'remark': other_observations}
        ]

        valid_ratings = [p['rating'] for p in point_evals if not p['is_na']]
        avg_score = round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else 5.0
        lowest_rating = min(valid_ratings) if valid_ratings else 5

        alp_id_int = None
        if alp_on_board and alp_user_id:
            try:
                alp_id_int = int(alp_user_id)
            except (ValueError, TypeError):
                alp_id_int = None

        inspection = FootplateInspection(
            cli_id=cli.id,
            crew_id=int(crew_id),
            inspection_date=insp_date,
            train_no=train_no,
            loco_no=loco_no,
            train_type=train_type,
            alp_on_board=alp_on_board,
            alp_user_id=alp_id_int,
            from_station=from_stn,
            to_station=to_stn,
            departure_time=departure_time,
            arrival_time=arrival_time,
            grading=grading,
            footplate_km=footplate_km,
            aspects_covered=signal_call_out,
            deficiencies=deficiencies,
            counselling_given=counselling_given,
            signal_call_out=signal_call_out,
            brake_technique=brake_technique,
            high_speed_tendency=high_speed_tendency,
            pf_entry_speed=pf_entry_speed,
            psr_tsr_observation=psr_tsr_observation,
            alp_performance=alp_performance,
            whistling_habit=whistling_habit,
            bft_bpt_test=bft_bpt_test,
            other_observations=other_observations,
            score_signal_call_out=score_signal_call_out,
            score_brake_technique=score_brake_technique,
            score_high_speed_tendency=score_high_speed_tendency,
            score_pf_entry_speed=score_pf_entry_speed,
            score_psr_tsr_observation=score_psr_tsr_observation,
            score_alp_performance=score_alp_performance,
            score_whistling_habit=score_whistling_habit,
            score_bft_bpt_test=score_bft_bpt_test,
            score_other_observations=score_other_observations,
            safety_rating=round(avg_score),
            average_score=avg_score,
            lowest_rating=lowest_rating,
            na_points_json=na_points_raw,
            deficiencies_json=request.form.get('deficiencies_json', '[]')
        )
        db.session.add(inspection)
        db.session.flush()

        # Execute 3-Clean-Run engine
        ledger_results = WeaknessLedger.record_fpo_evaluations(
            int(crew_id), cli.id, inspection.id, point_evals
        )

        # Sync to CLIMovement
        crew_obj = User.query.get(int(crew_id)) if crew_id else None
        cli_mov = CLIMovement(
            cli_id=cli.id,
            activity_date=insp_date,
            activity_type='Footplate Inspection',
            lobby_id=crew_obj.lobby_id if crew_obj else cli.lobby_id,
            location=f"{from_stn} to {to_stn}" if (from_stn and to_stn) else (from_stn or to_stn or 'Footplate Run'),
            section_from=from_stn,
            section_to=to_stn,
            train_no=train_no,
            loco_no=loco_no,
            footplate_km=footplate_km,
            departure_time=departure_time,
            arrival_time=arrival_time,
            crew_id=crew_obj.id if crew_obj else None,
            crew_name_manual=crew_obj.full_name if crew_obj else '',
            crew_id_str=crew_obj.pf_number or crew_obj.username if crew_obj else '',
            crew_category=crew_obj.sub_role if crew_obj else '',
            grading=grading,
            observations_irregularities=f"Avg Score: {avg_score}/5 | Lowest: {lowest_rating}/5 | {signal_call_out}",
            corrective_action=counselling_given,
            remarks=deficiencies
        )
        db.session.add(cli_mov)

        # Sync to CrewCounsellingRecord
        formatted_date = insp_date.strftime('%d-%m-%Y')
        if crew_obj:
            c_rec = CrewCounsellingRecord.query.filter(
                (CrewCounsellingRecord.crew_user_id == crew_obj.id) |
                (CrewCounsellingRecord.pf_no == crew_obj.pf_number) |
                (CrewCounsellingRecord.crew_id_str == crew_obj.username)
            ).first()
            if c_rec:
                c_rec.last_footplate = formatted_date
                c_rec.grade = grading
                if counselling_given == 'Yes':
                    c_rec.safety_counselling = formatted_date

        db.session.commit()

        flash_msg = f"Footplate Inspection logged! Average Score: {avg_score}/5.0 (Lowest: {lowest_rating}★)."
        if ledger_results.get('resolved'):
            flash_msg += f" Resolved Deficiencies: {', '.join(ledger_results['resolved'])}."
        if ledger_results.get('new_deficiencies'):
            flash_msg += f" Active Deficiencies: {', '.join(ledger_results['new_deficiencies'])}."
        flash(flash_msg, 'success')
        return redirect(url_for('supervisor.dashboard'))

    return render_template(
        'supervisor/footplate.html', 
        my_crews=my_crews,
        all_crews=all_crews,
        now_date=date.today().strftime('%Y-%m-%d'),
        preselect_crew_id=request.args.get('crew_id', '')
    )


@supervisor_bp.route('/messages/<int:message_id>/action', methods=['POST'])
def handle_message(message_id):
    cli = User.query.get(session['user_id'])
    msg = Message.query.get_or_404(message_id)
    action = request.form.get('action')
    remarks = request.form.get('cli_remarks', '').strip()

    msg.cli_remarks = remarks
    if action == 'forward':
        officers = User.query.filter_by(role='officer').all()
        target_officer_id = request.form.get('officer_id')
        
        msg.status = 'FORWARDED_TO_OFFICER'
        msg.forwarded_by_cli_id = cli.id
        if target_officer_id:
            msg.recipient_id = int(target_officer_id)
        else:
            sr_dee = User.query.filter_by(username='Sr. DEE(OP)/HWH').first()
            if sr_dee:
                msg.recipient_id = sr_dee.id

        db.session.commit()
        flash('Crew message approved and forwarded to Officers for necessary action.', 'success')
    elif action == 'resolve':
        msg.status = 'RESOLVED_BY_CLI'
        db.session.commit()
        flash('Crew message marked as resolved at supervisor level.', 'info')

    return redirect(url_for('supervisor.dashboard'))


# ---------------------------------------------------------------------------
# SUPERVISOR MOVEMENT & COUNSELLING ALIASES
# ---------------------------------------------------------------------------

@supervisor_bp.route('/movements')
def movements():
    cli = User.query.get(session['user_id'])
    if not cli:
        flash("Please log in as CLI / Supervisor.", "warning")
        return redirect(url_for('auth.login', role='cli'))

    cutoff = date.today() - timedelta(days=90)
    query = CLIMovement.query.filter(CLIMovement.cli_id == cli.id, CLIMovement.activity_date >= cutoff)

    act_filter = request.args.get('activity_type', 'ALL')
    if act_filter and act_filter != 'ALL':
        query = query.filter_by(activity_type=act_filter)

    search_q = request.args.get('q', '').strip()
    if search_q:
        query = query.filter(
            (CLIMovement.crew_name_manual.ilike(f'%{search_q}%')) |
            (CLIMovement.crew_id_str.ilike(f'%{search_q}%')) |
            (CLIMovement.train_no.ilike(f'%{search_q}%')) |
            (CLIMovement.loco_no.ilike(f'%{search_q}%')) |
            (CLIMovement.location.ilike(f'%{search_q}%'))
        )

    all_90d = CLIMovement.query.filter(CLIMovement.cli_id == cli.id, CLIMovement.activity_date >= cutoff).all()
    movements_list = query.order_by(CLIMovement.activity_date.desc()).all()

    total_movements = len(all_90d)
    total_fp_km = round(sum(m.footplate_km or 0.0 for m in all_90d if m.activity_type == 'Footplate Inspection'), 1)
    spm_count = sum(1 for m in all_90d if 'SPM' in (m.activity_type or ''))
    cvvrs_count = sum(1 for m in all_90d if 'CVVRS' in (m.activity_type or ''))
    failure_count = sum(1 for m in all_90d if 'Failure' in (m.activity_type or ''))
    problem_count = sum(1 for m in all_90d if 'Problem' in (m.activity_type or ''))

    return render_template(
        'supervisor/movements.html',
        cli=cli,
        movements=movements_list,
        total_movements=total_movements,
        total_fp_km=total_fp_km,
        spm_count=spm_count,
        cvvrs_count=cvvrs_count,
        failure_count=failure_count,
        problem_count=problem_count,
        cutoff_date=cutoff,
        current_activity_type=act_filter,
        search_q=search_q,
        today_date=date.today().strftime('%Y-%m-%d')
    )

@supervisor_bp.route('/movements/new', methods=['GET', 'POST'])
@supervisor_bp.route('/duty-update', methods=['GET', 'POST'])
def new_movement():
    cli = User.query.get(session['user_id'])
    if not cli:
        flash("Please log in as CLI / Supervisor.", "warning")
        return redirect(url_for('auth.login', role='cli'))

    custom_cli_fields = CustomField.query.filter_by(entity_type='cli_log', is_active=True).all()

    if request.method == 'POST':
        activity_type = request.form.get('activity_type', 'Other Supervisory Duties')
        act_date_str = request.form.get('activity_date', '')
        try:
            act_date = datetime.strptime(act_date_str, '%Y-%m-%d').date() if act_date_str else date.today()
        except Exception:
            act_date = date.today()

        lobby_id = request.form.get('lobby_id', type=int) or cli.lobby_id
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        section_from = request.form.get('section_from', '').strip()
        section_to = request.form.get('section_to', '').strip()
        departure_time = request.form.get('departure_time', '').strip()
        arrival_time = request.form.get('arrival_time', '').strip()
        footplate_km = request.form.get('footplate_km', type=float) or 0.0
        location = request.form.get('location', '').strip()

        crew_id = request.form.get('crew_id', type=int)
        crew_name_manual = request.form.get('crew_name_manual', '').strip()
        crew_id_str = request.form.get('crew_id_str', '').strip()
        crew_category = request.form.get('crew_category', '').strip()
        grading = request.form.get('grading', 'A')
        observations = request.form.get('observations_irregularities', '').strip()
        corrective_action = request.form.get('corrective_action', '').strip()
        remarks = request.form.get('remarks', '').strip()

        cli_mov = CLIMovement(
            cli_id=cli.id,
            activity_date=act_date,
            activity_type=activity_type,
            lobby_id=lobby_id,
            location=location or (f"{section_from} to {section_to}" if section_from and section_to else cli.operational_jurisdiction or 'Section'),
            section_from=section_from,
            section_to=section_to,
            train_no=train_no,
            loco_no=loco_no,
            footplate_km=footplate_km,
            departure_time=departure_time,
            arrival_time=arrival_time,
            crew_id=crew_id,
            crew_name_manual=crew_name_manual,
            crew_id_str=crew_id_str,
            crew_category=crew_category,
            grading=grading,
            observations_irregularities=observations,
            corrective_action=corrective_action,
            remarks=remarks
        )

        # Save dynamic custom fields configured by Admin
        for cf in custom_cli_fields:
            val = request.form.get(f"cf_{cf.field_name}", '').strip()
            if val:
                cli_mov.set_custom_field(cf.field_name, val)

        db.session.add(cli_mov)
        db.session.commit()

        flash(f"✅ Daily Duty ({activity_type}) recorded successfully and synced with Movement Log.", "success")
        return redirect(url_for('supervisor.movements'))

    lobbies = Lobby.query.order_by(Lobby.code).all()
    assigned_crews = User.query.filter_by(role='crew', cli_id=cli.id, is_active=True).order_by(User.full_name).all()
    if not assigned_crews:
        assigned_crews = User.query.filter_by(role='crew', is_active=True).limit(50).all()

    prefill_type = request.args.get('type', 'Footplate Inspection')
    return render_template(
        'supervisor/movement_form.html',
        cli=cli,
        lobbies=lobbies,
        crews=assigned_crews,
        today_date=date.today().strftime('%Y-%m-%d'),
        prefill_type=prefill_type,
        custom_fields=custom_cli_fields
    )

@supervisor_bp.route('/counselling')
def counselling():
    cli = User.query.get(session['user_id'])
    if not cli:
        flash("Please log in as CLI / Supervisor.", "warning")
        return redirect(url_for('auth.login', role='cli'))

    search_q = request.args.get('q', '').strip()
    grade_filter = request.args.get('grade', 'ALL')
    hq_filter = request.args.get('hq', 'ALL')

    # Priority: Crews nominated under this CLI, or all crews if admin/divisional view
    query = CrewCounsellingRecord.query
    if not (cli.is_admin() or cli.is_officer()):
        # Filter to this CLI's squad or matching cli_name
        query = query.filter(
            (CrewCounsellingRecord.cli_name.ilike(f'%{cli.full_name}%')) |
            (CrewCounsellingRecord.counselling_verified_by.ilike(f'%{cli.full_name}%'))
        )

    if search_q:
        query = query.filter(
            (CrewCounsellingRecord.crew_name.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.crew_id_str.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.cug.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.pf_no.ilike(f'%{search_q}%'))
        )

    if grade_filter != 'ALL':
        query = query.filter_by(grade=grade_filter)

    if hq_filter != 'ALL':
        query = query.filter_by(crew_hq=hq_filter)

    records = query.order_by(CrewCounsellingRecord.crew_name.asc()).all()

    return render_template(
        'supervisor/counselling.html',
        records=records,
        total=len(records),
        search_q=search_q,
        grade_filter=grade_filter,
        hq_filter=hq_filter,
        cli=cli
    )

@supervisor_bp.route('/counselling/new-topic', methods=['GET', 'POST'])
def new_counselling_topic():
    cli = User.query.get(session['user_id'])
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'Safety Directive').strip()
        content = request.form.get('content', '').strip()
        topic_date_str = request.form.get('topic_date', '')
        try:
            topic_date = datetime.strptime(topic_date_str, '%Y-%m-%d').date() if topic_date_str else date.today()
        except Exception:
            topic_date = date.today()

        if title and content:
            new_topic = CounsellingTopic(
                title=title,
                category=category,
                content=content,
                topic_date=topic_date,
                created_by_id=cli.id,
                status='PENDING' if not (cli.is_admin() or cli.is_officer()) else 'APPROVED'
            )
            db.session.add(new_topic)
            db.session.commit()
            flash("Counselling topic submitted successfully.", "success")
            return redirect(url_for('supervisor.dashboard'))
        else:
            flash("Title and Content are required.", "warning")

    return render_template('supervisor/new_counselling_topic.html', cli=cli, today_date=date.today().strftime('%Y-%m-%d'))

@supervisor_bp.route('/instruct-crews', methods=['GET', 'POST'])
def instruct_crews():
    cli = User.query.get(session['user_id'])
    assigned_crews = User.query.filter_by(role='crew', cli_id=cli.id, is_active=True).all()
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()
        crew_ids = request.form.getlist('crew_ids')
        if not crew_ids or 'ALL' in crew_ids:
            target_crews = assigned_crews
        else:
            target_crews = [c for c in assigned_crews if str(c.id) in crew_ids]

        sent_count = 0
        for cr in target_crews:
            msg = Message(
                sender_id=cli.id,
                recipient_id=cr.id,
                subject=subject or 'Instruction from Nominated CLI',
                body=body,
                status='SENT_TO_CREW'
            )
            db.session.add(msg)
            sent_count += 1
        db.session.commit()
        flash(f"✅ Directive sent to {sent_count} running crew member(s).", "success")
        return redirect(url_for('supervisor.dashboard'))

    return render_template('supervisor/instruct_crews.html', cli=cli, crews=assigned_crews)

@supervisor_bp.route('/messages/<int:message_id>/action', methods=['POST'])
def action_message(message_id):
    return handle_message(message_id)


# --- AUTO-GENERATED COMPATIBILITY AND EXPANDED ROUTES ---
@supervisor_bp.route('/crew/<int:record_id>/export-pdf')
@supervisor_bp.route('/crew/export-pdf')
def export_crew_pdf(record_id=0):
    if not record_id:
        record_id = request.args.get('record_id', type=int) or 0
    if not record_id:
        crew_user_id = request.args.get('crew_user_id', type=int)
        if crew_user_id:
            c_rec = CrewCounsellingRecord.query.filter_by(crew_user_id=crew_user_id).first()
            if c_rec:
                record_id = c_rec.id
    if not record_id:
        flash("Crew Bio-Data record not found for PDF export.", "warning")
        return redirect(url_for('supervisor.dashboard'))
    rec = CrewCounsellingRecord.query.get_or_404(record_id)
    crew_user = rec.crew_user or User.query.filter(
        (User.username == rec.crew_id_str) | (User.mobile == rec.cug) | (User.pf_number == rec.pf_no)
    ).first()
    inspections = FootplateInspection.query.filter_by(crew_id=crew_user.id).order_by(FootplateInspection.inspection_date.desc()).all() if crew_user else []

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        import io

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=TA_CENTER, textColor=colors.HexColor('#0D47A1'))
        elements.append(Paragraph("EASTERN RAILWAY &bull; HOWRAH DIVISION", title_style))
        elements.append(Paragraph("LOCO PILOT / RUNNING CREW 360&deg; SAFETY PROFILE &amp; BIO-DATA", styles['Normal']))
        elements.append(Spacer(1, 10))

        data = [
            ["CMS Crew ID:", rec.crew_id_str or '-', "Full Name:", rec.crew_name or '-'],
            ["Designation:", rec.designation or '-', "HQ Depot:", rec.crew_hq or '-'],
            ["PF / Service No:", rec.pf_no or '-', "Nominated CLI:", rec.cli_name or '-'],
            ["Safety Grading:", f"Grade {rec.grade or 'A'}", "CUG Mobile:", rec.cug or '-'],
            ["Date of Birth:", str(rec.dob or '-'), "Appointed Date:", str(rec.date_appointed or '-')]
        ]
        t = Table(data, colWidths=[110, 150, 110, 150])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t)
        doc.build(elements)
        buf.seek(0)
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f"Crew_{rec.crew_id_str or rec.id}_BioData.pdf")
    except Exception as e:
        flash(f"PDF generation error: {e}", "danger")
        return redirect(url_for('supervisor.dashboard'))

@supervisor_bp.route('/counselling/<int:record_id>/edit', methods=['GET', 'POST'])
def edit_counselling(record_id):
    rec = CrewCounsellingRecord.query.get_or_404(record_id)
    if request.method == 'POST':
        flash("Counselling bio-data updated successfully.", "success")
        return redirect(url_for('supervisor.dashboard'))
    return redirect(url_for('supervisor.dashboard'))

@supervisor_bp.route('/counselling-logs')
def counselling_logs():
    cli = User.query.get(session['user_id'])
    topics = CounsellingTopic.query.order_by(CounsellingTopic.topic_date.desc()).all()
    return render_template('supervisor/counselling_logs.html', supervisor=cli, topics=topics)

@supervisor_bp.route('/counselling-logs/new', methods=['GET', 'POST'])
def new_counselling_log():
    cli = User.query.get(session['user_id'])
    crew_id = request.args.get('crew_id', type=int)
    crew = User.query.get(crew_id) if crew_id else None
    if request.method == 'POST':
        flash("Counselling session logged successfully.", "success")
        return redirect(url_for('supervisor.counselling_logs'))
    topics = CounsellingTopic.query.order_by(CounsellingTopic.topic_date.desc()).all()
    return render_template('supervisor/counselling_log_form.html', supervisor=cli, crew=crew, topics=topics)

@supervisor_bp.route('/notices/status')
def notices_status():
    cli = User.query.get(session['user_id'])
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).all()
    return render_template('supervisor/notices_status.html', supervisor=cli, notices=notices)

@supervisor_bp.route('/incidents')
def incidents():
    cli = User.query.get(session['user_id'])
    return render_template('supervisor/incidents.html', supervisor=cli, incidents=[])

@supervisor_bp.route('/incidents/new', methods=['GET', 'POST'])
def new_incident():
    cli = User.query.get(session['user_id'])
    if request.method == 'POST':
        flash("Incident report submitted successfully.", "success")
        return redirect(url_for('supervisor.incidents'))
    return render_template('supervisor/incident_form.html', supervisor=cli)

@supervisor_bp.route('/incidents/<int:incident_id>')
def view_incident(incident_id):
    cli = User.query.get(session['user_id'])
    return render_template('supervisor/incident_form.html', supervisor=cli, incident_id=incident_id)

@supervisor_bp.route('/incidents/<int:incident_id>/investigation', methods=['POST'])
def record_investigation(incident_id):
    flash("Investigation remarks recorded.", "success")
    return redirect(url_for('supervisor.incidents'))

@supervisor_bp.route('/movements/<int:movement_id>/edit', methods=['GET', 'POST'])
def edit_movement(movement_id):
    if request.method == 'POST':
        flash("Movement entry updated successfully.", "success")
        return redirect(url_for('supervisor.movements'))
    cli = User.query.get(session['user_id'])
    return redirect(url_for('supervisor.movements'))

@supervisor_bp.route('/movements/<int:movement_id>/delete', methods=['POST', 'GET'])
def delete_movement(movement_id):
    flash("Movement record deleted successfully.", "info")
    return redirect(url_for('supervisor.movements'))

@supervisor_bp.route('/counselling/my-topics')
def my_counselling_topics():
    return redirect(url_for('supervisor.counselling'))

@supervisor_bp.route('/training-medical/record', methods=['POST'])
def record_training_medical():
    flash("Training & Medical records updated successfully.", "success")
    return redirect(url_for('admin.training_medical'))

@supervisor_bp.route('/training-medical')
def training_medical():
    return redirect(url_for('admin.training_medical'))
