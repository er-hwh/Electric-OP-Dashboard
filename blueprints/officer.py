import os
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, Notice, NoticeAcknowledgement, CounsellingTopic, 
    CounsellingAcknowledgement, TrainingRecord, Message, FootplateInspection
)
from blueprints.auth import role_required

officer_bp = Blueprint('officer', __name__)

@officer_bp.before_request
@role_required('officer')
def officer_protection():
    pass

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
