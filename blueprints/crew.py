import os
import io
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from database import db
from models import (
    User, Lobby, Notice, NoticeAcknowledgement, CounsellingTopic, 
    CounsellingAcknowledgement, TrainingRecord, MedicalRecord, FootplateInspection, Message,
    CrewCounsellingRecord, CrewCounsellingLog
)
from blueprints.auth import role_required
from blueprints.supervisor import compute_overdue_status, parse_date_value

crew_bp = Blueprint('crew', __name__)

@crew_bp.before_request
@role_required('crew')
def crew_protection():
    pass

@crew_bp.route('/')
def dashboard():
    crew = User.query.get(session['user_id'])
    
    # 1. Training & Competencies
    trainings = TrainingRecord.query.filter_by(crew_id=crew.id).order_by(TrainingRecord.due_date.asc()).all()
    pme_record = MedicalRecord.query.filter_by(crew_id=crew.id).order_by(MedicalRecord.due_date.desc()).first()

    # 2. Notices requiring acknowledgement
    all_notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).limit(25).all()
    acked_notice_ids = {a.notice_id for a in NoticeAcknowledgement.query.filter_by(user_id=crew.id).all()}
    
    pending_notices = [n for n in all_notices if n.id not in acked_notice_ids]
    acked_notices = [n for n in all_notices if n.id in acked_notice_ids]
    mandatory_pending_notices = [n for n in pending_notices if n.is_mandatory]

    # 3. Counselling topics & One-to-one Counselling Logs
    counselling_list = CounsellingTopic.query.filter(
        (CounsellingTopic.status == 'APPROVED') | (CounsellingTopic.status.is_(None))
    ).order_by(CounsellingTopic.topic_date.desc(), CounsellingTopic.created_at.desc()).limit(15).all()
    acked_counsel_ids = {ca.counselling_id for ca in CounsellingAcknowledgement.query.filter_by(crew_id=crew.id).all()}

    my_counselling_logs = CrewCounsellingLog.query.filter_by(crew_id=crew.id).order_by(CrewCounsellingLog.counselling_date.desc()).all()
    pending_counselling_logs = [l for l in my_counselling_logs if not l.crew_acknowledged]

    # 4. Recent footplate monitoring on this crew
    inspections = FootplateInspection.query.filter_by(crew_id=crew.id).order_by(FootplateInspection.inspection_date.desc()).all()

    # 5. Personal Safety & Counselling Profile (Read-only, maintained by CLI)
    counselling_record = CrewCounsellingRecord.query.filter(
        (CrewCounsellingRecord.crew_user_id == crew.id) |
        (CrewCounsellingRecord.crew_id_str == crew.pf_number) |
        (CrewCounsellingRecord.cug == crew.mobile) |
        (CrewCounsellingRecord.crew_id_str == crew.username)
    ).first()

    if not counselling_record:
        # Create initial record for this crew
        counselling_record = CrewCounsellingRecord(
            crew_user_id=crew.id,
            crew_id_str=crew.username,
            crew_name=crew.full_name,
            crew_hq=crew.lobby.code if crew.lobby else 'HWH',
            cug=crew.mobile,
            designation=crew.sub_role,
            pf_no=crew.pf_number or '',
            grade='A'
        )
        db.session.add(counselling_record)
        db.session.commit()

    # 6. Compliance Status
    compliance = compute_overdue_status(
        counselling_record.last_footplate,
        counselling_record.safety_counselling,
        None
    )

    # 7. Nominated CLI lookup
    cli_user = crew.nominated_cli
    if not cli_user and counselling_record.cli_name:
        cli_user = User.query.filter(
            (User.role == 'supervisor') & (User.full_name.ilike(f"%{counselling_record.cli_name}%"))
        ).first()

    # 8. Messages & Replies
    inbox = Message.query.filter_by(recipient_id=crew.id).order_by(Message.created_at.desc()).all()
    sent_messages = Message.query.filter_by(sender_id=crew.id).order_by(Message.created_at.desc()).all()

    return render_template(
        'crew/dashboard.html',
        crew=crew,
        counselling_record=counselling_record,
        compliance=compliance,
        cli_user=cli_user,
        trainings=trainings,
        pme_record=pme_record,
        pending_notices=pending_notices,
        acked_notices=acked_notices,
        mandatory_pending_notices=mandatory_pending_notices,
        counselling_list=counselling_list,
        acked_counsel_ids=acked_counsel_ids,
        my_counselling_logs=my_counselling_logs,
        pending_counselling_logs=pending_counselling_logs,
        inspections=inspections,
        inbox=inbox,
        sent_messages=sent_messages
    )


@crew_bp.route('/update-profile', methods=['POST'])
def update_profile():
    crew = User.query.get(session['user_id'])
    mobile = request.form.get('mobile', '').strip()
    email = request.form.get('email', '').strip()
    
    if mobile:
        crew.mobile = mobile
        rec = CrewCounsellingRecord.query.filter_by(crew_user_id=crew.id).first()
        if rec:
            rec.cug = mobile
    if email:
        crew.email = email
    db.session.commit()
    flash('Your contact details have been successfully updated.', 'success')
    return redirect(url_for('crew.dashboard'))


@crew_bp.route('/export-pdf')
def export_my_pdf():
    crew = User.query.get(session['user_id'])
    rec = CrewCounsellingRecord.query.filter_by(crew_user_id=crew.id).first()
    inspections = FootplateInspection.query.filter_by(crew_id=crew.id).order_by(FootplateInspection.inspection_date.desc()).all()

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

        title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=13, leading=16, alignment=TA_CENTER, textColor=colors.HexColor('#065f46'))
        elements.append(Paragraph("EASTERN RAILWAY &bull; HOWRAH DIVISION", title_style))
        elements.append(Paragraph("ELECTRIC OPERATION DEPARTMENT &bull; RUNNING CREW PERSONAL SAFETY & BIO-DATA SHEET", styles['Normal']))
        elements.append(Spacer(1, 10))

        data = [
            ["Crew Name:", rec.crew_name if rec else crew.full_name, "CMS Crew ID:", rec.crew_id_str if rec else crew.username],
            ["Designation:", rec.designation if rec else crew.sub_role, "Lobby / HQ:", rec.crew_hq if rec else (crew.lobby.code if crew.lobby else 'HWH')],
            ["CUG Mobile:", rec.cug if rec else crew.mobile, "PF No / HRMS:", rec.pf_no if rec else (crew.pf_number or 'N/A')],
            ["Safety Grade:", rec.grade if rec else 'A', "Nominated CLI:", rec.cli_name if rec else 'CLI/HWH'],
            ["Last Footplate:", rec.last_footplate if rec else 'N/A', "Technical Counselling:", rec.technical_counselling if rec else 'N/A'],
            ["Safety Counselling:", rec.safety_counselling if rec else 'N/A', "Verified By:", rec.counselling_verified_by if rec else 'N/A'],
            ["Last SPM Check:", rec.last_spm_check if rec else 'N/A', "Last CVVRS Check:", rec.last_cvvrs_check if rec else 'N/A'],
            ["BA Fail History:", rec.ba_fail_history if rec else 'Nil', "SPAD History:", rec.spad_history if rec else 'Nil'],
            ["Mobile Habit:", rec.mobile_habit if rec else 'Normal', "DA Case:", rec.da_case if rec else 'Nil'],
            ["Family Issue:", rec.family_issue if rec else 'Nil', "Health Issue:", rec.health_issue if rec else 'Nil'],
            ["Baby < 6 Months:", rec.baby_below_6_months if rec else 'No', "Accident Prone:", rec.accident_prone if rec else 'No'],
            ["Safety Remarks:", Paragraph(rec.remarks if (rec and rec.remarks) else 'Satisfactory performance in section.', styles['Normal']), "", ""]
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
        return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=f"BioData_{crew.username}.pdf")
    except Exception:
        return render_template('crew/biodata_print.html', crew=crew, rec=rec, inspections=inspections)


@crew_bp.route('/report-problem', methods=['POST'])
def report_problem():
    """Crew submitting a comment or reporting a family/health/duty problem to nominated CLI."""
    crew = User.query.get(session['user_id'])
    category = request.form.get('category', 'General')
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()

    if not body:
        flash('Please describe your comment or problem before submitting.', 'danger')
        return redirect(url_for('crew.dashboard'))

    # Determine recipient: Nominated CLI, or Lobby CCC / Admin
    recipient_id = crew.cli_id
    if not recipient_id:
        ccc = User.query.filter_by(lobby_id=crew.lobby_id, sub_role='CCC').first()
        if ccc:
            recipient_id = ccc.id
        else:
            sr_dee = User.query.filter_by(username='Sr. DEE(OP)/HWH').first()
            recipient_id = sr_dee.id if sr_dee else 1

    full_subject = f"[{category.upper()}] {subject if subject else 'Crew Comment / Problem Submission'}"
    msg = Message(
        sender_id=crew.id,
        recipient_id=recipient_id,
        subject=full_subject,
        body=body,
        message_type='CREW_TO_CLI',
        status='PENDING_CLI_REVIEW',
        is_read=False
    )
    db.session.add(msg)
    db.session.commit()

    recipient_name = crew.nominated_cli.full_name if crew.nominated_cli else "Supervisor / Lobby Controller"
    flash(f'Your comments / problem report has been submitted to {recipient_name}. You will be notified once reviewed.', 'success')
    return redirect(url_for('crew.dashboard'))


@crew_bp.route('/acknowledge-notice/<int:notice_id>', methods=['POST'])
def acknowledge_notice(notice_id):
    crew = User.query.get(session['user_id'])
    notice = Notice.query.get_or_404(notice_id)
    remarks = request.form.get('remarks', 'Read, understood, and assured strict compliance.').strip()
    
    existing = NoticeAcknowledgement.query.filter_by(notice_id=notice_id, user_id=crew.id).first()
    if not existing:
        ack = NoticeAcknowledgement(
            notice_id=notice_id,
            user_id=crew.id,
            acknowledged_at=datetime.utcnow(),
            remarks=remarks,
            ip_address=request.remote_addr,
            device_info=str(request.user_agent)[:250] if request.user_agent else None,
            is_confirmed=True
        )
        db.session.add(ack)
        db.session.commit()
        flash(f'Safety Circular [{notice.notice_number or notice.title}] successfully acknowledged and recorded with electronic assurance timestamp.', 'success')
    else:
        existing.acknowledged_at = datetime.utcnow()
        existing.remarks = remarks
        existing.is_confirmed = True
        existing.ip_address = request.remote_addr
        db.session.commit()
        flash(f'Safety Circular assurance updated.', 'info')
    return redirect(url_for('crew.dashboard'))


@crew_bp.route('/acknowledge-counselling-log/<int:log_id>', methods=['POST'])
def acknowledge_counselling_log(log_id):
    crew = User.query.get(session['user_id'])
    log = CrewCounsellingLog.query.get_or_404(log_id)
    if log.crew_id != crew.id:
        flash('Unauthorized access to counselling session record.', 'danger')
        return redirect(url_for('crew.dashboard'))

    response_text = request.form.get('crew_response', '').strip()
    log.crew_acknowledged = True
    log.crew_ack_date = datetime.utcnow()
    if response_text:
        log.crew_response = response_text
    db.session.commit()
    flash(f'One-to-one Counselling on "{log.topic}" acknowledged and confirmed.', 'success')
    return redirect(url_for('crew.dashboard'))

@crew_bp.route('/acknowledge-counselling/<int:counselling_id>', methods=['POST'])
def acknowledge_counselling(counselling_id):
    crew = User.query.get(session['user_id'])
    topic = CounsellingTopic.query.get_or_404(counselling_id)
    doubt = request.form.get('doubt_or_query', '').strip()
    
    existing = CounsellingAcknowledgement.query.filter_by(counselling_id=counselling_id, crew_id=crew.id).first()
    if existing:
        flash('You have already logged your digital assurance for this safety counselling topic.', 'info')
        return redirect(url_for('public.counselling_detail', topic_id=counselling_id))

    # Evaluate Q&A verification if topic contains questions
    questions = topic.get_questions()
    quiz_score = 100
    passed = True

    if questions:
        correct_count = 0
        total_questions = len(questions)
        
        for idx, q in enumerate(questions):
            ans_str = request.form.get(f'ans_{idx}')
            if ans_str is None:
                flash(f'Please answer Question {idx + 1} to verify your safety comprehension.', 'danger')
                return redirect(url_for('public.counselling_detail', topic_id=counselling_id))
            try:
                ans_idx = int(ans_str)
                if ans_idx == q.get('answer', 0):
                    correct_count += 1
            except ValueError:
                pass

        if total_questions > 0:
            quiz_score = int((correct_count / total_questions) * 100)

        # Indian Railways Safety Rule standard: 100% required to clear assurance check
        if correct_count < total_questions:
            flash(
                f'Safety Rule Comprehension Check Incomplete: You scored {correct_count}/{total_questions} ({quiz_score}%). '
                f'As per Railway Safety protocol, full 100% score is required. Please re-read the GR & SR instructions and resubmit.',
                'danger'
            )
            return redirect(url_for('public.counselling_detail', topic_id=counselling_id))

    ack = CounsellingAcknowledgement(
        counselling_id=counselling_id,
        crew_id=crew.id,
        acknowledged_at=datetime.utcnow(),
        quiz_score=quiz_score,
        passed=True,
        understood=True,
        doubt_or_query=doubt
    )
    db.session.add(ack)
    db.session.commit()

    flash(
        f'Safety Counselling for "{topic.title}" successfully acknowledged! '
        f'Comprehension check passed ({quiz_score}%). Your digital assurance is now recorded in the Howrah Division Register.',
        'success'
    )
    return redirect(url_for('public.counselling_detail', topic_id=counselling_id))

@crew_bp.route('/message-cli', methods=['GET', 'POST'])
def message_cli():
    crew = User.query.get(session['user_id'])
    if not crew.nominated_cli:
        flash('You do not currently have a nominated CLI assigned. Please contact your Lobby CCC.', 'warning')

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()

        if not subject or not body:
            flash('Subject and message content cannot be blank.', 'danger')
            return redirect(url_for('crew.message_cli'))

        if not crew.cli_id:
            flash('Cannot send: No nominated CLI mapped to your profile.', 'danger')
            return redirect(url_for('crew.dashboard'))

        new_msg = Message(
            sender_id=crew.id,
            recipient_id=crew.cli_id,
            subject=subject,
            body=body,
            message_type='CREW_TO_CLI',
            status='PENDING_CLI_REVIEW',
            is_read=False
        )
        db.session.add(new_msg)
        db.session.commit()

        flash('Your message has been sent to your nominated Chief Loco Inspector (CLI) for review and guidance.', 'success')
        return redirect(url_for('crew.dashboard'))

    return render_template('crew/message_cli.html', crew=crew)
