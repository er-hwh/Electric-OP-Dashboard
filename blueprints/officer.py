from blueprints.reporting_helper import (
    get_crew_overview_stats, get_cli_crew_matrix, get_lobby_crew_matrix,
    filter_crews_query, export_crews_to_excel, export_crews_to_csv
)
import os
import json
from datetime import datetime, date, timedelta
from flask import send_file, Response, Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, Notice, NoticeAcknowledgement, CounsellingTopic, 
    CounsellingAcknowledgement, TrainingRecord, MedicalRecord, Message, FootplateInspection,
    CLIMovement, CrewCounsellingRecord, CrewCounsellingLog, GoogleSheetLink, UnusualIncident
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
    
    # Statistics
    crew_total = User.query.filter_by(role='crew', is_active=True).count()
    cli_total = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).count()
    
    # Pending Counselling Approvals submitted by CLIs
    pending_counselling_count = CounsellingTopic.query.filter_by(status='PENDING_APPROVAL').count()

    # Escalated messages pending review
    escalated_messages = Message.query.filter(
        (Message.status == 'FORWARDED_TO_OFFICER') | (Message.recipient_id == officer.id)
    ).order_by(Message.created_at.desc()).all()

    # Training due statistics
    today = date.today()
    overdue_trainings = TrainingRecord.query.filter(TrainingRecord.due_date < today).count()
    due_soon_trainings = TrainingRecord.query.filter(
        TrainingRecord.due_date >= today,
        TrainingRecord.due_date <= today + timedelta(days=30)
    ).count()

    # Recent notices
    recent_notices = Notice.query.filter_by(published_by_id=officer.id).order_by(Notice.created_at.desc()).limit(5).all()

    # Lobbies for filter
    lobbies = Lobby.query.order_by(Lobby.code).all()

    # Divisional Officer Hierarchy list
    officers_list = User.query.filter_by(role='officer', is_active=True).all()
    officers_list = sorted(officers_list, key=lambda o: o.officer_rank)

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
        officers_list=officers_list
    )

@officer_bp.route('/broadcast', methods=['GET', 'POST'])
def broadcast():
    officer = User.query.get(session['user_id'])
    lobbies = Lobby.query.order_by(Lobby.code).all()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'Notice')
        target_audience = request.form.get('target_audience', 'ALL')
        target_lobby_id = request.form.get('target_lobby_id')
        content = request.form.get('content', '').strip()
        is_urgent = bool(request.form.get('is_urgent'))

        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(url_for('officer.broadcast'))

        # File attachment
        file = request.files.get('attachment')
        file_path = None
        if file and file.filename:
            fname = secure_filename(file.filename)
            file_path = f"notice_{int(datetime.utcnow().timestamp())}_{fname}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], file_path))

        new_notice = Notice(
            title=title,
            category=category,
            content=content,
            file_path=file_path,
            target_audience=target_audience,
            target_lobby_id=int(target_lobby_id) if target_lobby_id else None,
            published_by_id=officer.id,
            is_urgent=is_urgent,
            is_active=True
        )
        db.session.add(new_notice)
        db.session.commit()

        flash('Directive / Notice successfully published and broadcasted!', 'success')
        return redirect(url_for('officer.dashboard'))

    return render_template('officer/broadcast.html', lobbies=lobbies)


@officer_bp.route('/counselling/new', methods=['GET', 'POST'])
def new_counselling():
    officer = User.query.get(session['user_id'])
    if request.method == 'POST':
        counselling_type = request.form.get('counselling_type', 'MONTHLY').strip().upper()
        month_year = request.form.get('month_year', '').strip()
        title = request.form.get('title', '').strip()
        rule_reference = request.form.get('rule_reference', '').strip()
        content = request.form.get('content', '').strip()
        case_analysis = request.form.get('case_analysis', '').strip()

        if not title or not content:
            flash('Title and Counselling points are required.', 'danger')
            return redirect(url_for('officer.new_counselling'))

        # Questions (up to 3)
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

        file = request.files.get('attachment')
        file_path = None
        if file and file.filename:
            fname = secure_filename(file.filename)
            file_path = f"counsel_{int(datetime.utcnow().timestamp())}_{fname}"
            file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], file_path))

        topic = CounsellingTopic(
            counselling_type=counselling_type,
            month_year=month_year if month_year else datetime.now().strftime('%B %Y'),
            topic_date=date.today(),
            title=title,
            content=content,
            case_analysis=case_analysis,
            rule_reference=rule_reference,
            file_path=file_path,
            status='APPROVED',
            issued_by_id=officer.id,
            proposed_by_id=officer.id,
            approved_by_id=officer.id,
            approval_date=datetime.utcnow(),
            officer_signature_remarks=f"Directly approved and digitally signed by [{officer.officer_level_title}] {officer.sub_role} ({officer.full_name})",
            questions_json=questions_json
        )
        db.session.add(topic)
        db.session.commit()

        flash(f'Safety Counselling Topic & Case Study issued and digitally signed by {officer.sub_role}!', 'success')
        return redirect(url_for('public.counselling'))

    return render_template('officer/new_counselling.html', officer=officer)


@officer_bp.route('/counselling-approvals')
def counselling_approvals():
    officer = User.query.get(session['user_id'])
    pending_topics = CounsellingTopic.query.filter_by(status='PENDING_APPROVAL').order_by(CounsellingTopic.created_at.desc()).all()
    recent_approved = CounsellingTopic.query.filter(
        CounsellingTopic.status.in_(['APPROVED', 'REJECTED'])
    ).order_by(CounsellingTopic.approval_date.desc(), CounsellingTopic.created_at.desc()).limit(15).all()

    return render_template(
        'officer/counselling_approvals.html',
        officer=officer,
        pending_topics=pending_topics,
        recent_approved=recent_approved
    )


@officer_bp.route('/counselling/<int:topic_id>/approve', methods=['POST'])
def approve_counselling(topic_id):
    officer = User.query.get(session['user_id'])
    topic = CounsellingTopic.query.get_or_404(topic_id)
    signature_remarks = request.form.get('signature_remarks', '').strip()

    if not signature_remarks:
        signature_remarks = f"Digitally endorsed and approved for Division-wide circulation by [{officer.officer_level_title}] {officer.sub_role} {officer.full_name}"

    topic.status = 'APPROVED'
    topic.approved_by_id = officer.id
    topic.approval_date = datetime.utcnow()
    topic.officer_signature_remarks = signature_remarks
    topic.issued_by_id = officer.id

    # Notify proposer CLI
    if topic.proposed_by_id:
        notify_msg = Message(
            sender_id=officer.id,
            recipient_id=topic.proposed_by_id,
            subject=f"[APPROVED & SIGNED] {topic.counselling_type.capitalize()} Counselling: {topic.title}",
            body=f"Your proposed {topic.counselling_type} counselling topic referencing {topic.rule_reference} has been approved and digitally signed by [{officer.officer_level_title}] {officer.sub_role} {officer.full_name}. Digital Endorsement: \"{signature_remarks}\". The topic is now live for Running Staff.",
            message_type='OFFICER_DIRECT_CREW',
            status='DELIVERED',
            is_read=False
        )
        db.session.add(notify_msg)

    db.session.commit()
    flash(f'Counselling Topic "{topic.title}" has been digitally approved, signed, and published for Running Staff!', 'success')
    return redirect(url_for('officer.counselling_approvals'))


@officer_bp.route('/counselling/<int:topic_id>/reject', methods=['POST'])
def reject_counselling(topic_id):
    officer = User.query.get(session['user_id'])
    topic = CounsellingTopic.query.get_or_404(topic_id)
    rejection_remarks = request.form.get('signature_remarks', '').strip()

    if not rejection_remarks:
        rejection_remarks = "Returned to Chief Loco Inspector for clarification/revision of GR & SR safety guidelines."

    topic.status = 'REJECTED'
    topic.approved_by_id = officer.id
    topic.approval_date = datetime.utcnow()
    topic.officer_signature_remarks = rejection_remarks

    # Notify proposer CLI
    if topic.proposed_by_id:
        notify_msg = Message(
            sender_id=officer.id,
            recipient_id=topic.proposed_by_id,
            subject=f"[REVISION REQUIRED] Counselling: {topic.title}",
            body=f"Your proposed {topic.counselling_type} counselling topic on {topic.title} was reviewed by {officer.sub_role} {officer.full_name} and returned for revision. Remarks: {rejection_remarks}",
            message_type='OFFICER_DIRECT_CREW',
            status='DELIVERED',
            is_read=False
        )
        db.session.add(notify_msg)

    db.session.commit()
    flash(f'Counselling Topic "{topic.title}" returned to CLI with revision instructions.', 'warning')
    return redirect(url_for('officer.counselling_approvals'))


@officer_bp.route('/direct-message', methods=['GET', 'POST'])
def direct_message():
    officer = User.query.get(session['user_id'])
    crews = User.query.filter_by(role='crew', is_active=True).order_by(User.full_name).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()

    if request.method == 'POST':
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()

        if not recipient_id or not subject or not body:
            flash('Recipient, Subject, and Message are required.', 'danger')
            return redirect(url_for('officer.direct_message'))

        msg = Message(
            sender_id=officer.id,
            recipient_id=int(recipient_id),
            subject=subject,
            body=body,
            message_type='OFFICER_DIRECT_CREW',
            status='DELIVERED',
            is_read=False
        )
        db.session.add(msg)
        db.session.commit()

        flash('Message successfully sent to running staff/CLI.', 'success')
        return redirect(url_for('officer.dashboard'))

    return render_template('officer/direct_message.html', crews=crews, clis=clis)


@officer_bp.route('/messages/<int:message_id>/reply', methods=['POST'])
def reply_message(message_id):
    officer = User.query.get(session['user_id'])
    msg = Message.query.get_or_404(message_id)
    officer_remarks = request.form.get('officer_remarks', '').strip()

    if officer_remarks:
        msg.officer_remarks = officer_remarks
        msg.status = 'OFFICER_REPLIED'
        msg.is_read = True

        # Also create notification reply to the original crew sender
        reply = Message(
            sender_id=officer.id,
            recipient_id=msg.sender_id,
            parent_id=msg.id,
            subject=f"RE: {msg.subject} [Officer Decision]",
            body=officer_remarks,
            message_type='OFFICER_DIRECT_CREW',
            status='DELIVERED',
            is_read=False
        )
        db.session.add(reply)
        db.session.commit()
        flash('Officer decision and instructions recorded and sent to crew and CLI.', 'success')

    return redirect(url_for('officer.dashboard'))


@officer_bp.route('/training-monitor')
def training_monitor():
    lobbies = Lobby.query.order_by(Lobby.code).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    status_filter = request.args.get('status', 'ALL').strip().upper()
    lobby_filter = request.args.get('lobby', 'ALL').strip()
    cli_filter = request.args.get('cli', 'ALL').strip()
    record_type = request.args.get('type', 'ALL').strip().upper() # ALL, TRAINING, PME
    course_filter = request.args.get('course', 'ALL').strip()
    q = request.args.get('q', '').strip()

    today = date.today()

    # Query Training Records
    trainings = []
    if record_type in ['ALL', 'TRAINING']:
        t_query = TrainingRecord.query.join(User, TrainingRecord.crew_id == User.id)
        if lobby_filter != 'ALL' and lobby_filter.isdigit():
            t_query = t_query.filter(User.lobby_id == int(lobby_filter))
        if cli_filter != 'ALL' and cli_filter.isdigit():
            t_query = t_query.filter(User.cli_id == int(cli_filter))
        if course_filter != 'ALL' and course_filter:
            t_query = t_query.filter(TrainingRecord.training_type.ilike(f"%{course_filter}%"))
        if status_filter == 'OVERDUE':
            t_query = t_query.filter(TrainingRecord.due_date < today)
        elif status_filter == 'DUE_SOON':
            t_query = t_query.filter(TrainingRecord.due_date >= today, TrainingRecord.due_date <= today + timedelta(days=30))
        elif status_filter == 'VALID':
            t_query = t_query.filter(TrainingRecord.due_date > today + timedelta(days=30))
        if q:
            q_wild = f"%{q}%"
            t_query = t_query.filter(
                (User.full_name.ilike(q_wild)) |
                (User.pf_number.ilike(q_wild)) |
                (User.mobile.ilike(q_wild))
            )
        trainings = t_query.order_by(TrainingRecord.due_date.asc()).all()

    # Query Medical / PME Records
    medicals = []
    if record_type in ['ALL', 'PME']:
        m_query = MedicalRecord.query.join(User, MedicalRecord.crew_id == User.id)
        if lobby_filter != 'ALL' and lobby_filter.isdigit():
            m_query = m_query.filter(User.lobby_id == int(lobby_filter))
        if cli_filter != 'ALL' and cli_filter.isdigit():
            m_query = m_query.filter(User.cli_id == int(cli_filter))
        if status_filter == 'OVERDUE':
            m_query = m_query.filter(MedicalRecord.due_date < today)
        elif status_filter == 'DUE_SOON':
            m_query = m_query.filter(MedicalRecord.due_date >= today, MedicalRecord.due_date <= today + timedelta(days=30))
        elif status_filter == 'VALID':
            m_query = m_query.filter(MedicalRecord.due_date > today + timedelta(days=30))
        if q:
            q_wild = f"%{q}%"
            m_query = m_query.filter(
                (User.full_name.ilike(q_wild)) |
                (User.pf_number.ilike(q_wild)) |
                (User.mobile.ilike(q_wild))
            )
        medicals = m_query.order_by(MedicalRecord.due_date.asc()).all()

    # Summary Metrics across division
    overdue_trainings = TrainingRecord.query.filter(TrainingRecord.due_date < today).count()
    due_trainings = TrainingRecord.query.filter(TrainingRecord.due_date >= today, TrainingRecord.due_date <= today + timedelta(days=30)).count()
    overdue_pmes = MedicalRecord.query.filter(MedicalRecord.due_date < today).count()
    due_pmes = MedicalRecord.query.filter(MedicalRecord.due_date >= today, MedicalRecord.due_date <= today + timedelta(days=30)).count()

    return render_template(
        'officer/training_monitor.html',
        trainings=trainings,
        medicals=medicals,
        lobbies=lobbies,
        clis=clis,
        overdue_trainings=overdue_trainings,
        due_trainings=due_trainings,
        overdue_pmes=overdue_pmes,
        due_pmes=due_pmes,
        current_status=status_filter,
        current_lobby=lobby_filter,
        current_cli=cli_filter,
        current_type=record_type,
        current_course=course_filter,
        current_q=q
    )


# ---------------------------------------------------------------------------
# CLI DAILY MOVEMENT MONITORING & PERFORMANCE (PHASE 3)
# ---------------------------------------------------------------------------

@officer_bp.route('/cli-movements')
def cli_movements():
    officer = User.query.get(session['user_id'])
    
    cli_id_filter = request.args.get('cli_id', 'ALL').strip()
    lobby_id_filter = request.args.get('lobby_id', 'ALL').strip()
    activity_type_filter = request.args.get('activity_type', 'ALL').strip()
    date_from_str = request.args.get('date_from', '').strip()
    date_to_str = request.args.get('date_to', '').strip()
    q = request.args.get('q', '').strip()

    # Scope to 90 days retention window
    retention_cutoff = date.today() - timedelta(days=90)
    query = CLIMovement.query.filter(CLIMovement.activity_date >= retention_cutoff)

    if cli_id_filter != 'ALL' and cli_id_filter.isdigit():
        query = query.filter(CLIMovement.cli_id == int(cli_id_filter))

    if lobby_id_filter != 'ALL' and lobby_id_filter.isdigit():
        query = query.filter(CLIMovement.lobby_id == int(lobby_id_filter))

    if activity_type_filter != 'ALL' and activity_type_filter:
        query = query.filter(CLIMovement.activity_type == activity_type_filter)

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

    movements = query.order_by(CLIMovement.activity_date.desc(), CLIMovement.created_at.desc()).all()

    # Summary metrics across entire division within retention window
    division_90d = CLIMovement.query.filter(CLIMovement.activity_date >= retention_cutoff).all()
    total_activities = len(division_90d)
    total_footplates = sum(1 for m in division_90d if m.activity_type == 'Footplate Inspection')
    total_fp_km = sum([m.footplate_km or 0.0 for m in division_90d if m.activity_type == 'Footplate Inspection'])
    total_spm = sum(1 for m in division_90d if m.activity_type == 'SPM Analysis')
    total_cvvrs = sum(1 for m in division_90d if m.activity_type == 'CVVRS Inspection')
    total_failures = sum(1 for m in division_90d if m.activity_type == 'Locomotive Failure Attendance')
    total_problems = sum(1 for m in division_90d if m.activity_type == 'Crew Problem Attendance')
    total_counsel = sum(1 for m in division_90d if m.activity_type == 'Crew Counselling')

    all_clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

    return render_template(
        'officer/cli_movements.html',
        officer=officer,
        movements=movements,
        total_activities=total_activities,
        total_footplates=total_footplates,
        total_fp_km=round(total_fp_km, 1),
        total_spm=total_spm,
        total_cvvrs=total_cvvrs,
        total_failures=total_failures,
        total_problems=total_problems,
        total_counsel=total_counsel,
        all_clis=all_clis,
        lobbies=lobbies,
        retention_cutoff=retention_cutoff,
        current_cli_id=cli_id_filter,
        current_lobby_id=lobby_id_filter,
        current_activity_type=activity_type_filter,
        current_date_from=date_from_str,
        current_date_to=date_to_str,
        current_q=q
    )


@officer_bp.route('/cli-movements/<int:movement_id>/remark', methods=['POST'])
def add_cli_movement_remark(movement_id):
    officer = User.query.get(session['user_id'])
    movement = CLIMovement.query.get_or_404(movement_id)
    remark = request.form.get('officer_remarks', '').strip()

    # Rule: Officers only modify officer_remarks field, CLI factual data is immutable by officers
    movement.officer_remarks = remark
    movement.officer_remarked_by_id = officer.id
    movement.officer_remarked_at = datetime.utcnow()
    db.session.commit()

    flash(f'Officer remark successfully recorded for CLI {movement.cli.full_name if movement.cli else "Supervisor"}.', 'success')
    return redirect(request.referrer or url_for('officer.cli_movements'))


@officer_bp.route('/cli-performance')
def cli_performance():
    officer = User.query.get(session['user_id'])
    clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    
    retention_cutoff = date.today() - timedelta(days=90)
    cli_perf_list = []

    for cli in clis:
        cli_movs = CLIMovement.query.filter(
            CLIMovement.cli_id == cli.id,
            CLIMovement.activity_date >= retention_cutoff
        ).all()

        fp_count = sum(1 for m in cli_movs if m.activity_type == 'Footplate Inspection')
        fp_km = sum([m.footplate_km or 0.0 for m in cli_movs if m.activity_type == 'Footplate Inspection'])
        spm_count = sum(1 for m in cli_movs if m.activity_type == 'SPM Analysis')
        cvvrs_count = sum(1 for m in cli_movs if m.activity_type == 'CVVRS Inspection')
        counsel_count = sum(1 for m in cli_movs if m.activity_type == 'Crew Counselling')
        failures_count = sum(1 for m in cli_movs if m.activity_type == 'Locomotive Failure Attendance')
        problems_count = sum(1 for m in cli_movs if m.activity_type == 'Crew Problem Attendance')

        assigned_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all()
        crew_count = len(assigned_crews)
        distinct_days = len(set([m.activity_date for m in cli_movs]))
        last_act = max([m.activity_date for m in cli_movs]) if cli_movs else None

        cli_perf_list.append({
            'cli': cli,
            'assigned_crews': crew_count,
            'total_movements': len(cli_movs),
            'fp_count': fp_count,
            'fp_km': round(fp_km, 1),
            'spm_count': spm_count,
            'cvvrs_count': cvvrs_count,
            'counsel_count': counsel_count,
            'failures_count': failures_count,
            'problems_count': problems_count,
            'active_days': distinct_days,
            'last_active': last_act
        })

    return render_template(
        'officer/cli_performance.html',
        officer=officer,
        cli_perf_list=cli_perf_list,
        retention_cutoff=retention_cutoff
    )


@officer_bp.route('/crew-performance', methods=['GET', 'POST'])
def crew_performance():
    officer = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Add officer remark to crew
        record_id = request.form.get('record_id')
        remark = request.form.get('officer_remarks', '').strip()
        if record_id and record_id.isdigit():
            c_rec = CrewCounsellingRecord.query.get(int(record_id))
            if c_rec:
                c_rec.officer_remarks = remark
                c_rec.officer_remarked_by_id = officer.id
                c_rec.officer_remarked_at = datetime.utcnow()
                db.session.commit()
                flash(f'Officer observation/remark saved for crew {c_rec.crew_name}.', 'success')
        return redirect(request.referrer or url_for('officer.crew_performance'))

    lobby_id_filter = request.args.get('lobby', 'ALL').strip()
    cli_id_filter = request.args.get('cli', 'ALL').strip()
    grade_filter = request.args.get('grade', 'ALL').strip().upper()
    category_filter = request.args.get('category', 'ALL').strip().upper()
    q = request.args.get('q', '').strip()

    records = CrewCounsellingRecord.query.all()
    all_clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

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
        filtered.append(r)

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
        current_q=q
    )


# ---------------------------------------------------------------------------
# PHASE 5: OFFICER NOTICE COMPLIANCE & DIGITAL SIGN-OFF
# ---------------------------------------------------------------------------

@officer_bp.route('/notice-compliance')
def notice_compliance():
    """Divisional Safety Notice & Circular Acknowledgement Oversight."""
    officer = User.query.get(session['user_id'])
    notice_id = request.args.get('notice_id')
    lobby_id = request.args.get('lobby_id', 'ALL')
    cli_id = request.args.get('cli_id', 'ALL')
    status_filter = request.args.get('status', 'ALL').strip().upper() # ALL, ACKNOWLEDGED, PENDING
    traction_filter = request.args.get('traction', 'ALL').strip().upper()
    q = request.args.get('q', '').strip()

    # Notices available for inspection
    notices_query = Notice.query.filter_by(is_active=True)
    if traction_filter != 'ALL' and traction_filter:
        notices_query = notices_query.filter_by(traction_type=traction_filter)
    active_notices = notices_query.order_by(Notice.created_at.desc()).all()

    selected_notice = None
    if notice_id and notice_id.isdigit():
        selected_notice = Notice.query.get(int(notice_id))
    elif active_notices:
        selected_notice = active_notices[0]

    crew_rows = []
    lobby_breakdown = []
    cli_breakdown = []
    stats = {'eligible': 0, 'acknowledged': 0, 'pending': 0, 'percentage': 0.0}

    lobbies = Lobby.query.order_by(Lobby.code).all()
    all_clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()

    if selected_notice:
        stats = selected_notice.get_compliance_stats()
        acked_map = {a.user_id: a for a in selected_notice.acknowledgements.all()}

        # Build crew rows
        crew_query = User.query.filter_by(role='crew', is_active=True)
        if selected_notice.target_lobby_id:
            crew_query = crew_query.filter_by(lobby_id=selected_notice.target_lobby_id)
        elif lobby_id != 'ALL' and lobby_id.isdigit():
            crew_query = crew_query.filter_by(lobby_id=int(lobby_id))

        if cli_id != 'ALL' and cli_id.isdigit():
            crew_query = crew_query.filter_by(cli_id=int(cli_id))

        if q:
            crew_query = crew_query.filter(
                (User.full_name.ilike(f"%{q}%")) |
                (User.username.ilike(f"%{q}%")) |
                (User.mobile.ilike(f"%{q}%")) |
                (User.pf_number.ilike(f"%{q}%"))
            )

        target_crews = crew_query.order_by(User.full_name).all()
        for c in target_crews:
            ack = acked_map.get(c.id)
            is_acked = ack is not None
            if status_filter == 'ACKNOWLEDGED' and not is_acked:
                continue
            if status_filter == 'PENDING' and is_acked:
                continue
            crew_rows.append({
                'crew': c,
                'is_acknowledged': is_acked,
                'ack': ack,
                'cli': c.nominated_cli
            })

        # Lobby breakdown
        for lob in lobbies:
            l_crews = User.query.filter_by(lobby_id=lob.id, role='crew', is_active=True).all()
            l_total = len(l_crews)
            if l_total == 0:
                continue
            l_acked = sum(1 for c in l_crews if c.id in acked_map)
            pct = round((l_acked / l_total) * 100, 1)
            lobby_breakdown.append({
                'lobby': lob,
                'total': l_total,
                'acknowledged': l_acked,
                'pending': l_total - l_acked,
                'percentage': pct
            })

        # CLI breakdown
        for cli in all_clis:
            squad = cli.assigned_crews.filter_by(is_active=True).all()
            s_total = len(squad)
            if s_total == 0:
                continue
            s_acked = sum(1 for c in squad if c.id in acked_map)
            pct = round((s_acked / s_total) * 100, 1)
            cli_breakdown.append({
                'cli': cli,
                'total': s_total,
                'acknowledged': s_acked,
                'pending': s_total - s_acked,
                'percentage': pct
            })

    return render_template(
        'officer/notice_compliance.html',
        officer=officer,
        active_notices=active_notices,
        selected_notice=selected_notice,
        crew_rows=crew_rows,
        lobby_breakdown=lobby_breakdown,
        cli_breakdown=cli_breakdown,
        stats=stats,
        lobbies=lobbies,
        all_clis=all_clis,
        current_notice_id=selected_notice.id if selected_notice else None,
        current_lobby=lobby_id,
        current_cli=cli_id,
        current_status=status_filter,
        current_traction=traction_filter,
        current_q=q
    )


@officer_bp.route('/notices/<int:notice_id>/sign', methods=['POST'])
def sign_notice(notice_id):
    """Officer digital signature / executive approval on safety circular."""
    officer = User.query.get(session['user_id'])
    if not (officer.is_officer() or officer.is_admin()):
        flash('Only Divisional Officers can digitally approve circulars.', 'danger')
        return redirect(url_for('officer.notice_compliance', notice_id=notice_id))

    notice = Notice.query.get_or_404(notice_id)
    remarks = request.form.get('officer_remarks', '').strip()

    notice.approved_by_id = officer.id
    notice.approval_date = datetime.utcnow()
    notice.officer_remarks = remarks or f"Digitally endorsed by {officer.full_name} ({officer.sub_role or 'Officer'}) for strict compliance."
    db.session.commit()

    flash(f'Safety Circular "{notice.title}" digitally approved with official executive stamp.', 'success')
    return redirect(url_for('officer.notice_compliance', notice_id=notice.id))


@officer_bp.route('/notices/<int:notice_id>/remind', methods=['POST'])
def remind_notice(notice_id):
    """Officer dispatches division-wide compliance alert to unacknowledged staff."""
    officer = User.query.get(session['user_id'])
    notice = Notice.query.get_or_404(notice_id)
    acked_user_ids = {a.user_id for a in notice.acknowledgements.all()}
    
    target_crews = User.query.filter_by(role='crew', is_active=True)
    if notice.target_lobby_id:
        target_crews = target_crews.filter_by(lobby_id=notice.target_lobby_id)
    unacked = [c for c in target_crews.all() if c.id not in acked_user_ids]

    sent_cnt = 0
    for c in unacked:
        msg = Message(
            sender_id=officer.id,
            recipient_id=c.id,
            subject=f"DIRECTIVE FROM {officer.sub_role or 'OFFICER'}: {notice.title[:60]}",
            body=(
                f"Running Staff {c.full_name} ({c.username}):\n\n"
                f"You have not yet digitally acknowledged Safety Circular '{notice.title}'. "
                f"Under Divisional Safety Regulations, compliance acknowledgement is mandatory. "
                f"Please open your running desk and complete acknowledgement immediately.\n\n"
                f"Signed: {officer.full_name}, {officer.sub_role or 'Divisional Officer'}, Howrah Division."
            ),
            status='SENT'
        )
        db.session.add(msg)
        sent_cnt += 1

    db.session.commit()
    flash(f'Direct executive compliance alert dispatched to {sent_cnt} unacknowledged running staff.', 'success')
    return redirect(url_for('officer.notice_compliance', notice_id=notice.id))


# ---------------------------------------------------------------------------
# PHASE 5: COUNSELLING OVERSIGHT & 30-DAY OVERDUE TRACKER
# ---------------------------------------------------------------------------

@officer_bp.route('/counselling-monitor')
def counselling_monitor():
    """Divisional Safety Counselling Oversight & 30-Day Overdue Tracker."""
    officer = User.query.get(session['user_id'])
    lobby_filter = request.args.get('lobby_id', 'ALL')
    cli_filter = request.args.get('cli_id', 'ALL')
    status_filter = request.args.get('status', 'ALL').strip().upper()
    q = request.args.get('q', '').strip()

    lobbies = Lobby.query.order_by(Lobby.code).all()
    all_clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    cli_name_map = {cli.id: cli.full_name for cli in all_clis}
    lobby_code_map = {lob.id: lob.code for lob in lobbies}

    crew_query = User.query.filter_by(role='crew', is_active=True)
    if lobby_filter != 'ALL' and lobby_filter.isdigit():
        crew_query = crew_query.filter_by(lobby_id=int(lobby_filter))
    if cli_filter != 'ALL' and cli_filter.isdigit():
        crew_query = crew_query.filter_by(cli_id=int(cli_filter))

    if q:
        crew_query = crew_query.filter(
            (User.full_name.ilike(f"%{q}%")) |
            (User.username.ilike(f"%{q}%")) |
            (User.mobile.ilike(f"%{q}%")) |
            (User.pf_number.ilike(f"%{q}%"))
        )

    all_crews = crew_query.all()
    total_crews = len(all_crews)

    # Pre-fetch all CrewCounsellingRecord and CrewCounsellingLog for instant in-memory resolution
    from blueprints.supervisor import parse_date_value

    all_recs = CrewCounsellingRecord.query.all()
    rec_by_user = {}
    rec_by_cug = {}
    rec_by_str = {}
    for r in all_recs:
        if r.crew_user_id:
            rec_by_user[r.crew_user_id] = r
        if r.cug:
            rec_by_cug[r.cug] = r
        if r.crew_id_str:
            rec_by_str[r.crew_id_str] = r

    all_logs = CrewCounsellingLog.query.order_by(CrewCounsellingLog.counselling_date.desc()).all()
    latest_log_by_crew = {}
    for l in all_logs:
        if l.crew_id not in latest_log_by_crew:
            latest_log_by_crew[l.crew_id] = l

    today = date.today()
    overdue_crews = []
    ok_count = 0
    overdue_count = 0
    crew_status_cache = {}

    from collections import defaultdict
    crew_by_cli = defaultdict(list)
    crew_by_lobby = defaultdict(list)

    for c in all_crews:
        last_d = None
        if c.id in latest_log_by_crew:
            last_d = latest_log_by_crew[c.id].counselling_date
        else:
            rec = rec_by_user.get(c.id) or rec_by_cug.get(c.mobile) or rec_by_str.get(c.username)
            if rec and rec.safety_counselling:
                last_d = parse_date_value(rec.safety_counselling)

        if not last_d:
            st = {'status': 'OVERDUE', 'days_ago': 999, 'days_elapsed': 999, 'is_overdue': True, 'badge': 'danger', 'last_date': None}
        else:
            days_ago = (today - last_d).days
            if days_ago > 30:
                st = {'status': 'OVERDUE', 'days_ago': days_ago, 'days_elapsed': days_ago, 'is_overdue': True, 'badge': 'danger', 'last_date': last_d}
            elif days_ago >= 25:
                st = {'status': 'DUE_SOON', 'days_ago': days_ago, 'days_elapsed': days_ago, 'is_overdue': False, 'badge': 'warning', 'last_date': last_d}
            else:
                st = {'status': 'OK', 'days_ago': days_ago, 'days_elapsed': days_ago, 'is_overdue': False, 'badge': 'success', 'last_date': last_d}

        crew_status_cache[c.id] = st
        if c.cli_id:
            crew_by_cli[c.cli_id].append(c)
        if c.lobby_id:
            crew_by_lobby[c.lobby_id].append(c)

        if st['status'] == 'OVERDUE':
            overdue_count += 1
            overdue_crews.append({
                'crew': c,
                'status': st,
                'cli_name': cli_name_map.get(c.cli_id, 'Unassigned'),
                'lobby_code': lobby_code_map.get(c.lobby_id, 'HWH')
            })
        else:
            ok_count += 1

    compliance_pct = round((ok_count / (total_crews or 1)) * 100, 1)

    # CLI Summary table (Instant via pre-grouped map)
    cli_summary = []
    for cli in all_clis:
        cli_crews = crew_by_cli.get(cli.id, [])
        if not cli_crews:
            continue
        c_ok = sum(1 for c in cli_crews if crew_status_cache.get(c.id, {}).get('status') != 'OVERDUE')
        c_over = len(cli_crews) - c_ok
        c_pct = round((c_ok / len(cli_crews)) * 100, 1)
        cli_summary.append({
            'cli_name': cli.full_name,
            'lobby': cli.lobby.code if cli.lobby else 'HWH',
            'total': len(cli_crews),
            'ok': c_ok,
            'overdue': c_over,
            'pct': c_pct
        })
    cli_summary.sort(key=lambda x: x['pct'], reverse=True)

    # Lobby Summary table (Instant via pre-grouped map)
    lobby_summary = []
    for lob in lobbies:
        lob_crews = crew_by_lobby.get(lob.id, [])
        if not lob_crews:
            continue
        l_ok = sum(1 for c in lob_crews if crew_status_cache.get(c.id, {}).get('status') != 'OVERDUE')
        l_over = len(lob_crews) - l_ok
        l_pct = round((l_ok / len(lob_crews)) * 100, 1)
        lobby_summary.append({
            'lobby_code': lob.code,
            'total': len(lob_crews),
            'ok': l_ok,
            'overdue': l_over,
            'pct': l_pct
        })
    lobby_summary.sort(key=lambda x: x['pct'], reverse=True)

    if status_filter in ['OK', 'VALID']:
        overdue_crews = []

    return render_template(
        'officer/counselling_monitor.html',
        officer=officer,
        total_crews=total_crews,
        ok_count=ok_count,
        overdue_count=overdue_count,
        compliance_pct=compliance_pct,
        cli_summary=cli_summary,
        lobby_summary=lobby_summary,
        overdue_crews=overdue_crews[:100],
        recent_logs=all_logs[:25],
        lobbies=lobbies,
        all_clis=all_clis,
        current_lobby=lobby_filter,
        current_cli=cli_filter,
        current_status=status_filter,
        current_q=q
    )


@officer_bp.route('/counselling-log/<int:log_id>/remark', methods=['POST'])
@officer_bp.route('/counselling-log/<int:log_id>/remark', methods=['POST'], endpoint='add_counselling_log_remark')
def remark_counselling_log(log_id):
    """Officer adds supervisory remark / directive on a CLI counselling log."""
    officer = User.query.get(session['user_id'])
    log = CrewCounsellingLog.query.get_or_404(log_id)
    remarks = request.form.get('officer_remarks', '').strip()

    if remarks:
        log.officer_remarks = remarks
        log.officer_remarked_by_id = officer.id
        log.officer_remarked_at = datetime.utcnow()
        db.session.commit()
        flash(f'Officer directive recorded on counselling session with {log.crew.full_name}.', 'success')
    return redirect(url_for('officer.counselling_monitor'))


# ---------------------------------------------------------------------------
# PHASE 6: OFFICER GOOGLE SHEETS & UNUSUAL INCIDENTS SURVEILLANCE
# ---------------------------------------------------------------------------

@officer_bp.route('/sheets', methods=['GET'])
def sheets():
    """View active Google Sheets accessible to officers."""
    user = User.query.get(session.get('user_id'))
    category = request.args.get('category', '').strip()
    traction = request.args.get('traction', '').strip()
    search = request.args.get('search', '').strip()

    query = GoogleSheetLink.query.filter_by(is_active=True)
    if category and category != 'ALL':
        query = query.filter_by(category=category)
    if traction and traction != 'ALL':
        query = query.filter(GoogleSheetLink.traction_type.in_([traction, 'BOTH']))
    if search:
        query = query.filter(
            db.or_(
                GoogleSheetLink.title.ilike(f'%{search}%'),
                GoogleSheetLink.description.ilike(f'%{search}%')
            )
        )

    all_sheets = [s for s in query.order_by(GoogleSheetLink.display_order.asc()).all() if s.is_accessible_by(user)]
    categories = [
        ('CLI_PERFORMANCE', 'CLI Performance & Monitoring'),
        ('CREW_MONITORING', 'Crew Monitoring & Grading'),
        ('TRAINING', 'Training & Refresher Master'),
        ('PME', 'Periodic Medical Examination (PME)'),
        ('SAFETY_MONITORING', 'Safety Drives & Counselling'),
        ('OPERATIONAL', 'Operational Punctuality & Logs'),
        ('GENERAL', 'General Administration & Other Links')
    ]
    return render_template(
        'officer/sheets.html',
        sheets=all_sheets,
        categories=categories,
        selected_category=category,
        selected_traction=traction,
        search=search
    )


@officer_bp.route('/incidents', methods=['GET'])
def incidents():
    """Officer Surveillance Desk for Unusual Incidents."""
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    traction = request.args.get('traction', '').strip()
    lobby_id = request.args.get('lobby_id', '').strip()
    section = request.args.get('section', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    search = request.args.get('search', '').strip()

    query = UnusualIncident.query
    if category and category != 'ALL':
        query = query.filter_by(incident_category=category)
    if status and status != 'ALL':
        query = query.filter_by(status=status)
    if traction and traction != 'ALL':
        query = query.filter(UnusualIncident.traction_type.in_([traction, 'BOTH']))
    if lobby_id and lobby_id != 'ALL':
        try:
            query = query.filter_by(lobby_id=int(lobby_id))
        except ValueError:
            pass
    if section:
        query = query.filter(UnusualIncident.section.ilike(f'%{section}%'))
    if date_from:
        d_from = parse_date_value(date_from)
        if d_from:
            query = query.filter(UnusualIncident.incident_date >= d_from)
    if date_to:
        d_to = parse_date_value(date_to)
        if d_to:
            query = query.filter(UnusualIncident.incident_date <= d_to)
    if search:
        query = query.filter(
            db.or_(
                UnusualIncident.incident_number.ilike(f'%{search}%'),
                UnusualIncident.brief_description.ilike(f'%{search}%'),
                UnusualIncident.train_no.ilike(f'%{search}%'),
                UnusualIncident.loco_no.ilike(f'%{search}%'),
                UnusualIncident.crew_name_manual.ilike(f'%{search}%'),
                UnusualIncident.station_location.ilike(f'%{search}%')
            )
        )

    all_incidents = query.order_by(UnusualIncident.incident_date.desc(), UnusualIncident.id.desc()).all()

    total_count = len(all_incidents)
    spad_count = sum(1 for inc in all_incidents if inc.incident_category == 'SPAD')
    investigating_count = sum(1 for inc in all_incidents if inc.status == 'UNDER_INVESTIGATION')
    reported_count = sum(1 for inc in all_incidents if inc.status == 'REPORTED')
    closed_count = sum(1 for inc in all_incidents if inc.status in ('ACTION_COMPLETED', 'CLOSED'))
    total_delay = sum(inc.delay_minutes or 0 for inc in all_incidents)

    lobbies = Lobby.query.order_by(Lobby.name.asc()).all()
    categories = [
        ('SPAD', 'Signal Passing At Danger (SPAD)'),
        ('LOCO_FAILURE', 'Locomotive / Equipment Tripping'),
        ('OHE_BREAKDOWN', 'OHE Power Supply Disruption'),
        ('SIGNAL_FAILURE', 'Signaling & Interlocking Failure'),
        ('DERAILMENT', 'Derailment / Track Obstruction'),
        ('FLAT_TYRE', 'Hot Axle / Flat Tyre / Brake Binding'),
        ('CATTLE_RUN_OVER', 'Cattle Run Over / Trespass'),
        ('ACP_UNUSUAL', 'Alarm Chain Pulling (ACP)'),
        ('UNUSUAL_SOUND', 'Unusual Sound / Jerk by Crew'),
        ('MISC', 'Miscellaneous Operational Unusual')
    ]

    return render_template(
        'officer/incidents.html',
        incidents=all_incidents,
        lobbies=lobbies,
        categories=categories,
        total_count=total_count,
        spad_count=spad_count,
        investigating_count=investigating_count,
        reported_count=reported_count,
        closed_count=closed_count,
        total_delay=total_delay,
        selected_category=category,
        selected_status=status,
        selected_traction=traction,
        selected_lobby=lobby_id,
        section=section,
        date_from=date_from,
        date_to=date_to,
        search=search
    )


@officer_bp.route('/incidents/<int:incident_id>', methods=['GET'])
def view_incident(incident_id):
    """View incident dossier by officer."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    return render_template('admin/incident_detail.html', incident=incident, is_officer_view=True)


@officer_bp.route('/incidents/<int:incident_id>/remark', methods=['POST'])
def add_incident_remark(incident_id):
    """Endorse officer remarks / inquiry directives on unusual incident."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    remarks = request.form.get('officer_remarks', '').strip()
    new_status = request.form.get('status', '').strip()
    if remarks:
        existing = incident.officer_remarks or ''
        officer = User.query.get(session.get('user_id'))
        officer_name = f"{officer.full_name} ({officer.sub_role or 'Officer'})" if officer else "Officer"
        ts_str = datetime.now().strftime('%d-%m-%Y %H:%M')
        incident.officer_remarks = f"{existing}\n[{ts_str} - {officer_name}]: {remarks}".strip()
        incident.officer_remarked_by_id = session.get('user_id')
        incident.officer_remarked_at = datetime.utcnow()
    if new_status in ('REPORTED', 'UNDER_INVESTIGATION', 'ACTION_COMPLETED', 'CLOSED'):
        incident.status = new_status
    db.session.commit()
    flash(f'Officer directive recorded on incident [{incident.incident_number}].', 'success')
    return redirect(url_for('officer.view_incident', incident_id=incident.id))


# ---------------------------------------------------------------------------
# PHASE 7: OFFICER ADVANCED REPORTING SUITE & EXPORT ANALYTICS
# ---------------------------------------------------------------------------

@officer_bp.route('/reports', methods=['GET'])
def reports():
    """Advanced Multi-Parameter Filtered Reports & Analytics Suite."""
    active_tab = request.args.get('tab', 'overview').strip()
    selected_lobby = request.args.get('lobby_id', '').strip()
    selected_cli = request.args.get('cli_id', '').strip()
    selected_category = request.args.get('category', '').strip()
    selected_traction = request.args.get('traction', '').strip()
    selected_grading = request.args.get('grading', '').strip()
    search = request.args.get('search', '').strip()

    overview = get_crew_overview_stats()
    cli_matrix = get_cli_crew_matrix()
    lobby_matrix = get_lobby_crew_matrix()

    # Query filtered crews
    query = filter_crews_query(
        lobby_id=selected_lobby,
        cli_id=selected_cli,
        category=selected_category,
        traction=selected_traction,
        grading=selected_grading,
        search=search
    )
    filtered_count = query.count()
    crews = query.limit(100).all()

    lobbies = Lobby.query.order_by(Lobby.code.asc()).all()
    clis = User.query.filter_by(role='supervisor').order_by(User.full_name.asc()).all()

    return render_template(
        'officer/reports.html',
        overview=overview,
        cli_matrix=cli_matrix,
        lobby_matrix=lobby_matrix,
        crews=crews,
        filtered_count=filtered_count,
        lobbies=lobbies,
        clis=clis,
        active_tab=active_tab,
        selected_lobby=selected_lobby,
        selected_cli=selected_cli,
        selected_category=selected_category,
        selected_traction=selected_traction,
        selected_grading=selected_grading,
        search=search,
        export_base_url=url_for('officer.reports'),
        is_officer_view=True
    )


@officer_bp.route('/reports/export/excel', methods=['GET'])
def export_reports_excel():
    """Download filtered crew records as styled Excel (.xlsx)."""
    selected_lobby = request.args.get('lobby_id', '').strip()
    selected_cli = request.args.get('cli_id', '').strip()
    selected_category = request.args.get('category', '').strip()
    selected_traction = request.args.get('traction', '').strip()
    selected_grading = request.args.get('grading', '').strip()
    search = request.args.get('search', '').strip()

    crews = filter_crews_query(
        lobby_id=selected_lobby,
        cli_id=selected_cli,
        category=selected_category,
        traction=selected_traction,
        grading=selected_grading,
        search=search
    ).all()

    buf = export_crews_to_excel(crews)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"HWH_Crew_Master_Report_{ts}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@officer_bp.route('/reports/export/csv', methods=['GET'])
def export_reports_csv():
    """Download filtered crew records as standard CSV."""
    selected_lobby = request.args.get('lobby_id', '').strip()
    selected_cli = request.args.get('cli_id', '').strip()
    selected_category = request.args.get('category', '').strip()
    selected_traction = request.args.get('traction', '').strip()
    selected_grading = request.args.get('grading', '').strip()
    search = request.args.get('search', '').strip()

    crews = filter_crews_query(
        lobby_id=selected_lobby,
        cli_id=selected_cli,
        category=selected_category,
        traction=selected_traction,
        grading=selected_grading,
        search=search
    ).all()

    buf = export_crews_to_csv(crews)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=HWH_Crew_Report_{ts}.csv"}
    )


@officer_bp.route('/crew/<int:crew_id>/remark', methods=['POST'])
def add_crew_remark(crew_id):
    """Add supervisory / performance remark on a running crew."""
    crew = User.query.get_or_404(crew_id)
    remark = request.form.get('officer_remark', '').strip()
    grading = request.form.get('safety_grading', '').strip()
    officer = User.query.get(session.get('user_id'))
    officer_name = officer.full_name if officer else "Officer"

    if grading in ('A', 'B', 'C'):
        crew.safety_grading = grading

    if remark:
        existing = crew.remarks or ''
        ts_str = datetime.now().strftime('%d-%m-%Y %H:%M')
        crew.remarks = f"{existing}\n[{ts_str} - {officer_name}]: {remark}".strip()

    db.session.commit()
    flash(f'Observation recorded for {crew.full_name}.', 'success')
    return redirect(url_for('officer.reports', tab='filter'))
