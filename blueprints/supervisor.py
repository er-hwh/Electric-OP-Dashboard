import os
import json
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, FootplateInspection, Message, TrainingRecord, 
    CounsellingTopic, Notice, CrewCounsellingRecord
)
from blueprints.auth import role_required

supervisor_bp = Blueprint('supervisor', __name__)

@supervisor_bp.before_request
@role_required('supervisor')
def supervisor_protection():
    pass

@supervisor_bp.route('/')
def dashboard():
    cli = User.query.get(session['user_id'])
    
    # Crews assigned to this CLI
    if cli.sub_role == 'CLI':
        my_crews = User.query.filter_by(cli_id=cli.id, is_active=True).all()
        crew_ids = [c.id for c in my_crews]
    else: # CCC can see all crews in their lobby
        my_crews = User.query.filter_by(lobby_id=cli.lobby_id, role='crew', is_active=True).all()
        crew_ids = [c.id for c in my_crews]

    # Map counselling records to my crews
    counselling_map = {}
    if my_crews:
        crew_pfs = [c.pf_number for c in my_crews if c.pf_number]
        crew_mobiles = [c.mobile for c in my_crews if c.mobile]
        records = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id.in_(crew_ids)) |
            (CrewCounsellingRecord.crew_id_str.in_(crew_pfs)) |
            (CrewCounsellingRecord.cug.in_(crew_mobiles))
        ).all()
        for r in records:
            if r.crew_user_id and r.crew_user_id in crew_ids:
                counselling_map[r.crew_user_id] = r
            else:
                for c in my_crews:
                    if (c.pf_number and r.crew_id_str and c.pf_number.upper() == r.crew_id_str.upper()) or \
                       (c.mobile and r.cug and c.mobile == r.cug):
                        counselling_map[c.id] = r
                        if not r.crew_user_id:
                            r.crew_user_id = c.id
                            db.session.commit()

    # Pending messages from crews
    pending_messages = Message.query.filter(
        Message.recipient_id == cli.id,
        Message.status == 'PENDING_CLI_REVIEW'
    ).order_by(Message.created_at.desc()).all()

    # Recent inspections
    recent_inspections = FootplateInspection.query.filter_by(cli_id=cli.id).order_by(FootplateInspection.inspection_date.desc()).limit(5).all()
    total_footplate_km = sum([insp.footplate_km or 0.0 for insp in FootplateInspection.query.filter_by(cli_id=cli.id).all()])

    # Training alerts for my crews
    today = date.today()
    crew_training_alerts = TrainingRecord.query.filter(
        TrainingRecord.crew_id.in_(crew_ids) if crew_ids else False,
        TrainingRecord.due_date <= today + timedelta(days=30)
    ).order_by(TrainingRecord.due_date.asc()).all()

    return render_template(
        'supervisor/dashboard.html',
        cli=cli,
        my_crews=my_crews,
        counselling_map=counselling_map,
        pending_messages=pending_messages,
        recent_inspections=recent_inspections,
        total_footplate_km=total_footplate_km,
        crew_training_alerts=crew_training_alerts
    )

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


# ─────────────────────────────────────────────────────────────────
#  CREW SAFETY & COUNSELLING MANAGEMENT (CLI EXCLUSIVE EDIT)
# ─────────────────────────────────────────────────────────────────

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
