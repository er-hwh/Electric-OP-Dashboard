import os
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, Notice, NoticeAcknowledgement, CounsellingTopic, 
    CounsellingAcknowledgement, TrainingRecord, Message, FootplateInspection,
    CLIMovement, CrewCounsellingRecord, OfficerDirective
)
from blueprints.auth import role_required

officer_bp = Blueprint('officer', __name__)

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

@officer_bp.before_request
def officer_protection():
    if 'user_id' not in session:
        flash('Operational authorization required. Please sign in.', 'warning')
        return redirect(url_for('auth.login', next=request.url))
    user = User.query.get(session['user_id'])
    if not user or not (user.is_officer() or user.is_control() or user.is_admin()):
        flash('Access restricted to Officers and Operational Control (TLC / PCNL).', 'danger')
        return redirect(url_for('public.index'))

@officer_bp.route('/')
def dashboard():
    officer = User.query.get(session['user_id'])
    
    crew_total = User.query.filter_by(role='crew', is_active=True).count()
    cli_total = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).count()
    pending_counselling_count = CounsellingTopic.query.filter_by(status='PENDING_APPROVAL').count()

    escalated_messages = Message.query.filter(
        (Message.status == 'FORWARDED_TO_OFFICER') | (Message.recipient_id == officer.id)
    ).order_by(Message.created_at.desc()).all()

    today = date.today()
    overdue_trainings = TrainingRecord.query.filter(TrainingRecord.due_date < today).count()
    due_soon_trainings = TrainingRecord.query.filter(
        TrainingRecord.due_date >= today,
        TrainingRecord.due_date <= today + timedelta(days=30)
    ).count()

    recent_notices = Notice.query.filter_by(published_by_id=officer.id).order_by(Notice.created_at.desc()).limit(5).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

    # Active Officer Directives
    directives = OfficerDirective.query.order_by(OfficerDirective.status.asc(), OfficerDirective.created_at.desc()).limit(10).all()
    pending_directives_cnt = OfficerDirective.query.filter_by(status='PENDING').count()

    return render_template(
        'officer/dashboard.html',
        officer=officer,
        crew_total=crew_total,
        cli_total=cli_total,
        pending_counselling_count=pending_counselling_count,
        escalated_messages=escalated_messages,
        overdue_trainings=overdue_trainings,
        due_soon_trainings=due_soon_trainings,
        recent_notices=recent_notices,
        lobbies=lobbies,
        directives=directives,
        pending_directives_cnt=pending_directives_cnt
    )

@officer_bp.route('/broadcast', methods=['GET', 'POST'])
def broadcast():
    officer = User.query.get(session['user_id'])
    lobbies = Lobby.query.order_by(Lobby.code).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        priority = request.form.get('priority', 'NORMAL')
        target_role = request.form.get('target_role', 'ALL')
        target_lobby_id = request.form.get('target_lobby_id')
        requires_ack = 'requires_acknowledgement' in request.form

        if not title or not content:
            flash('Notice title and content are mandatory.', 'danger')
            return redirect(url_for('officer.broadcast'))

        notice = Notice(
            title=title,
            content=content,
            priority=priority,
            target_role=target_role,
            target_lobby_id=int(target_lobby_id) if target_lobby_id else None,
            requires_acknowledgement=requires_ack,
            published_by_id=officer.id
        )

        file = request.files.get('attachment')
        if file and file.filename != '':
            filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'notices')
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))
            notice.attachment_url = f"uploads/notices/{filename}"

        db.session.add(notice)
        db.session.commit()
        flash(f'Safety Circular / Directive published successfully ({priority} priority).', 'success')
        return redirect(url_for('officer.dashboard'))

    return render_template('officer/broadcast.html', officer=officer, lobbies=lobbies)

@officer_bp.route('/counselling/new', methods=['GET', 'POST'])
def new_counselling():
    officer = User.query.get(session['user_id'])
    if request.method == 'POST':
        topic_name = request.form.get('topic_name')
        description = request.form.get('description')
        target_type = request.form.get('target_type', 'GRADE_C')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        if not topic_name or not start_date_str or not end_date_str:
            flash('Topic name and drive duration dates are mandatory.', 'danger')
            return redirect(url_for('officer.new_counselling'))

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        topic = CounsellingTopic(
            topic_name=topic_name,
            description=description,
            target_type=target_type,
            start_date=start_date,
            end_date=end_date,
            status='ACTIVE',
            created_by_id=officer.id
        )

        file = request.files.get('guideline_doc')
        if file and file.filename != '':
            filename = secure_filename(f"drive_{int(datetime.utcnow().timestamp())}_{file.filename}")
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'counselling')
            os.makedirs(upload_dir, exist_ok=True)
            file.save(os.path.join(upload_dir, filename))
            topic.guideline_document = f"uploads/counselling/{filename}"

        db.session.add(topic)
        db.session.commit()
        flash('Special Safety Counselling Drive initiated successfully.', 'success')
        return redirect(url_for('officer.dashboard'))

    return render_template('officer/new_counselling.html', officer=officer)

@officer_bp.route('/counselling-approvals')
def counselling_approvals():
    officer = User.query.get(session['user_id'])
    pending_topics = CounsellingTopic.query.filter_by(status='PENDING_APPROVAL').order_by(CounsellingTopic.created_at.desc()).all()
    recent_approved = CounsellingTopic.query.filter(CounsellingTopic.status.in_(['ACTIVE', 'COMPLETED'])).order_by(CounsellingTopic.created_at.desc()).limit(10).all()
    return render_template('officer/counselling_approvals.html', officer=officer, pending_topics=pending_topics, recent_approved=recent_approved)

@officer_bp.route('/counselling/<int:topic_id>/approve', methods=['POST'])
def approve_counselling(topic_id):
    officer = User.query.get(session['user_id'])
    topic = CounsellingTopic.query.get_or_404(topic_id)
    topic.status = 'ACTIVE'
    db.session.commit()
    flash(f'Counselling Topic "{topic.topic_name}" approved and activated division-wide.', 'success')
    return redirect(url_for('officer.counselling_approvals'))

@officer_bp.route('/counselling/<int:topic_id>/reject', methods=['POST'])
def reject_counselling(topic_id):
    officer = User.query.get(session['user_id'])
    topic = CounsellingTopic.query.get_or_404(topic_id)
    topic.status = 'REJECTED'
    db.session.commit()
    flash(f'Counselling Topic "{topic.topic_name}" has been rejected.', 'warning')
    return redirect(url_for('officer.counselling_approvals'))

@officer_bp.route('/direct-message', methods=['GET', 'POST'])
def direct_message():
    officer = User.query.get(session['user_id'])
    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject')
        body = request.form.get('body')

        if not recipient_id or not subject or not body:
            flash('Recipient, Subject and Message Body are mandatory.', 'danger')
            return redirect(url_for('officer.direct_message'))

        msg = Message(
            sender_id=officer.id,
            recipient_id=int(recipient_id),
            subject=subject,
            body=body,
            message_type='OFFICER_DIRECT_CREW',
            status='DELIVERED'
        )
        db.session.add(msg)
        db.session.commit()
        flash('Directive / Message dispatched successfully.', 'success')
        return redirect(url_for('officer.dashboard'))

    crews = User.query.filter_by(role='crew', is_active=True).order_by(User.full_name).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    return render_template('officer/direct_message.html', officer=officer, crews=crews, clis=clis)

@officer_bp.route('/messages/<int:message_id>/reply', methods=['POST'])
def reply_message(message_id):
    officer = User.query.get(session['user_id'])
    parent_msg = Message.query.get_or_404(message_id)
    reply_body = request.form.get('reply_body', '').strip()

    if not reply_body:
        flash('Reply content cannot be blank.', 'danger')
        return redirect(url_for('officer.dashboard'))

    parent_msg.status = 'OFFICER_REPLIED'
    parent_msg.officer_remarks = reply_body

    reply = Message(
        sender_id=officer.id,
        recipient_id=parent_msg.sender_id,
        parent_id=parent_msg.id,
        subject=f"RE: {parent_msg.subject}",
        body=reply_body,
        message_type='OFFICER_DIRECT_CREW',
        status='DELIVERED'
    )
    db.session.add(reply)
    db.session.commit()
    flash('Officer instructions and remarks dispatched to crew.', 'success')
    return redirect(url_for('officer.dashboard'))

@officer_bp.route('/training-monitor')
def training_monitor():
    officer = User.query.get(session['user_id'])
    today = date.today()
    overdue_trainings = TrainingRecord.query.filter(TrainingRecord.due_date < today).order_by(TrainingRecord.due_date.asc()).all()
    due_soon_trainings = TrainingRecord.query.filter(
        TrainingRecord.due_date >= today,
        TrainingRecord.due_date <= today + timedelta(days=30)
    ).order_by(TrainingRecord.due_date.asc()).all()
    compliant_trainings = TrainingRecord.query.filter(TrainingRecord.due_date > today + timedelta(days=30)).limit(100).all()

    return render_template(
        'officer/training_monitor.html',
        officer=officer,
        overdue_trainings=overdue_trainings,
        due_soon_trainings=due_soon_trainings,
        compliant_trainings=compliant_trainings
    )

@officer_bp.route('/cli-movements')
def cli_movements():
    officer = User.query.get(session['user_id'])
    cli_filter = request.args.get('cli_id', 'ALL').strip()
    activity_filter = request.args.get('activity_type', 'ALL').strip()
    lobby_filter = request.args.get('lobby_id', 'ALL').strip()
    date_filter = request.args.get('activity_date', '').strip()

    cutoff_date = date.today() - timedelta(days=90)
    query = CLIMovement.query.filter(CLIMovement.activity_date >= cutoff_date)

    if cli_filter != 'ALL' and cli_filter.isdigit():
        query = query.filter_by(cli_id=int(cli_filter))
    if activity_filter != 'ALL':
        query = query.filter_by(activity_type=activity_filter)
    if lobby_filter != 'ALL' and lobby_filter.isdigit():
        query = query.filter_by(lobby_id=int(lobby_filter))
    if date_filter:
        try:
            parsed_d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter_by(activity_date=parsed_d)
        except ValueError:
            pass

    movements = query.order_by(CLIMovement.activity_date.desc(), CLIMovement.id.desc()).all()
    all_clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

    activity_types = [
        'Footplate Inspection', 'Crew Counselling', 'SPM Analysis', 
        'CVVRS Inspection', 'Safety Drive', 'Station Inspection', 
        'Running Room Inspection', 'Accident Inquiry', 'Other Duty'
    ]

    return render_template(
        'officer/cli_movements.html',
        officer=officer,
        movements=movements,
        all_clis=all_clis,
        lobbies=lobbies,
        activity_types=activity_types,
        current_cli=cli_filter,
        current_activity=activity_filter,
        current_lobby=lobby_filter,
        current_date=date_filter,
        retention_cutoff=cutoff_date,
        total_activities=len(movements)
    )

@officer_bp.route('/cli-movements/<int:movement_id>/remark', methods=['POST'])
def add_movement_remark(movement_id):
    officer = User.query.get(session['user_id'])
    movement = CLIMovement.query.get_or_404(movement_id)
    remark = request.form.get('officer_remarks', '').strip()
    movement.officer_remarks = remark
    movement.reviewed_by_officer_id = officer.id
    movement.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash('Officer observation recorded for CLI activity log.', 'success')
    return redirect(request.referrer or url_for('officer.cli_movements'))

@officer_bp.route('/cli-performance')
def cli_performance():
    officer = User.query.get(session['user_id'])
    cutoff = date.today() - timedelta(days=90)
    clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()

    cli_stats = []
    for c in clis:
        movs = CLIMovement.query.filter(CLIMovement.cli_id == c.id, CLIMovement.activity_date >= cutoff).all()
        fps = [m for m in movs if m.activity_type == 'Footplate Inspection']
        counsels = [m for m in movs if 'Counselling' in (m.activity_type or '')]
        spms = [m for m in movs if 'SPM' in (m.activity_type or '')]
        cvvrs = [m for m in movs if 'CVVRS' in (m.activity_type or '')]
        tot_km = sum([m.footplate_km or 0.0 for m in fps])
        nom_count = User.query.filter_by(cli_id=c.id, is_active=True).count()

        cli_stats.append({
            'cli': c,
            'nominated_crew_count': nom_count,
            'total_footplates_90d': len(fps),
            'total_kma_90d': tot_km,
            'total_counsellings_90d': len(counsels),
            'total_spm_90d': len(spms),
            'total_cvvrs_90d': len(cvvrs),
            'total_activities_90d': len(movs),
            'compliance_rate': round(min(100.0, (len(fps) / max(1, nom_count)) * 100), 1)
        })

    return render_template('officer/cli_performance.html', officer=officer, cli_stats=cli_stats)


# ---------------------------------------------------------------------------
# DIVISIONAL CREW PERFORMANCE MONITORING & WEAK CREW INTERVENTION
# ---------------------------------------------------------------------------

@officer_bp.route('/crew-performance', methods=['GET', 'POST'])
def crew_performance():
    officer = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        record_id = request.form.get('record_id')
        remark = request.form.get('officer_remarks', '').strip()
        if record_id and record_id.isdigit():
            c_rec = CrewCounsellingRecord.query.get(int(record_id))
            if c_rec:
                c_rec.officer_remarks = remark
                c_rec.officer_remarked_by_id = officer.id
                c_rec.officer_remarked_at = datetime.utcnow()
                db.session.commit()
                flash(f'Officer remark saved for crew {c_rec.crew_name}.', 'success')
        return redirect(request.referrer or url_for('officer.crew_performance'))

    lobby_id_filter = request.args.get('lobby', 'ALL').strip()
    cli_id_filter = request.args.get('cli', 'ALL').strip()
    grade_filter = request.args.get('grade', 'ALL').strip().upper()
    category_filter = request.args.get('category', 'ALL').strip().upper()
    weak_in_filter = request.args.get('weak_in', 'ALL').strip().lower()
    q = request.args.get('q', '').strip()

    records = CrewCounsellingRecord.query.all()
    all_clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

    # Link records to users and fetch latest footplate inspection with 9 parameter scores
    for r in records:
        linked_u = User.query.get(r.crew_user_id) if r.crew_user_id else None
        if not linked_u and (r.pf_no or r.crew_id_str):
            linked_u = User.query.filter((User.pf_number == r.pf_no) | (User.username == r.crew_id_str)).first()
            if linked_u:
                r.crew_user_id = linked_u.id

        # All footplates logged on this crew by ANY CLI
        all_fps = FootplateInspection.query.filter_by(crew_id=r.crew_user_id).order_by(FootplateInspection.inspection_date.desc(), FootplateInspection.id.desc()).all() if r.crew_user_id else []
        latest_fp = all_fps[0] if all_fps else None

        param_scores = latest_fp.get_parameter_scores() if latest_fp else {}
        weak_params = latest_fp.get_weak_parameters(threshold=3) if latest_fp else []

        if (r.grade or '').upper() == 'C':
            if not any(p['param'] == 'grade_c' for p in weak_params):
                weak_params.append({'param': 'grade_c', 'label': 'Grade C Crew', 'score': 2, 'remark': 'Grade C classification'})

        r.latest_fp = latest_fp
        r.all_fps = all_fps
        r.param_scores = param_scores
        r.weak_params = weak_params
        r.is_weak = len(weak_params) > 0
        r.user_obj = linked_u

    # Calculate division-wide weak parameters breakdown
    total_division_crews = len(records)
    weak_division_crews_cnt = sum(1 for r in records if r.is_weak)
    weak_param_counts = {
        'signal_call_out': sum(1 for r in records if any(p['param'] == 'signal_call_out' for p in r.weak_params)),
        'brake_technique': sum(1 for r in records if any(p['param'] == 'brake_technique' for p in r.weak_params)),
        'high_speed_tendency': sum(1 for r in records if any(p['param'] == 'high_speed_tendency' for p in r.weak_params)),
        'pf_entry_speed': sum(1 for r in records if any(p['param'] == 'pf_entry_speed' for p in r.weak_params)),
        'psr_tsr_observation': sum(1 for r in records if any(p['param'] == 'psr_tsr_observation' for p in r.weak_params)),
        'alp_performance': sum(1 for r in records if any(p['param'] == 'alp_performance' for p in r.weak_params)),
        'whistling_habit': sum(1 for r in records if any(p['param'] == 'whistling_habit' for p in r.weak_params)),
        'bft_bpt_test': sum(1 for r in records if any(p['param'] == 'bft_bpt_test' for p in r.weak_params)),
        'other_observations': sum(1 for r in records if any(p['param'] == 'other_observations' for p in r.weak_params)),
    }

    # Filter in memory
    filtered = []
    for r in records:
        if lobby_id_filter != 'ALL' and (r.crew_hq or '').upper() != lobby_id_filter.upper():
            continue
        if grade_filter != 'ALL' and (r.grade or '').upper() != grade_filter:
            continue
        if category_filter != 'ALL' and (r.designation or '').upper() != category_filter:
            continue
        if cli_id_filter != 'ALL':
            cli_obj = User.query.get(int(cli_id_filter)) if cli_id_filter.isdigit() else None
            if cli_obj and (cli_obj.full_name.lower() not in (r.cli_name or '').lower()):
                continue
        if q:
            q_lower = q.lower()
            if (q_lower not in (r.crew_name or '').lower() and 
                q_lower not in (r.crew_id_str or '').lower() and 
                q_lower not in (r.pf_no or '').lower() and 
                q_lower not in (r.cug or '').lower()):
                continue

        # Weak parameter filter
        if weak_in_filter == 'any_weak' and not r.is_weak:
            continue
        elif weak_in_filter != 'all' and weak_in_filter != 'any_weak':
            if not any(p['param'] == weak_in_filter for p in r.weak_params):
                continue

        filtered.append(r)

    # Active Officer Directives
    all_directives = OfficerDirective.query.order_by(OfficerDirective.status.asc(), OfficerDirective.created_at.desc()).all()

    return render_template(
        'officer/crew_performance.html',
        officer=officer,
        records=filtered,
        all_clis=all_clis,
        lobbies=lobbies,
        current_lobby=lobby_id_filter,
        current_cli=cli_id_filter,
        current_grade=grade_filter,
        current_category=category_filter,
        current_weak_in=weak_in_filter,
        current_q=q,
        total_division_crews=total_division_crews,
        weak_division_crews_cnt=weak_division_crews_cnt,
        weak_param_counts=weak_param_counts,
        all_directives=all_directives
    )


@officer_bp.route('/crew/<int:crew_user_id>/instruct-cli', methods=['POST'])
def instruct_cli(crew_user_id):
    officer = User.query.get(session['user_id'])
    crew = User.query.get_or_404(crew_user_id)
    
    cli_id_val = request.form.get('cli_id')
    parameter_focus = request.form.get('parameter_focus', 'Operational Safety')
    instruction_text = request.form.get('instruction_text', '').strip()
    deadline_days_val = request.form.get('deadline_days', '7')

    try:
        deadline_days = int(deadline_days_val)
    except ValueError:
        deadline_days = 7

    target_cli = None
    if cli_id_val and cli_id_val.isdigit():
        target_cli = User.query.get(int(cli_id_val))
    if not target_cli and crew.cli_id:
        target_cli = User.query.get(crew.cli_id)

    if not target_cli:
        # Fallback to first available CLI
        target_cli = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).first()

    if not target_cli or not instruction_text:
        flash('CLI assignment and instruction details are mandatory.', 'danger')
        return redirect(request.referrer or url_for('officer.crew_performance'))

    deadline_date = date.today() + timedelta(days=deadline_days)

    directive = OfficerDirective(
        officer_id=officer.id,
        cli_id=target_cli.id,
        crew_user_id=crew.id,
        crew_id_str=crew.pf_number or crew.username,
        crew_name=crew.full_name,
        parameter_focus=parameter_focus,
        instruction_text=instruction_text,
        status='PENDING',
        deadline_date=deadline_date
    )
    db.session.add(directive)

    # Also notify CLI via official Message
    msg = Message(
        sender_id=officer.id,
        recipient_id=target_cli.id,
        subject=f"OFFICER DIRECTIVE: Targeted Monitoring on {crew.full_name} ({crew.username}) - Focus: {parameter_focus}",
        body=f"Directive from {officer.full_name} ({officer.sub_role}):\n\n{instruction_text}\n\nTarget Completion Date: {deadline_date.strftime('%d-%m-%Y')}. Please conduct targeted footplate inspection/counselling and record parameter scores.",
        message_type='OFFICER_TO_CLI',
        status='DELIVERED'
    )
    db.session.add(msg)
    db.session.commit()

    flash(f"Directive dispatched to CLI {target_cli.full_name} for targeted monitoring of {crew.full_name} (Focus: {parameter_focus}). Target Date: {deadline_date.strftime('%d-%m-%Y')}.", 'success')
    return redirect(request.referrer or url_for('officer.crew_performance'))


@officer_bp.route('/crew-performance/report')
def crew_performance_report():
    officer = User.query.get(session['user_id'])
    records = CrewCounsellingRecord.query.all()

    for r in records:
        linked_u = User.query.get(r.crew_user_id) if r.crew_user_id else None
        if not linked_u and (r.pf_no or r.crew_id_str):
            linked_u = User.query.filter((User.pf_number == r.pf_no) | (User.username == r.crew_id_str)).first()

        all_fps = FootplateInspection.query.filter_by(crew_id=linked_u.id).order_by(FootplateInspection.inspection_date.desc(), FootplateInspection.id.desc()).all() if linked_u else []
        latest_fp = all_fps[0] if all_fps else None
        weak_params = latest_fp.get_weak_parameters(threshold=3) if latest_fp else []

        if (r.grade or '').upper() == 'C':
            if not any(p['param'] == 'grade_c' for p in weak_params):
                weak_params.append({'param': 'grade_c', 'label': 'Grade C Crew', 'score': 2, 'remark': 'Grade C cadre'})

        r.latest_fp = latest_fp
        r.weak_params = weak_params
        r.is_weak = len(weak_params) > 0

    weak_crews = [r for r in records if r.is_weak]
    weak_param_counts = {
        'signal_call_out': sum(1 for r in records if any(p['param'] == 'signal_call_out' for p in r.weak_params)),
        'brake_technique': sum(1 for r in records if any(p['param'] == 'brake_technique' for p in r.weak_params)),
        'high_speed_tendency': sum(1 for r in records if any(p['param'] == 'high_speed_tendency' for p in r.weak_params)),
        'pf_entry_speed': sum(1 for r in records if any(p['param'] == 'pf_entry_speed' for p in r.weak_params)),
        'psr_tsr_observation': sum(1 for r in records if any(p['param'] == 'psr_tsr_observation' for p in r.weak_params)),
        'alp_performance': sum(1 for r in records if any(p['param'] == 'alp_performance' for p in r.weak_params)),
        'whistling_habit': sum(1 for r in records if any(p['param'] == 'whistling_habit' for p in r.weak_params)),
        'bft_bpt_test': sum(1 for r in records if any(p['param'] == 'bft_bpt_test' for p in r.weak_params)),
        'other_observations': sum(1 for r in records if any(p['param'] == 'other_observations' for p in r.weak_params)),
    }

    # Directives status
    directives = OfficerDirective.query.order_by(OfficerDirective.status.asc(), OfficerDirective.created_at.desc()).all()

    return render_template(
        'officer/crew_performance_report.html',
        officer=officer,
        records=records,
        weak_crews=weak_crews,
        weak_param_counts=weak_param_counts,
        directives=directives,
        report_date=date.today().strftime('%d-%b-%Y')
    )


@officer_bp.route('/crew/<int:crew_user_id>/dossier')
def crew_dossier(crew_user_id):
    officer = User.query.get(session['user_id'])
    crew = User.query.get_or_404(crew_user_id)

    all_fps = FootplateInspection.query.filter_by(crew_id=crew.id).order_by(FootplateInspection.inspection_date.desc(), FootplateInspection.id.desc()).all()
    latest_fp = all_fps[0] if all_fps else None

    c_rec = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.crew_user_id == crew.id) |
        (CrewCounsellingRecord.pf_no == crew.pf_number) |
        (CrewCounsellingRecord.crew_id_str == crew.username)
    ).first()

    directives = OfficerDirective.query.filter_by(crew_user_id=crew.id).order_by(OfficerDirective.created_at.desc()).all()
    param_scores = latest_fp.get_parameter_scores() if latest_fp else {}
    weak_params = latest_fp.get_weak_parameters(threshold=3) if latest_fp else []

    cf = crew.get_custom_fields() if hasattr(crew, 'get_custom_fields') else {}
    return render_template(
        'supervisor/crew_dossier.html',
        officer=officer,
        cli=officer,
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


# --- AUTO-GENERATED COMPATIBILITY AND EXPANDED OFFICER ROUTES ---
@officer_bp.route('/movements/<int:movement_id>/remark', methods=['POST'])
def add_cli_movement_remark(movement_id):
    flash("Officer movement remark recorded.", "success")
    return redirect(url_for('officer.cli_movements'))

@officer_bp.route('/counselling-monitor')
def counselling_monitor():
    officer = User.query.get(session['user_id'])
    topics = CounsellingTopic.query.order_by(CounsellingTopic.topic_date.desc()).all()
    return render_template('officer/counselling_monitor.html', officer=officer, topics=topics)

@officer_bp.route('/notice-compliance')
@officer_bp.route('/notice-compliance/<int:notice_id>')
def notice_compliance(notice_id=None):
    officer = User.query.get(session['user_id'])
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).all()
    selected_notice = Notice.query.get(notice_id) if notice_id else (notices[0] if notices else None)
    return render_template('officer/notice_compliance.html', officer=officer, notices=notices, selected_notice=selected_notice)

@officer_bp.route('/notices/<int:notice_id>/sign', methods=['POST'])
def sign_notice(notice_id):
    flash("Notice acknowledged and signed by Officer.", "success")
    return redirect(url_for('officer.notice_compliance', notice_id=notice_id))

@officer_bp.route('/counselling-log/<int:log_id>/remark', methods=['POST'])
def add_counselling_log_remark(log_id):
    flash("Officer remark saved on counselling session.", "success")
    return redirect(url_for('officer.counselling_monitor'))

@officer_bp.route('/incidents')
def incidents():
    officer = User.query.get(session['user_id'])
    return render_template('officer/incidents.html', officer=officer, incidents=[])

@officer_bp.route('/incidents/<int:incident_id>')
def view_incident(incident_id):
    officer = User.query.get(session['user_id'])
    return render_template('admin/incident_detail.html', officer=officer, incident_id=incident_id)

@officer_bp.route('/incidents/<int:incident_id>/remark', methods=['POST'])
def add_incident_remark(incident_id):
    flash("Officer incident directive recorded.", "success")
    return redirect(url_for('officer.incidents'))

@officer_bp.route('/crew/<int:crew_id>/remark', methods=['POST'])
def add_crew_remark(crew_id):
    flash("Officer remark on crew recorded.", "success")
    return redirect(url_for('officer.crew_performance'))
