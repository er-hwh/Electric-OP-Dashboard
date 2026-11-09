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
    CounsellingTopic, Notice, CrewCounsellingRecord, CLIMovement
)
from blueprints.auth import role_required

supervisor_bp = Blueprint('supervisor', __name__)

@supervisor_bp.before_request
@role_required('supervisor')
def supervisor_protection():
    pass


# ---------------------------------------------------------------------------
# DATE PARSER & COMPLIANCE CALCULATOR (From hwh-division-operation-dashboard)
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
        "%d.%m.%Y", "%d-%b-%Y", "%d-%B-%Y", "%d-%b-%y",
        "%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"
    ]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        f = float(s)
        if f > 30000:
            return (datetime(1899, 12, 30) + timedelta(days=f)).date()
    except Exception:
        pass
    return None


def compute_overdue_status(last_fp_raw, last_counsel_raw, next_pme_raw=None):
    """
    Overdue Calculation matching Indian Railways Electric Operation standards:
    - Footplate: >90 days overdue, 75-90 days due soon, compliant <75 days
    - Counselling: >90 days overdue, 75-90 days due soon, compliant <75 days
    - PME / Medical: overdue if past due date, due soon if <= 30 days
    """
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
# CLI DASHBOARD & SQUAD MONITORING (Ported from hwh-division-operation-dashboard)
# ---------------------------------------------------------------------------

@supervisor_bp.route('/')
@supervisor_bp.route('/dashboard')
def dashboard():
    cli = User.query.get(session['user_id'])
    search_q = request.args.get('q', '').strip()
    grade_filter = request.args.get('grade', 'ALL').strip().upper()
    hq_filter = request.args.get('hq', 'ALL').strip().upper()
    status_filter = request.args.get('status', 'ALL').strip().lower()

    # 1. Fetch assigned crew users
    if cli.sub_role == 'CLI':
        my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all()
        crew_ids = [c.id for c in my_crews]
    else:
        my_crews = User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()
        crew_ids = [c.id for c in my_crews]

    # 2. Fetch 24-column counselling records for this CLI's squad or by CLI name match
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

    # Link records to User rows if not already linked
    counselling_map = {}
    for r in records:
        if r.crew_user_id:
            counselling_map[r.crew_user_id] = r
        else:
            for c in my_crews:
                if (c.pf_number and r.crew_id_str and c.pf_number.upper() == r.crew_id_str.upper()) or \
                   (c.mobile and r.cug and c.mobile == r.cug):
                    r.crew_user_id = c.id
                    counselling_map[c.id] = r
                    db.session.commit()
                    break

    # 3. Build comprehensive squad data with live compliance statuses
    squad_data = []
    # If records exist in CrewCounsellingRecord, use them as primary source to show all 24 fields
    processed_pfs = set()
    for r in records:
        comp = compute_overdue_status(r.last_footplate, r.safety_counselling, None)
        linked_user = User.query.get(r.crew_user_id) if r.crew_user_id else None
        
        # Apply filters
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

        squad_data.append({
            'record': r,
            'user': linked_user,
            'compliance': comp
        })
        if r.pf_no:
            processed_pfs.add(r.pf_no)
        if r.crew_id_str:
            processed_pfs.add(r.crew_id_str)

    # Also include any assigned crews not yet in CrewCounsellingRecord
    for c in my_crews:
        if (c.pf_number and c.pf_number in processed_pfs) or (c.username in processed_pfs):
            continue
        # Check or persist record so it has an actual database ID and complete bio-data
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
        
        # Apply filters
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
            if q_lower not in (rec.crew_name or '').lower() and                q_lower not in (rec.crew_id_str or '').lower() and                q_lower not in (rec.cug or '').lower() and                q_lower not in (rec.pf_no or '').lower():
                continue

        squad_data.append({
            'record': rec,
            'user': c,
            'compliance': comp
        })
        if rec.pf_no:
            processed_pfs.add(rec.pf_no)
        if rec.crew_id_str:
            processed_pfs.add(rec.crew_id_str)

    # 4. Calculate Division & Squad Compliance Metrics
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

    # 5. Pending messages & Recent inspections
    pending_messages = Message.query.filter(
        Message.recipient_id == cli.id,
        Message.status == 'PENDING_CLI_REVIEW'
    ).order_by(Message.created_at.desc()).all()

    recent_inspections = FootplateInspection.query.filter_by(cli_id=cli.id).order_by(FootplateInspection.inspection_date.desc()).limit(8).all()
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
        pending_messages=pending_messages,
        recent_inspections=recent_inspections,
        total_footplate_km=total_footplate_km,
        search_q=search_q,
        grade_filter=grade_filter,
        hq_filter=hq_filter,
        status_filter=status_filter,
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

    # 9 Critical Footplate Inspection Checkpoints & 5-Star Rating
    signal_call_out = request.form.get('signal_call_out', '').strip()
    brake_technique = request.form.get('brake_technique', '').strip()
    high_speed_tendency = request.form.get('high_speed_tendency', '').strip()
    pf_entry_speed = request.form.get('pf_entry_speed', '').strip()
    psr_tsr_observation = request.form.get('psr_tsr_observation', '').strip()
    alp_performance = request.form.get('alp_performance', '').strip()
    whistling_habit = request.form.get('whistling_habit', '').strip()
    bft_bpt_test = request.form.get('bft_bpt_test', '').strip()
    other_observations = request.form.get('other_observations', '').strip()
    safety_rating_val = request.form.get('safety_rating', '5').strip()
    try:
        safety_rating = int(safety_rating_val)
    except ValueError:
        safety_rating = 5

    try:
        kma = float(kma_str) if kma_str else 0.0
    except ValueError:
        kma = 0.0

    insp_date = parse_date_value(date_str) or date.today()

    crew = User.query.get(int(crew_id_val)) if crew_id_val and crew_id_val.isdigit() else None
    
    # Create inspection row with full 9 safety checkpoints & rating
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
        safety_rating=safety_rating
    )
    db.session.add(insp)

    # Compile 9-point summary for CLIMovement
    summary_obs = [f"Rating: {safety_rating}/5"]
    if signal_call_out: summary_obs.append(f"Signal: {signal_call_out}")
    if brake_technique: summary_obs.append(f"Brake: {brake_technique}")
    if high_speed_tendency: summary_obs.append(f"Speed: {high_speed_tendency}")
    if pf_entry_speed: summary_obs.append(f"PF/Yellow: {pf_entry_speed}")
    if psr_tsr_observation: summary_obs.append(f"PSR/TSR: {psr_tsr_observation}")
    if alp_performance: summary_obs.append(f"ALP: {alp_performance}")
    if whistling_habit: summary_obs.append(f"Whistle: {whistling_habit}")
    if bft_bpt_test: summary_obs.append(f"BFT/BPT: {bft_bpt_test}")
    if other_observations: summary_obs.append(f"Other: {other_observations}")

    # Sync to CLIMovement (90-day retention log)
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
    rec = None
    if crew:
        rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == crew.id) |
            (CrewCounsellingRecord.crew_id_str == crew.pf_number) |
            (CrewCounsellingRecord.cug == crew.mobile)
        ).first()
    if rec:
        rec.last_footplate = formatted_date
        rec.grade = grading
        if counselling_given:
            rec.safety_counselling = formatted_date
            rec.remarks = counselling_given

    db.session.commit()
    flash(f"Footplate Inspection on Train {train_no} logged successfully. Last Footplate date updated to {formatted_date}.", "success")
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
        flash(f"{counsel_type.capitalize()} Counselling logged for {rec.crew_name}. Status marked compliant as of {formatted_date}.", "success")
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
        
        # Sync to CLIMovement
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
        
        # Sync to CLIMovement
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

    # Sync to User model if linked
    if rec.crew_user:
        if rec.cug:
            rec.crew_user.mobile = rec.cug
        if rec.designation:
            rec.crew_user.sub_role = rec.designation
        if rec.crew_name:
            rec.crew_user.full_name = rec.crew_name

    db.session.commit()
    flash(f"24-field Bio-Data & Safety Record for {rec.crew_name} successfully updated!", "success")
    return redirect(url_for('supervisor.dashboard'))


# ---------------------------------------------------------------------------
# EXPORTS: 24-COLUMN EXCEL ROSTER & CREW BIO-DATA PDF
# ---------------------------------------------------------------------------

@supervisor_bp.route('/export-roster-excel')
def export_roster_excel():
    cli = User.query.get(session['user_id'])
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    # Query CLI's squad records
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


@supervisor_bp.route('/crew/<int:record_id>/export-pdf')
def export_crew_pdf(record_id):
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

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=28, rightMargin=28, topMargin=28, bottomMargin=28)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=TA_CENTER, textColor=colors.HexColor('#0D47A1'))
        elements.append(Paragraph("EASTERN RAILWAY &bull; HOWRAH DIVISION", title_style))
        elements.append(Paragraph("ELECTRIC OPERATION DEPARTMENT &bull; RUNNING CREW BIO-DATA & SAFETY SHEET", styles['Normal']))
        elements.append(Spacer(1, 10))

        data = [
            ["Crew Name:", rec.crew_name or 'N/A', "CMS Crew ID:", rec.crew_id_str or 'N/A'],
            ["Designation:", rec.designation or 'ALP', "Lobby / HQ:", rec.crew_hq or 'HWH'],
            ["CUG Mobile:", rec.cug or 'N/A', "PF No / HRMS:", rec.pf_no or 'N/A'],
            ["Safety Grade:", rec.grade or 'A', "Nominated CLI:", rec.cli_name or 'CLI/HWH'],
            ["Last Footplate:", rec.last_footplate or 'N/A', "Technical Counselling:", rec.technical_counselling or 'N/A'],
            ["Safety Counselling:", rec.safety_counselling or 'N/A', "Verified By:", rec.counselling_verified_by or 'N/A'],
            ["Last SPM Check:", rec.last_spm_check or 'N/A', "Last CVVRS Check:", rec.last_cvvrs_check or 'N/A'],
            ["BA Fail History:", rec.ba_fail_history or 'Nil', "SPAD History:", rec.spad_history or 'Nil'],
            ["Mobile Habit:", rec.mobile_habit or 'Normal', "DA Case:", rec.da_case or 'Nil'],
            ["Family Issue:", rec.family_issue or 'Nil', "Health Issue:", rec.health_issue or 'Nil'],
            ["Baby < 6 Months:", rec.baby_below_6_months or 'No', "Accident Prone:", rec.accident_prone or 'No'],
            ["Safety Remarks:", Paragraph(rec.remarks or 'Satisfactory performance in section.', styles['Normal']), "", ""]
        ]
        t = Table(data, colWidths=[110, 160, 110, 160])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ]))
        elements.append(t)
        doc.build(elements)
        buf.seek(0)
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f"BioData_{rec.crew_id_str}.pdf")
    except Exception:
        return render_template('crew/biodata_print.html', crew=crew_user, rec=rec, inspections=inspections)

@supervisor_bp.route('/footplate/new', methods=['GET', 'POST'])
def new_footplate():
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all() if cli.sub_role == 'CLI' else User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()

    if request.method == 'POST':
        crew_id = request.form.get('crew_id')
        inspection_date_str = request.form.get('inspection_date')
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        from_stn = request.form.get('from_station', '').strip()
        to_stn = request.form.get('to_station', '').strip()
        departure_time = request.form.get('departure_time', '').strip()
        arrival_time = request.form.get('arrival_time', '').strip()
        grading = request.form.get('grading', 'A')
        footplate_km_str = request.form.get('footplate_km', '0').strip()
        aspects = request.form.get('aspects_covered', '').strip()
        deficiencies = request.form.get('deficiencies', '').strip()
        counselling_given = request.form.get('counselling_given', '').strip()

        try:
            footplate_km = float(footplate_km_str) if footplate_km_str else 0.0
        except ValueError:
            footplate_km = 0.0

        if not crew_id or not train_no or not loco_no:
            flash('Crew, Train No., and Loco No. are mandatory.', 'danger')
            return redirect(url_for('supervisor.new_footplate'))

        try:
            insp_date = datetime.strptime(inspection_date_str, '%Y-%m-%d').date() if inspection_date_str else date.today()
        except:
            insp_date = date.today()

        inspection = FootplateInspection(
            cli_id=cli.id,
            crew_id=int(crew_id),
            inspection_date=insp_date,
            train_no=train_no,
            loco_no=loco_no,
            from_station=from_stn,
            to_station=to_stn,
            departure_time=departure_time,
            arrival_time=arrival_time,
            grading=grading,
            footplate_km=footplate_km,
            aspects_covered=aspects,
            deficiencies=deficiencies,
            counselling_given=counselling_given
        )
        db.session.add(inspection)

        # Sync to CLIMovement (90-day retention log)
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
            observations_irregularities=aspects,
            corrective_action=counselling_given,
            remarks=deficiencies
        )
        db.session.add(cli_mov)

        # Sync to CrewCounsellingRecord
        formatted_date = insp_date.strftime('%d-%m-%Y')
        if crew_obj:
            c_rec = CrewCounsellingRecord.query.filter(
                (CrewCounsellingRecord.crew_user_id == crew_obj.id) |
                (CrewCounsellingRecord.crew_id_str == crew_obj.pf_number) |
                (CrewCounsellingRecord.cug == crew_obj.mobile)
            ).first()
            if c_rec:
                c_rec.last_footplate = formatted_date
                c_rec.grade = grading
                if counselling_given:
                    c_rec.safety_counselling = formatted_date

        db.session.commit()

        flash(f'Footplate inspection and counselling for crew logged successfully (Grade: {grading})!', 'success')
        return redirect(url_for('supervisor.dashboard'))

    return render_template('supervisor/footplate.html', my_crews=my_crews)


@supervisor_bp.route('/messages/<int:message_id>/action', methods=['POST'])
def handle_message(message_id):
    cli = User.query.get(session['user_id'])
    msg = Message.query.get_or_404(message_id)
    action = request.form.get('action') # 'forward' or 'resolve'
    remarks = request.form.get('cli_remarks', '').strip()

    msg.cli_remarks = remarks
    if action == 'forward':
        # Forward to Officers
        officers = User.query.filter_by(role='officer').all()
        target_officer_id = request.form.get('officer_id')
        
        msg.status = 'FORWARDED_TO_OFFICER'
        msg.forwarded_by_cli_id = cli.id
        if target_officer_id:
            msg.recipient_id = int(target_officer_id)
        else:
            # Default to Sr. DEE(OP)/HWH if not specified
            sr_dee = User.query.filter_by(username='Sr. DEE(OP)/HWH').first()
            if sr_dee:
                msg.recipient_id = sr_dee.id

        db.session.commit()
        flash('Crew message approved and forwarded to Officers for necessary action.', 'success')

    elif action == 'resolve':
        msg.status = 'RESOLVED_BY_CLI'
        msg.is_read = True

        # Reply directly back to crew
        reply = Message(
            sender_id=cli.id,
            recipient_id=msg.sender_id,
            parent_id=msg.id,
            subject=f"RE: {msg.subject} [Resolved by CLI]",
            body=remarks,
            message_type='CLI_TO_CREW',
            status='DELIVERED',
            is_read=False
        )
        db.session.add(reply)
        db.session.commit()
        flash('Message resolved locally and response sent to the Crew.', 'info')

    return redirect(url_for('supervisor.dashboard'))


@supervisor_bp.route('/instruct-crews', methods=['GET', 'POST'])
def instruct_crews():
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all() if cli.sub_role == 'CLI' else User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()

    if request.method == 'POST':
        target = request.form.get('target') # 'ALL' or specific crew_id
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()

        if not subject or not body:
            flash('Subject and Instructions cannot be blank.', 'danger')
            return redirect(url_for('supervisor.instruct_crews'))

        if target == 'ALL':
            for c in my_crews:
                msg = Message(
                    sender_id=cli.id,
                    recipient_id=c.id,
                    subject=subject,
                    body=body,
                    message_type='CLI_TO_CREW',
                    status='DELIVERED',
                    is_read=False
                )
                db.session.add(msg)
            flash(f'Instructions broadcasted to all {len(my_crews)} assigned running staff!', 'success')
        else:
            msg = Message(
                sender_id=cli.id,
                recipient_id=int(target),
                subject=subject,
                body=body,
                message_type='CLI_TO_CREW',
                status='DELIVERED',
                is_read=False
            )
            db.session.add(msg)
            flash('Instruction sent to selected crew.', 'success')

        db.session.commit()
        return redirect(url_for('supervisor.dashboard'))

    return render_template('supervisor/instruct_crews.html', my_crews=my_crews)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
#  CREW SAFETY & COUNSELLING MANAGEMENT (CLI EXCLUSIVE EDIT)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@supervisor_bp.route('/counselling')
def counselling():
    """CLI view of their assigned squad's counselling & safety monitoring register."""
    cli = User.query.get(session['user_id'])
    hq_filter = request.args.get('hq', 'ALL')
    grade_filter = request.args.get('grade', 'ALL')
    search_q = request.args.get('q', '').strip()

    # Get my crews
    if cli.sub_role == 'CLI':
        my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all()
    else:
        my_crews = User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()

    crew_ids = [c.id for c in my_crews]
    crew_pfs = [c.pf_number for c in my_crews if c.pf_number]
    crew_mobiles = [c.mobile for c in my_crews if c.mobile]

    # Query counselling records for my squad, or by CLI name match
    query = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.crew_user_id.in_(crew_ids)) |
        (CrewCounsellingRecord.crew_id_str.in_(crew_pfs)) |
        (CrewCounsellingRecord.cug.in_(crew_mobiles)) |
        (CrewCounsellingRecord.cli_name.ilike(f'%{cli.full_name}%')) |
        (CrewCounsellingRecord.cli_name.ilike(f'%{cli.username}%'))
    )

    if hq_filter != 'ALL':
        query = query.filter(CrewCounsellingRecord.crew_hq == hq_filter)
    if grade_filter != 'ALL':
        query = query.filter(CrewCounsellingRecord.grade == grade_filter)
    if search_q:
        query = query.filter(
            (CrewCounsellingRecord.crew_name.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.crew_id_str.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.pf_no.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.cug.ilike(f'%{search_q}%'))
        )

    records = query.order_by(CrewCounsellingRecord.grade.asc(), CrewCounsellingRecord.crew_name.asc()).all()

    return render_template(
        'supervisor/counselling.html',
        cli=cli,
        records=records,
        hq_filter=hq_filter,
        grade_filter=grade_filter,
        search_q=search_q,
        total=len(records)
    )


@supervisor_bp.route('/counselling/<int:record_id>/edit', methods=['GET', 'POST'])
def edit_counselling(record_id):
    """CLI edit screen for a specific crew counselling & safety monitoring record."""
    cli = User.query.get(session['user_id'])
    rec = CrewCounsellingRecord.query.get_or_404(record_id)
    lobbies = Lobby.query.order_by(Lobby.code).all()

    if request.method == 'POST':
        # Update all 25 fields editable by CLI
        rec.cli_name = request.form.get('cli_name', cli.full_name).strip()
        rec.crew_hq = request.form.get('crew_hq', '').strip().upper()
        rec.cug = request.form.get('cug', '').strip()
        rec.designation = request.form.get('designation', '').strip().upper()
        rec.designation_since = request.form.get('designation_since', '').strip()
        rec.pf_no = request.form.get('pf_no', '').strip()
        rec.grade = request.form.get('grade', 'A').strip().upper()

        rec.last_footplate = request.form.get('last_footplate', '').strip()
        rec.technical_counselling = request.form.get('technical_counselling', '').strip()
        rec.safety_counselling = request.form.get('safety_counselling', '').strip()
        rec.counselling_verified_by = request.form.get('counselling_verified_by', '').strip()

        rec.last_spm_check = request.form.get('last_spm_check', '').strip()
        rec.last_cvvrs_check = request.form.get('last_cvvrs_check', '').strip()

        rec.ba_fail_history = request.form.get('ba_fail_history', 'NA').strip()
        rec.mobile_habit = request.form.get('mobile_habit', 'NA').strip()
        rec.spad_history = request.form.get('spad_history', 'NA').strip()
        rec.da_case = request.form.get('da_case', 'NA').strip()

        rec.family_issue = request.form.get('family_issue', 'NA').strip()
        rec.health_issue = request.form.get('health_issue', 'NA').strip()
        rec.baby_below_6_months = request.form.get('baby_below_6_months', 'No').strip()
        rec.accident_prone = request.form.get('accident_prone', 'No').strip()
        rec.remarks = request.form.get('remarks', '').strip()

        # Sync changes to linked User row if present
        if rec.crew_user:
            if rec.designation:
                rec.crew_user.sub_role = rec.designation
            if rec.cug:
                rec.crew_user.mobile = rec.cug
            if rec.pf_no and not rec.crew_user.pf_number:
                rec.crew_user.pf_number = rec.pf_no
            if rec.crew_hq:
                lobby_match = Lobby.query.filter_by(code=rec.crew_hq).first()
                if lobby_match:
                    rec.crew_user.lobby_id = lobby_match.id

        db.session.commit()
        flash(f'Counselling & Safety Record for {rec.crew_name} ({rec.crew_id_str}) updated successfully!', 'success')
        return redirect(url_for('supervisor.counselling'))

    return render_template(
        'supervisor/edit_counselling.html',
        cli=cli,
        rec=rec,
        lobbies=lobbies
    )


@supervisor_bp.route('/counselling/crew/<int:crew_user_id>/edit', methods=['GET', 'POST'])
def edit_crew_counselling(crew_user_id):
    """Direct shortcut from crew squad table to edit or create counselling record for a crew."""
    cli = User.query.get(session['user_id'])
    crew = User.query.get_or_404(crew_user_id)

    # Find existing record
    rec = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.crew_user_id == crew.id) |
        (CrewCounsellingRecord.crew_id_str == crew.pf_number) |
        (CrewCounsellingRecord.cug == crew.mobile)
    ).first()

    if not rec:
        # Create blank record for this crew
        rec = CrewCounsellingRecord(
            crew_id_str=crew.pf_number or crew.username,
            crew_user_id=crew.id,
            cli_name=cli.full_name,
            crew_name=crew.full_name,
            crew_hq=crew.lobby.code if crew.lobby else 'HWH',
            cug=crew.mobile or '',
            designation=crew.sub_role or 'ALP',
            pf_no=crew.pf_number or '',
            grade='A',
            ba_fail_history='NA',
            mobile_habit='NA',
            spad_history='NA',
            da_case='NA',
            family_issue='NA',
            health_issue='NA',
            baby_below_6_months='No',
            accident_prone='No'
        )
        db.session.add(rec)
        db.session.commit()

    return redirect(url_for('supervisor.edit_counselling', record_id=rec.id))


@supervisor_bp.route('/counselling-topic/new', methods=['GET', 'POST'])
def new_counselling_topic():
    cli = User.query.get(session['user_id'])
    officers = User.query.filter_by(role='officer').all()

    if request.method == 'POST':
        counselling_type = request.form.get('counselling_type', 'MONTHLY').strip().upper()
        month_year = request.form.get('month_year', '').strip()
        title = request.form.get('title', '').strip()
        rule_reference = request.form.get('rule_reference', '').strip()
        content = request.form.get('content', '').strip()
        case_analysis = request.form.get('case_analysis', '').strip()
        officer_id = request.form.get('officer_id')

        if not title or not content or not rule_reference:
            flash('Title, GR & SR Rule Reference, and Safety Instructions are mandatory.', 'danger')
            return redirect(url_for('supervisor.new_counselling_topic'))

        # Process safety check questions (up to 3 questions)
        questions = []
        for i in range(1, 4):
            q_text = request.form.get(f'q{i}_text', '').strip()
            if q_text:
                opt1 = request.form.get(f'q{i}_opt1', '').strip()
                opt2 = request.form.get(f'q{i}_opt2', '').strip()
                opt3 = request.form.get(f'q{i}_opt3', '').strip()
                opt4 = request.form.get(f'q{i}_opt4', '').strip()
                correct_idx = request.form.get(f'q{i}_correct', '0')
                try:
                    correct_idx = int(correct_idx)
                except ValueError:
                    correct_idx = 0
                
                options = [o for o in [opt1, opt2, opt3, opt4] if o]
                if len(options) >= 2:
                    questions.append({
                        'q': q_text,
                        'options': options,
                        'answer': correct_idx
                    })

        questions_json = json.dumps(questions) if questions else None

        # Process file attachment
        file = request.files.get('attachment')
        file_path = None
        if file and file.filename:
            fname = secure_filename(file.filename)
            file_path = f"counsel_{int(datetime.utcnow().timestamp())}_{fname}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], file_path))

        # Create topic with PENDING_APPROVAL status
        topic = CounsellingTopic(
            counselling_type=counselling_type,
            month_year=month_year if month_year else datetime.now().strftime('%B %Y'),
            topic_date=date.today(),
            title=title,
            content=content,
            case_analysis=case_analysis,
            rule_reference=rule_reference,
            file_path=file_path,
            status='PENDING_APPROVAL',
            proposed_by_id=cli.id,
            questions_json=questions_json
        )
        db.session.add(topic)
        db.session.commit()

        # Send notification to the designated officer
        if officer_id:
            try:
                officer_user = User.query.get(int(officer_id))
                if officer_user:
                    msg = Message(
                        sender_id=cli.id,
                        recipient_id=officer_user.id,
                        subject=f"[Approval Needed] {counselling_type.capitalize()} Counselling: {title}",
                        body=f"Chief Loco Inspector {cli.full_name} has drafted a new {counselling_type} Counselling topic referencing {rule_reference}. Please review, approve, and digitally sign for Division-wide circulation.",
                        message_type='CLI_TO_OFFICER',
                        status='DELIVERED',
                        is_read=False
                    )
                    db.session.add(msg)
                    db.session.commit()
            except Exception as e:
                pass

        flash(f'Safety Counselling topic "{title}" successfully drafted and forwarded to the Officer for digital review and approval!', 'success')
        return redirect(url_for('supervisor.my_counselling_topics'))

    return render_template('supervisor/new_counselling_topic.html', cli=cli, officers=officers)


@supervisor_bp.route('/my-counselling-topics')
def my_counselling_topics():
    cli = User.query.get(session['user_id'])
    topics = CounsellingTopic.query.filter_by(proposed_by_id=cli.id).order_by(CounsellingTopic.created_at.desc()).all()
    return render_template('supervisor/my_counselling_topics.html', cli=cli, topics=topics)


# ---------------------------------------------------------------------------
# CLI DAILY MOVEMENT & OPERATIONAL SUPERVISION (3-MONTH RETENTION)
# ---------------------------------------------------------------------------

@supervisor_bp.route('/movements')
def movements():
    cli = User.query.get(session['user_id'])
    activity_type = request.args.get('activity_type', 'ALL').strip()
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()
    q = request.args.get('q', '').strip()

    # Retention policy: 90 days active retention
    cutoff_date = date.today() - timedelta(days=90)
    
    query = CLIMovement.query.filter(
        CLIMovement.cli_id == cli.id,
        CLIMovement.activity_date >= cutoff_date
    )

    if activity_type != 'ALL' and activity_type:
        query = query.filter(CLIMovement.activity_type == activity_type)

    if date_from_str:
        d_from = parse_date_value(date_from_str)
        if d_from:
            query = query.filter(CLIMovement.activity_date >= d_from)

    if date_to_str:
        d_to = parse_date_value(date_to_str)
        if d_to:
            query = query.filter(CLIMovement.activity_date <= d_to)

    if q:
        q_wild = f"%{q}%"
        query = query.filter(
            (CLIMovement.crew_name_manual.ilike(q_wild)) |
            (CLIMovement.crew_id_str.ilike(q_wild)) |
            (CLIMovement.train_no.ilike(q_wild)) |
            (CLIMovement.loco_no.ilike(q_wild)) |
            (CLIMovement.location.ilike(q_wild)) |
            (CLIMovement.observations_irregularities.ilike(q_wild)) |
            (CLIMovement.corrective_action.ilike(q_wild))
        )

    movements_list = query.order_by(CLIMovement.activity_date.desc(), CLIMovement.created_at.desc()).all()

    # Metrics over last 90 days
    all_90d = CLIMovement.query.filter(
        CLIMovement.cli_id == cli.id,
        CLIMovement.activity_date >= cutoff_date
    ).all()

    total_movements = len(all_90d)
    total_fp_km = sum([m.footplate_km or 0.0 for m in all_90d if m.activity_type == 'Footplate Inspection'])
    spm_count = sum(1 for m in all_90d if m.activity_type == 'SPM Analysis')
    cvvrs_count = sum(1 for m in all_90d if m.activity_type == 'CVVRS Inspection')
    failure_count = sum(1 for m in all_90d if m.activity_type == 'Locomotive Failure Attendance')
    problem_count = sum(1 for m in all_90d if m.activity_type == 'Crew Problem Attendance')
    counsel_count = sum(1 for m in all_90d if m.activity_type == 'Crew Counselling')

    lobbies = Lobby.query.order_by(Lobby.code).all()
    my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all() if cli.sub_role == 'CLI' else User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()

    return render_template(
        'supervisor/movements.html',
        cli=cli,
        movements=movements_list,
        total_movements=total_movements,
        total_fp_km=round(total_fp_km, 1),
        spm_count=spm_count,
        cvvrs_count=cvvrs_count,
        failure_count=failure_count,
        problem_count=problem_count,
        counsel_count=counsel_count,
        cutoff_date=cutoff_date,
        lobbies=lobbies,
        my_crews=my_crews,
        current_activity_type=activity_type,
        current_date_from=date_from_str,
        current_date_to=date_to_str,
        current_q=q
    )


@supervisor_bp.route('/movements/new', methods=['GET', 'POST'])
def new_movement():
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).order_by(User.full_name).all() if cli.sub_role == 'CLI' else User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).order_by(User.full_name).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

    prefill_type = request.args.get('type', 'Footplate Inspection').strip()

    if request.method == 'POST':
        activity_type = request.form.get('activity_type', 'Footplate Inspection').strip()
        date_str = request.form.get('activity_date', '').strip()
        activity_date = parse_date_value(date_str) or date.today()

        lobby_id = request.form.get('lobby_id')
        location = request.form.get('location', '').strip()
        section_from = request.form.get('section_from', '').strip()
        section_to = request.form.get('section_to', '').strip()
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        departure_time = request.form.get('departure_time', '').strip()
        arrival_time = request.form.get('arrival_time', '').strip()

        fp_km_str = request.form.get('footplate_km', '0').strip()
        try:
            footplate_km = float(fp_km_str) if fp_km_str else 0.0
        except ValueError:
            footplate_km = 0.0

        crew_id_val = request.form.get('crew_id')
        crew_name_manual = request.form.get('crew_name_manual', '').strip()
        crew_id_str = request.form.get('crew_id_str', '').strip()
        crew_category = request.form.get('crew_category', '').strip()
        grading = request.form.get('grading', 'A').strip().upper()

        observations = request.form.get('observations_irregularities', '').strip()
        corrective = request.form.get('corrective_action', '').strip()
        remarks = request.form.get('remarks', '').strip()

        crew_obj = None
        if crew_id_val and crew_id_val.isdigit():
            crew_obj = User.query.get(int(crew_id_val))
            if crew_obj:
                if not crew_name_manual:
                    crew_name_manual = crew_obj.full_name
                if not crew_id_str:
                    crew_id_str = crew_obj.pf_number or crew_obj.username
                if not crew_category:
                    crew_category = crew_obj.sub_role

        movement = CLIMovement(
            cli_id=cli.id,
            activity_date=activity_date,
            activity_type=activity_type,
            lobby_id=int(lobby_id) if lobby_id and lobby_id.isdigit() else cli.lobby_id,
            location=location or (f"{section_from} - {section_to}" if section_from or section_to else 'Section'),
            section_from=section_from,
            section_to=section_to,
            train_no=train_no,
            loco_no=loco_no,
            footplate_km=footplate_km,
            departure_time=departure_time,
            arrival_time=arrival_time,
            crew_id=crew_obj.id if crew_obj else None,
            crew_name_manual=crew_name_manual,
            crew_id_str=crew_id_str,
            crew_category=crew_category,
            grading=grading,
            observations_irregularities=observations,
            corrective_action=corrective,
            remarks=remarks
        )
        db.session.add(movement)

        # Synchronize with FootplateInspection if Footplate
        if activity_type == 'Footplate Inspection' and crew_obj:
            fp_row = FootplateInspection(
                cli_id=cli.id,
                crew_id=crew_obj.id,
                inspection_date=activity_date,
                train_no=train_no,
                loco_no=loco_no,
                from_station=section_from,
                to_station=section_to,
                departure_time=departure_time,
                arrival_time=arrival_time,
                grading=grading,
                footplate_km=footplate_km,
                aspects_covered=observations,
                deficiencies=remarks,
                counselling_given=corrective
            )
            db.session.add(fp_row)

        # Update CrewCounsellingRecord dates if match found
        target_pf = (crew_obj.pf_number if crew_obj else crew_id_str) or ''
        c_rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == (crew_obj.id if crew_obj else -1)) |
            (CrewCounsellingRecord.crew_id_str == target_pf) |
            (CrewCounsellingRecord.pf_no == target_pf)
        ).first()
        if c_rec:
            d_formatted = activity_date.strftime("%d-%m-%Y")
            if activity_type == 'Footplate Inspection':
                c_rec.last_footplate = d_formatted
            elif activity_type == 'SPM Analysis':
                c_rec.last_spm_check = d_formatted
            elif activity_type == 'CVVRS Inspection':
                c_rec.last_cvvrs_check = d_formatted
            elif activity_type == 'Crew Counselling':
                c_rec.safety_counselling = d_formatted
            if grading:
                c_rec.grade = grading

        db.session.commit()
        flash(f'CLI Daily Activity [{activity_type}] on {activity_date} successfully recorded!', 'success')
        return redirect(url_for('supervisor.movements'))

    return render_template(
        'supervisor/movement_form.html',
        cli=cli,
        my_crews=my_crews,
        lobbies=lobbies,
        prefill_type=prefill_type,
        today_date=date.today().strftime('%Y-%m-%d')
    )


@supervisor_bp.route('/movements/<int:movement_id>/edit', methods=['GET', 'POST'])
def edit_movement(movement_id):
    cli = User.query.get(session['user_id'])
    movement = CLIMovement.query.get_or_404(movement_id)

    # Permission check: CLIs can edit only their own entries
    if movement.cli_id != cli.id and not cli.is_admin():
        flash('Unauthorized: You can only edit your own activity records.', 'danger')
        return redirect(url_for('supervisor.movements'))

    my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).order_by(User.full_name).all() if cli.sub_role == 'CLI' else User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).order_by(User.full_name).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

    if request.method == 'POST':
        movement.activity_type = request.form.get('activity_type', movement.activity_type).strip()
        date_str = request.form.get('activity_date', '').strip()
        movement.activity_date = parse_date_value(date_str) or movement.activity_date

        lobby_id = request.form.get('lobby_id')
        if lobby_id and lobby_id.isdigit():
            movement.lobby_id = int(lobby_id)
        
        movement.location = request.form.get('location', '').strip()
        movement.section_from = request.form.get('section_from', '').strip()
        movement.section_to = request.form.get('section_to', '').strip()
        movement.train_no = request.form.get('train_no', '').strip()
        movement.loco_no = request.form.get('loco_no', '').strip()
        movement.departure_time = request.form.get('departure_time', '').strip()
        movement.arrival_time = request.form.get('arrival_time', '').strip()

        fp_km_str = request.form.get('footplate_km', '0').strip()
        try:
            movement.footplate_km = float(fp_km_str) if fp_km_str else 0.0
        except ValueError:
            pass

        crew_id_val = request.form.get('crew_id')
        if crew_id_val and crew_id_val.isdigit():
            crew_obj = User.query.get(int(crew_id_val))
            if crew_obj:
                movement.crew_id = crew_obj.id
                movement.crew_name_manual = crew_obj.full_name
                movement.crew_id_str = crew_obj.pf_number or crew_obj.username
                movement.crew_category = crew_obj.sub_role
        else:
            movement.crew_name_manual = request.form.get('crew_name_manual', movement.crew_name_manual).strip()
            movement.crew_id_str = request.form.get('crew_id_str', movement.crew_id_str).strip()
            movement.crew_category = request.form.get('crew_category', movement.crew_category).strip()

        movement.grading = request.form.get('grading', movement.grading).strip().upper()
        movement.observations_irregularities = request.form.get('observations_irregularities', '').strip()
        movement.corrective_action = request.form.get('corrective_action', '').strip()
        movement.remarks = request.form.get('remarks', '').strip()
        # Preserves officer_remarks and officer_remarked_by_id!

        db.session.commit()
        flash('CLI Daily Activity record updated successfully.', 'success')
        return redirect(url_for('supervisor.movements'))

    return render_template(
        'supervisor/movement_edit.html',
        cli=cli,
        movement=movement,
        my_crews=my_crews,
        lobbies=lobbies
    )


@supervisor_bp.route('/movements/<int:movement_id>/delete', methods=['POST'])
def delete_movement(movement_id):
    cli = User.query.get(session['user_id'])
    movement = CLIMovement.query.get_or_404(movement_id)
    if movement.cli_id != cli.id and not cli.is_admin():
        flash('Unauthorized: You can only remove your own activity records.', 'danger')
        return redirect(url_for('supervisor.movements'))

    db.session.delete(movement)
    db.session.commit()
    flash('Activity record removed from daily log.', 'info')
    return redirect(url_for('supervisor.movements'))

@supervisor_bp.route('/message/<int:message_id>/action', methods=['POST'])
def action_message(message_id):
    """Mark an operational notice / memo actioned by CLI supervisor."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    cli = User.query.get(session['user_id'])
    from models import Message
    msg = Message.query.get_or_404(message_id)
    action = request.form.get('action')
    remarks = request.form.get('cli_remarks', '').strip()
    
    if action == 'resolve':
        msg.status = 'resolved'
    elif action == 'forward':
        msg.status = 'forwarded'
        msg.forwarded_by_cli_id = cli.id
    msg.action_remarks = remarks
    db.session.commit()
    flash(f"Message #{msg.id} successfully {msg.status}.", "success")
    return redirect(url_for('supervisor.dashboard'))


# ---------------------------------------------------------------------------
# SQUAD TRAINING & PERIODIC MEDICAL EXAMINATION (PME)
# ---------------------------------------------------------------------------

@supervisor_bp.route('/training-medical')
def training_medical():
    """Squad Training & Medical (PME) Monitoring Console for CLI."""
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id).order_by(User.full_name).all()
    crew_ids = [c.id for c in my_crews]

    today = date.today()
    due_threshold = today + timedelta(days=30)

    trainings = []
    medicals = []
    overdue_tr = 0
    due_tr = 0
    overdue_pme = 0
    due_pme = 0

    if crew_ids:
        from models import MedicalRecord
        trainings = TrainingRecord.query.filter(TrainingRecord.crew_id.in_(crew_ids)).order_by(TrainingRecord.due_date.asc()).all()
        medicals = MedicalRecord.query.filter(MedicalRecord.crew_id.in_(crew_ids)).order_by(MedicalRecord.due_date.asc()).all()

        for t in trainings:
            if t.due_date < today:
                overdue_tr += 1
            elif t.due_date <= due_threshold:
                due_tr += 1

        for m in medicals:
            if m.due_date < today:
                overdue_pme += 1
            elif m.due_date <= due_threshold:
                due_pme += 1

    return render_template(
        'supervisor/training_medical.html',
        cli=cli,
        my_crews=my_crews,
        trainings=trainings,
        medicals=medicals,
        overdue_tr=overdue_tr,
        due_tr=due_tr,
        overdue_pme=overdue_pme,
        due_pme=due_pme
    )


@supervisor_bp.route('/training-medical/record', methods=['POST'])
def record_training_medical():
    """Save squad training or PME record submitted by CLI."""
    cli = User.query.get(session['user_id'])
    crew_id = request.form.get('crew_id', type=int)
    record_type = request.form.get('record_type', '').upper()
    done_date_str = request.form.get('done_date', '')
    cert_no = request.form.get('certificate_no', '').strip()
    remarks = request.form.get('remarks', '').strip()

    crew = User.query.get_or_404(crew_id)
    if crew.cli_id != cli.id and not cli.is_admin():
        flash('Unauthorized: Crew member is not assigned to your squad.', 'danger')
        return redirect(url_for('supervisor.training_medical'))

    try:
        done_date = datetime.strptime(done_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        done_date = date.today()

    if record_type == 'PME':
        from models import MedicalRecord
        freq_years = request.form.get('frequency_years', 4, type=int)
        due_date = done_date + timedelta(days=freq_years * 365)
        fit_status = request.form.get('fitness_status', 'Fit A-One')
        hosp = request.form.get('hospital_name', 'Divisional Hospital HWH')

        pme = MedicalRecord(
            crew_id=crew.id,
            last_pme_date=done_date,
            due_date=due_date,
            fitness_status=fit_status,
            hospital_name=hosp,
            frequency_years=freq_years,
            certificate_no=cert_no,
            remarks=remarks
        )
        db.session.add(pme)
        db.session.commit()
        flash(f'PME record recorded for {crew.full_name} (Due: {due_date.strftime("%d-%b-%Y")}).', 'success')
    else:
        training_type = request.form.get('training_type', 'Refresher Course')
        institute = request.form.get('institute', 'ZRTI Bhuli')
        validity_years = 3
        if 'ABS' in training_type or 'Block' in training_type:
            validity_years = 0.5
        due_date = done_date + timedelta(days=int(validity_years * 365))

        rec = TrainingRecord(
            crew_id=crew.id,
            training_type=training_type,
            institute=institute,
            last_done_date=done_date,
            due_date=due_date,
            certificate_no=cert_no,
            remarks=remarks
        )
        db.session.add(rec)
        db.session.commit()
        flash(f'Training record recorded for {crew.full_name} (Due: {due_date.strftime("%d-%b-%Y")}).', 'success')

    return redirect(url_for('supervisor.training_medical'))


# ---------------------------------------------------------------------------
# SQUAD COUNSELLING LOGS & HISTORY
# ---------------------------------------------------------------------------

@supervisor_bp.route('/counselling-logs')
def counselling_logs():
    """Safety Counselling History and Register for CLI's Squad."""
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id).order_by(User.full_name).all()
    crew_ids = [c.id for c in my_crews]

    from models import CrewCounsellingLog
    logs = []
    if crew_ids:
        logs = CrewCounsellingLog.query.filter(CrewCounsellingLog.crew_id.in_(crew_ids)).order_by(CrewCounsellingLog.counselling_date.desc()).all()

    # Identify overdue crews (> 30 days without counselling)
    overdue_crews = [c for c in my_crews if c.counselling_status.get('is_overdue', False)]

    return render_template(
        'supervisor/counselling_logs.html',
        cli=cli,
        my_crews=my_crews,
        logs=logs,
        overdue_crews=overdue_crews
    )


@supervisor_bp.route('/counselling-logs/new', methods=['GET', 'POST'])
def new_counselling_log():
    """Record safety counselling session with a squad crew member."""
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id).order_by(User.full_name).all()
    preselect_crew_id = request.args.get('crew_id', type=int)
    topics = CounsellingTopic.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        from models import CrewCounsellingLog
        crew_id = request.form.get('crew_id', type=int)
        counselling_date_str = request.form.get('counselling_date', '')
        counselling_type = request.form.get('counselling_type', 'Regular Monthly')
        counselling_mode = request.form.get('counselling_mode', 'One-on-One')
        topic = request.form.get('topic', '').strip()
        location = request.form.get('location', 'Lobby').strip()
        cli_remarks = request.form.get('cli_remarks', '').strip()
        crew_response = request.form.get('crew_response', 'Understood and assured compliance.').strip()

        try:
            c_date = datetime.strptime(counselling_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            c_date = date.today()

        new_log = CrewCounsellingLog(
            cli_id=cli.id,
            crew_id=crew_id,
            counselling_date=c_date,
            counselling_type=counselling_type,
            counselling_mode=counselling_mode,
            topic=topic,
            location=location,
            cli_remarks=cli_remarks,
            crew_response=crew_response,
            is_acknowledged=True
        )
        db.session.add(new_log)
        db.session.commit()
        flash('Safety counselling session recorded successfully.', 'success')
        return redirect(url_for('supervisor.counselling_logs'))

    return render_template(
        'supervisor/counselling_log_form.html',
        cli=cli,
        my_crews=my_crews,
        preselect_crew_id=preselect_crew_id,
        topics=topics
    )


# ---------------------------------------------------------------------------
# SQUAD NOTICES & CIRCULAR ASSURANCE STATUS
# ---------------------------------------------------------------------------

@supervisor_bp.route('/notices-status')
def notices_status():
    """Monitor digital safety circular acknowledgements for squad members."""
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id).order_by(User.full_name).all()
    crew_ids = [c.id for c in my_crews]
    total_crew = len(my_crews)

    from models import NoticeAcknowledgement
    active_notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).limit(20).all()

    notice_cards = []
    for n in active_notices:
        ack_crew_ids = set()
        if crew_ids:
            acks = NoticeAcknowledgement.query.filter(
                NoticeAcknowledgement.notice_id == n.id,
                NoticeAcknowledgement.user_id.in_(crew_ids)
            ).all()
            ack_crew_ids = {a.user_id for a in acks}

        ack_count = len(ack_crew_ids)
        pending_count = max(0, total_crew - ack_count)
        pct = round((ack_count / total_crew * 100), 1) if total_crew > 0 else 100
        pending_crews = [c for c in my_crews if c.id not in ack_crew_ids]

        notice_cards.append({
            'notice': n,
            'acknowledged_count': ack_count,
            'pending_count': pending_count,
            'percentage': pct,
            'pending_crews': pending_crews
        })

    return render_template(
        'supervisor/notices_status.html',
        cli=cli,
        my_crews=my_crews,
        notice_cards=notice_cards
    )


# ---------------------------------------------------------------------------
# SQUAD UNUSUAL INCIDENTS REGISTER
# ---------------------------------------------------------------------------

@supervisor_bp.route('/incidents')
def incidents():
    """Unusual Incidents Register involving CLI's running staff or lobby."""
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id).all()
    crew_ids = [c.id for c in my_crews]

    search = request.args.get('search', '').strip()
    from models import UnusualIncident
    query = UnusualIncident.query

    if crew_ids:
        query = query.filter((UnusualIncident.crew_id.in_(crew_ids)) | (UnusualIncident.lobby_id == cli.lobby_id))
    elif cli.lobby_id:
        query = query.filter_by(lobby_id=cli.lobby_id)

    if search:
        query = query.filter(
            UnusualIncident.incident_number.ilike(f'%{search}%') |
            UnusualIncident.section.ilike(f'%{search}%') |
            UnusualIncident.train_no.ilike(f'%{search}%')
        )

    incidents_list = query.order_by(UnusualIncident.incident_date.desc(), UnusualIncident.id.desc()).all()

    return render_template(
        'supervisor/incidents.html',
        cli=cli,
        incidents=incidents_list,
        search=search
    )


@supervisor_bp.route('/incidents/new', methods=['GET', 'POST'])
def new_incident():
    """Log an unusual incident for CLI's crew or lobby."""
    cli = User.query.get(session['user_id'])
    my_crews = User.query.filter_by(cli_id=cli.id).all()

    if request.method == 'POST':
        from models import UnusualIncident
        inc_date_str = request.form.get('incident_date')
        inc_time = request.form.get('incident_time', '')
        traction = request.form.get('traction_type', 'ELECTRIC')
        section = request.form.get('section', '').strip()
        station = request.form.get('station_location', '').strip()
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        category = request.form.get('incident_category', 'Other Operational')
        crew_id = request.form.get('crew_id', type=int)
        desc = request.form.get('description', '').strip()

        try:
            inc_date = datetime.strptime(inc_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            inc_date = date.today()

        count = UnusualIncident.query.count() + 1
        inc_no = f"INC/HWH/{date.today().year}/{count:03d}"

        new_inc = UnusualIncident(
            incident_number=inc_no,
            incident_date=inc_date,
            incident_time=inc_time,
            traction_type=traction,
            section=section,
            station_location=station,
            train_no=train_no,
            loco_no=loco_no,
            incident_category=category,
            crew_id=crew_id,
            lobby_id=cli.lobby_id,
            description=desc,
            status='LOGGED',
            reported_by_id=cli.id
        )
        db.session.add(new_inc)
        db.session.commit()
        flash(f'Unusual incident {inc_no} logged successfully.', 'success')
        return redirect(url_for('supervisor.incidents'))

    return render_template(
        'supervisor/incident_form.html',
        cli=cli,
        my_crews=my_crews
    )


@supervisor_bp.route('/incidents/<int:incident_id>')
def view_incident(incident_id):
    """View details of a specific unusual incident."""
    from models import UnusualIncident
    inc = UnusualIncident.query.get_or_404(incident_id)
    return redirect(url_for('supervisor.incidents'))

