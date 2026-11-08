import os
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, Notice, NoticeAcknowledgement, CounsellingTopic, 
    CounsellingAcknowledgement, TrainingRecord, Message, FootplateInspection,
    CLIMovement, CrewCounsellingRecord
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
    status_filter = request.args.get('status', 'ALL')
    lobby_filter = request.args.get('lobby', 'ALL')

    query = TrainingRecord.query.join(User, TrainingRecord.crew_id == User.id)

    if lobby_filter != 'ALL':
        query = query.filter(User.lobby_id == int(lobby_filter))

    today = date.today()
    if status_filter == 'OVERDUE':
        query = query.filter(TrainingRecord.due_date < today)
    elif status_filter == 'DUE_SOON':
        query = query.filter(
            TrainingRecord.due_date >= today,
            TrainingRecord.due_date <= today + timedelta(days=30)
        )
    elif status_filter == 'VALID':
        query = query.filter(TrainingRecord.due_date > today + timedelta(days=30))

    records = query.order_by(TrainingRecord.due_date.asc()).all()

    return render_template(
        'officer/training_monitor.html',
        records=records,
        lobbies=lobbies,
        current_status=status_filter,
        current_lobby=lobby_filter
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
