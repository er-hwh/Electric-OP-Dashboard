import os
import sys

base_dir = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard'
sys.path.insert(0, base_dir)

# ---------------------------------------------------------------------------
# 1. Update blueprints/admin.py
# ---------------------------------------------------------------------------
admin_path = os.path.join(base_dir, 'blueprints', 'admin.py')
with open(admin_path, 'r', encoding='utf-8') as f:
    admin_code = f.read()

phase6_admin_code = '''

# ---------------------------------------------------------------------------
# PHASE 6: HELPER & GOOGLE SHEETS DIRECTORY MANAGEMENT
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


@admin_bp.route('/sheets', methods=['GET'], endpoint='sheets')
@admin_bp.route('/sheets/list', methods=['GET'], endpoint='sheets_list')
def sheets():
    """List and manage all registered Google Sheets."""
    category = request.args.get('category', '').strip()
    traction = request.args.get('traction', '').strip()
    search = request.args.get('search', '').strip()

    query = GoogleSheetLink.query
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

    all_sheets = query.order_by(GoogleSheetLink.display_order.asc(), GoogleSheetLink.id.desc()).all()
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
        'admin/sheets.html',
        sheets=all_sheets,
        categories=categories,
        selected_category=category,
        selected_traction=traction,
        search=search
    )


@admin_bp.route('/sheets/new', methods=['GET', 'POST'], endpoint='new_sheet')
def new_sheet():
    """Add a new Google Sheet to the directory."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        sheet_url = request.form.get('sheet_url', '').strip()
        category = request.form.get('category', 'GENERAL').strip()
        description = request.form.get('description', '').strip()
        roles = request.form.getlist('allowed_roles')
        allowed_roles = ','.join(roles) if roles else 'admin,officer,control,supervisor,crew'
        lobby_id = request.form.get('lobby_id') or None
        if lobby_id:
            try:
                lobby_id = int(lobby_id)
            except ValueError:
                lobby_id = None
        traction_type = request.form.get('traction_type', 'BOTH').strip()
        is_embedded = True if request.form.get('is_embedded') else False
        display_order = int(request.form.get('display_order', 0) or 0)
        is_active = True if request.form.get('is_active', '1') == '1' else False

        if not title or not sheet_url:
            flash('Title and Google Sheet URL are required.', 'danger')
            lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
            return render_template('admin/sheet_form.html', sheet=None, lobbies=lobbies)

        sheet = GoogleSheetLink(
            title=title,
            sheet_url=sheet_url,
            category=category,
            description=description,
            allowed_roles=allowed_roles,
            lobby_id=lobby_id,
            traction_type=traction_type,
            is_embedded=is_embedded,
            display_order=display_order,
            is_active=is_active,
            created_by_id=session.get('user_id')
        )
        db.session.add(sheet)
        db.session.commit()
        flash(f'Google Sheet link "{title}" added successfully.', 'success')
        return redirect(url_for('admin.sheets'))

    lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
    return render_template('admin/sheet_form.html', sheet=None, lobbies=lobbies)


@admin_bp.route('/sheets/<int:sheet_id>/edit', methods=['GET', 'POST'], endpoint='edit_sheet')
def edit_sheet(sheet_id):
    """Edit existing Google Sheet metadata."""
    sheet = GoogleSheetLink.query.get_or_404(sheet_id)
    if request.method == 'POST':
        sheet.title = request.form.get('title', '').strip()
        sheet.sheet_url = request.form.get('sheet_url', '').strip()
        sheet.category = request.form.get('category', 'GENERAL').strip()
        sheet.description = request.form.get('description', '').strip()
        roles = request.form.getlist('allowed_roles')
        sheet.allowed_roles = ','.join(roles) if roles else 'admin,officer,control,supervisor,crew'
        lobby_id = request.form.get('lobby_id') or None
        if lobby_id:
            try:
                sheet.lobby_id = int(lobby_id)
            except ValueError:
                sheet.lobby_id = None
        else:
            sheet.lobby_id = None
        sheet.traction_type = request.form.get('traction_type', 'BOTH').strip()
        sheet.is_embedded = True if request.form.get('is_embedded') else False
        sheet.display_order = int(request.form.get('display_order', 0) or 0)
        sheet.is_active = True if request.form.get('is_active') else False
        db.session.commit()
        flash(f'Google Sheet link "{sheet.title}" updated.', 'success')
        return redirect(url_for('admin.sheets'))

    lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
    return render_template('admin/sheet_form.html', sheet=sheet, lobbies=lobbies)


@admin_bp.route('/sheets/<int:sheet_id>/toggle', methods=['POST'], endpoint='toggle_sheet')
def toggle_sheet(sheet_id):
    """Toggle Google Sheet active/inactive status."""
    sheet = GoogleSheetLink.query.get_or_404(sheet_id)
    sheet.is_active = not sheet.is_active
    db.session.commit()
    status_str = "activated" if sheet.is_active else "deactivated"
    flash(f'Google Sheet "{sheet.title}" has been {status_str}.', 'info')
    return redirect(url_for('admin.sheets'))


@admin_bp.route('/sheets/<int:sheet_id>/delete', methods=['POST'], endpoint='delete_sheet')
def delete_sheet(sheet_id):
    """Delete a Google Sheet link."""
    sheet = GoogleSheetLink.query.get_or_404(sheet_id)
    title = sheet.title
    db.session.delete(sheet)
    db.session.commit()
    flash(f'Google Sheet "{title}" deleted from directory.', 'warning')
    return redirect(url_for('admin.sheets'))


# ---------------------------------------------------------------------------
# PHASE 6: UNUSUAL INCIDENT TRACKER DIRECTORY
# ---------------------------------------------------------------------------

@admin_bp.route('/incidents', methods=['GET'], endpoint='incidents')
@admin_bp.route('/incidents/list', methods=['GET'], endpoint='incidents_list')
def incidents():
    """Unusual Incident Tracker Directory & Analytics."""
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

    lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
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
        'admin/incidents.html',
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


@admin_bp.route('/incidents/new', methods=['GET', 'POST'], endpoint='new_incident')
def new_incident():
    """Log a new unusual incident."""
    if request.method == 'POST':
        incident_date_str = request.form.get('incident_date', '').strip()
        incident_date = parse_date_value(incident_date_str) or date.today()
        incident_time = request.form.get('incident_time', '').strip()
        section = request.form.get('section', '').strip()
        station_location = request.form.get('station_location', '').strip()
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        traction_type = request.form.get('traction_type', 'ELECTRIC').strip()
        incident_category = request.form.get('incident_category', 'MISC').strip()
        
        crew_id_raw = request.form.get('crew_id')
        crew_id = int(crew_id_raw) if crew_id_raw and crew_id_raw.isdigit() else None
        crew_name_manual = request.form.get('crew_name_manual', '').strip()
        alp_name_manual = request.form.get('alp_name_manual', '').strip()

        lobby_id_raw = request.form.get('lobby_id')
        lobby_id = int(lobby_id_raw) if lobby_id_raw and lobby_id_raw.isdigit() else None

        cli_id_raw = request.form.get('cli_id')
        cli_id = int(cli_id_raw) if cli_id_raw and cli_id_raw.isdigit() else None

        brief_description = request.form.get('brief_description', '').strip()
        primary_cause = request.form.get('primary_cause', '').strip()
        immediate_action = request.form.get('immediate_action', '').strip()
        rectification_time = request.form.get('rectification_time', '').strip()
        delay_minutes = int(request.form.get('delay_minutes', 0) or 0)
        status = request.form.get('status', 'REPORTED').strip()

        if not section or not brief_description:
            flash('Section and Brief Description are mandatory.', 'danger')
            lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
            clis = User.query.filter_by(role='supervisor').order_by(User.full_name.asc()).all()
            return render_template('admin/incident_form.html', incident=None, lobbies=lobbies, clis=clis)

        attachment_path = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                save_filename = f"{ts}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'incidents')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, save_filename))
                attachment_path = f"uploads/incidents/{save_filename}"

        inc_number = UnusualIncident.generate_incident_number()
        incident = UnusualIncident(
            incident_number=inc_number,
            incident_date=incident_date,
            incident_time=incident_time,
            section=section,
            station_location=station_location,
            train_no=train_no,
            loco_no=loco_no,
            traction_type=traction_type,
            incident_category=incident_category,
            crew_id=crew_id,
            crew_name_manual=crew_name_manual,
            alp_name_manual=alp_name_manual,
            lobby_id=lobby_id,
            cli_id=cli_id,
            brief_description=brief_description,
            primary_cause=primary_cause,
            immediate_action=immediate_action,
            rectification_time=rectification_time,
            delay_minutes=delay_minutes,
            status=status,
            attachment_path=attachment_path,
            reported_by_id=session.get('user_id'),
            reported_by_role='ADMIN'
        )
        db.session.add(incident)
        db.session.commit()
        flash(f'Unusual Incident registered successfully as [{inc_number}].', 'success')
        return redirect(url_for('admin.incidents'))

    lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
    clis = User.query.filter_by(role='supervisor').order_by(User.full_name.asc()).all()
    return render_template('admin/incident_form.html', incident=None, lobbies=lobbies, clis=clis)


@admin_bp.route('/incidents/<int:incident_id>', methods=['GET'], endpoint='view_incident')
def view_incident(incident_id):
    """Detailed incident dossier view."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    return render_template('admin/incident_detail.html', incident=incident)


@admin_bp.route('/incidents/<int:incident_id>/edit', methods=['GET', 'POST'], endpoint='edit_incident')
def edit_incident(incident_id):
    """Edit existing incident details."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    if request.method == 'POST':
        incident_date_str = request.form.get('incident_date', '').strip()
        if incident_date_str:
            d = parse_date_value(incident_date_str)
            if d:
                incident.incident_date = d
        incident.incident_time = request.form.get('incident_time', '').strip()
        incident.section = request.form.get('section', '').strip()
        incident.station_location = request.form.get('station_location', '').strip()
        incident.train_no = request.form.get('train_no', '').strip()
        incident.loco_no = request.form.get('loco_no', '').strip()
        incident.traction_type = request.form.get('traction_type', incident.traction_type).strip()
        incident.incident_category = request.form.get('incident_category', incident.incident_category).strip()

        crew_id_raw = request.form.get('crew_id')
        incident.crew_id = int(crew_id_raw) if crew_id_raw and crew_id_raw.isdigit() else None
        incident.crew_name_manual = request.form.get('crew_name_manual', '').strip()
        incident.alp_name_manual = request.form.get('alp_name_manual', '').strip()

        lobby_id_raw = request.form.get('lobby_id')
        incident.lobby_id = int(lobby_id_raw) if lobby_id_raw and lobby_id_raw.isdigit() else None

        cli_id_raw = request.form.get('cli_id')
        incident.cli_id = int(cli_id_raw) if cli_id_raw and cli_id_raw.isdigit() else None

        incident.brief_description = request.form.get('brief_description', '').strip()
        incident.primary_cause = request.form.get('primary_cause', '').strip()
        incident.immediate_action = request.form.get('immediate_action', '').strip()
        incident.rectification_time = request.form.get('rectification_time', '').strip()
        incident.delay_minutes = int(request.form.get('delay_minutes', 0) or 0)
        incident.status = request.form.get('status', incident.status).strip()

        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                filename = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                save_filename = f"{ts}_{filename}"
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'incidents')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, save_filename))
                incident.attachment_path = f"uploads/incidents/{save_filename}"

        db.session.commit()
        flash(f'Incident [{incident.incident_number}] updated successfully.', 'success')
        return redirect(url_for('admin.view_incident', incident_id=incident.id))

    lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
    clis = User.query.filter_by(role='supervisor').order_by(User.full_name.asc()).all()
    return render_template('admin/incident_form.html', incident=incident, lobbies=lobbies, clis=clis)


@admin_bp.route('/incidents/<int:incident_id>/status', methods=['POST'], endpoint='update_incident_status')
def update_incident_status(incident_id):
    """Quick update of incident status and resolution."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    new_status = request.form.get('status', '').strip()
    resolution_notes = request.form.get('resolution_notes', '').strip()
    if new_status in ('REPORTED', 'UNDER_INVESTIGATION', 'ACTION_COMPLETED', 'CLOSED'):
        incident.status = new_status
        if resolution_notes:
            existing = incident.immediate_action or ''
            ts_str = datetime.now().strftime('%d-%m-%Y %H:%M')
            incident.immediate_action = f"{existing}\\n[{ts_str} Update by Admin]: {resolution_notes}".strip()
        db.session.commit()
        flash(f'Status of [{incident.incident_number}] updated to {new_status}.', 'success')
    return redirect(url_for('admin.view_incident', incident_id=incident.id))


@admin_bp.route('/incidents/<int:incident_id>/delete', methods=['POST'], endpoint='delete_incident')
def delete_incident(incident_id):
    """Delete an incident record."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    inc_num = incident.incident_number
    db.session.delete(incident)
    db.session.commit()
    flash(f'Incident [{inc_num}] deleted.', 'warning')
    return redirect(url_for('admin.incidents'))
'''

if 'def sheets():' not in admin_code:
    with open(admin_path, 'a', encoding='utf-8') as f:
        f.write(phase6_admin_code)
    print("blueprints/admin.py updated with Phase 6.")
else:
    print("blueprints/admin.py already has Phase 6 routes.")

# ---------------------------------------------------------------------------
# 2. Update blueprints/officer.py
# ---------------------------------------------------------------------------
officer_path = os.path.join(base_dir, 'blueprints', 'officer.py')
with open(officer_path, 'r', encoding='utf-8') as f:
    officer_code = f.read()

# Update import in officer.py
if 'GoogleSheetLink' not in officer_code:
    officer_code = officer_code.replace(
        'CrewCounsellingRecord, CrewCounsellingLog',
        'CrewCounsellingRecord, CrewCounsellingLog, GoogleSheetLink, UnusualIncident'
    )

phase6_officer_code = '''

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

    lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
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
        incident.officer_remarks = f"{existing}\\n[{ts_str} - {officer_name}]: {remarks}".strip()
        incident.officer_remarked_by_id = session.get('user_id')
        incident.officer_remarked_at = datetime.utcnow()
    if new_status in ('REPORTED', 'UNDER_INVESTIGATION', 'ACTION_COMPLETED', 'CLOSED'):
        incident.status = new_status
    db.session.commit()
    flash(f'Officer directive recorded on incident [{incident.incident_number}].', 'success')
    return redirect(url_for('officer.view_incident', incident_id=incident.id))
'''

if 'def sheets():' not in officer_code:
    officer_code = officer_code + phase6_officer_code
    with open(officer_path, 'w', encoding='utf-8') as f:
        f.write(officer_code)
    print("blueprints/officer.py updated with Phase 6.")
else:
    print("blueprints/officer.py already has Phase 6 routes.")

# ---------------------------------------------------------------------------
# 3. Update blueprints/control.py
# ---------------------------------------------------------------------------
control_path = os.path.join(base_dir, 'blueprints', 'control.py')
with open(control_path, 'r', encoding='utf-8') as f:
    control_code = f.read()

if 'GoogleSheetLink' not in control_code:
    control_code = control_code.replace(
        'from models import User, Lobby',
        'from models import User, Lobby, GoogleSheetLink, UnusualIncident'
    )

phase6_control_code = '''

# ---------------------------------------------------------------------------
# PHASE 6: CONTROL (TLC / PCNL) GOOGLE SHEETS & SHIFT UNUSUAL INCIDENTS
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


@control_bp.route('/sheets', methods=['GET'])
def sheets():
    """Operational Google Sheets Directory for TLC / PCNL Control."""
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
        search=search,
        is_control_view=True
    )


@control_bp.route('/incidents', methods=['GET'])
def incidents():
    """Operational Incident Control Room Desk."""
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    traction = request.args.get('traction', '').strip()
    search = request.args.get('search', '').strip()

    query = UnusualIncident.query
    if category and category != 'ALL':
        query = query.filter_by(incident_category=category)
    if status and status != 'ALL':
        query = query.filter_by(status=status)
    if traction and traction != 'ALL':
        query = query.filter(UnusualIncident.traction_type.in_([traction, 'BOTH']))
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
        'control/incidents.html',
        incidents=all_incidents,
        categories=categories,
        selected_category=category,
        selected_status=status,
        selected_traction=traction,
        search=search
    )


@control_bp.route('/incidents/new', methods=['GET', 'POST'])
def new_incident():
    """Fast logging of unusual incident by TLC / PCNL during shift."""
    user = User.query.get(session.get('user_id'))
    default_role = 'TLC' if user and user.is_tlc() else ('PCNL' if user and user.is_pcnl() else 'CONTROL')
    if request.method == 'POST':
        incident_date_str = request.form.get('incident_date', '').strip()
        incident_date = parse_date_value(incident_date_str) or date.today()
        incident_time = request.form.get('incident_time', '').strip()
        section = request.form.get('section', '').strip()
        station_location = request.form.get('station_location', '').strip()
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        traction_type = request.form.get('traction_type', 'ELECTRIC' if default_role == 'TLC' else 'DIESEL').strip()
        incident_category = request.form.get('incident_category', 'MISC').strip()
        crew_name_manual = request.form.get('crew_name_manual', '').strip()
        alp_name_manual = request.form.get('alp_name_manual', '').strip()
        lobby_id_raw = request.form.get('lobby_id')
        lobby_id = int(lobby_id_raw) if lobby_id_raw and lobby_id_raw.isdigit() else None
        brief_description = request.form.get('brief_description', '').strip()
        immediate_action = request.form.get('immediate_action', '').strip()
        delay_minutes = int(request.form.get('delay_minutes', 0) or 0)

        if not section or not brief_description:
            flash('Section and Brief Description are mandatory.', 'danger')
            lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
            return render_template('control/incident_form.html', lobbies=lobbies, default_role=default_role)

        inc_number = UnusualIncident.generate_incident_number()
        incident = UnusualIncident(
            incident_number=inc_number,
            incident_date=incident_date,
            incident_time=incident_time,
            section=section,
            station_location=station_location,
            train_no=train_no,
            loco_no=loco_no,
            traction_type=traction_type,
            incident_category=incident_category,
            crew_name_manual=crew_name_manual,
            alp_name_manual=alp_name_manual,
            lobby_id=lobby_id,
            brief_description=brief_description,
            immediate_action=immediate_action,
            delay_minutes=delay_minutes,
            status='REPORTED',
            reported_by_id=session.get('user_id'),
            reported_by_role=default_role
        )
        db.session.add(incident)
        db.session.commit()
        flash(f'Unusual Incident [{inc_number}] logged into Shift Control Log.', 'success')
        return redirect(url_for('control.incidents'))

    lobbies = Lobby.query.order_by(Lobby.lobby_name.asc()).all()
    return render_template('control/incident_form.html', lobbies=lobbies, default_role=default_role)


@control_bp.route('/incidents/<int:incident_id>', methods=['GET'])
def view_incident(incident_id):
    """View incident dossier by Control."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    return render_template('admin/incident_detail.html', incident=incident, is_control_view=True)


@control_bp.route('/incidents/<int:incident_id>/update-action', methods=['POST'])
def update_action(incident_id):
    """Log shift control rectification action & train delay minutes."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    action_note = request.form.get('action_note', '').strip()
    delay = request.form.get('delay_minutes')
    rect_time = request.form.get('rectification_time', '').strip()
    new_status = request.form.get('status', '').strip()

    if delay and delay.isdigit():
        incident.delay_minutes = int(delay)
    if rect_time:
        incident.rectification_time = rect_time
    if action_note:
        existing = incident.immediate_action or ''
        ts_str = datetime.now().strftime('%d-%m-%Y %H:%M')
        incident.immediate_action = f"{existing}\\n[{ts_str} Control Action]: {action_note}".strip()
    if new_status in ('REPORTED', 'UNDER_INVESTIGATION', 'ACTION_COMPLETED', 'CLOSED'):
        incident.status = new_status

    db.session.commit()
    flash(f'Operational action updated on [{incident.incident_number}].', 'success')
    return redirect(url_for('control.view_incident', incident_id=incident.id))
'''

if 'def sheets():' not in control_code:
    control_code = control_code + phase6_control_code
    with open(control_path, 'w', encoding='utf-8') as f:
        f.write(control_code)
    print("blueprints/control.py updated with Phase 6.")
else:
    print("blueprints/control.py already has Phase 6 routes.")

# ---------------------------------------------------------------------------
# 4. Update blueprints/supervisor.py
# ---------------------------------------------------------------------------
sup_path = os.path.join(base_dir, 'blueprints', 'supervisor.py')
with open(sup_path, 'r', encoding='utf-8') as f:
    sup_code = f.read()

if 'GoogleSheetLink' not in sup_code:
    sup_code = sup_code.replace(
        'CLIMovement, CrewCounsellingLog',
        'CLIMovement, CrewCounsellingLog, GoogleSheetLink, UnusualIncident'
    )

phase6_sup_code = '''

# ---------------------------------------------------------------------------
# PHASE 6: CLI SUPERVISOR GOOGLE SHEETS & SQUAD UNUSUAL INCIDENTS
# ---------------------------------------------------------------------------

@supervisor_bp.route('/sheets', methods=['GET'])
def sheets():
    """View permitted Google Sheets for CLI."""
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
        search=search,
        is_supervisor_view=True
    )


@supervisor_bp.route('/incidents', methods=['GET'])
def incidents():
    """Squad Unusual Incidents Register for CLI."""
    cli = User.query.get(session.get('user_id'))
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    query = UnusualIncident.query.filter(
        db.or_(
            UnusualIncident.cli_id == cli.id,
            UnusualIncident.lobby_id == cli.lobby_id,
            UnusualIncident.reported_by_id == cli.id
        )
    )
    if status and status != 'ALL':
        query = query.filter_by(status=status)
    if search:
        query = query.filter(
            db.or_(
                UnusualIncident.incident_number.ilike(f'%{search}%'),
                UnusualIncident.brief_description.ilike(f'%{search}%'),
                UnusualIncident.train_no.ilike(f'%{search}%'),
                UnusualIncident.loco_no.ilike(f'%{search}%'),
                UnusualIncident.crew_name_manual.ilike(f'%{search}%')
            )
        )

    squad_incidents = query.order_by(UnusualIncident.incident_date.desc(), UnusualIncident.id.desc()).all()
    return render_template(
        'supervisor/incidents.html',
        incidents=squad_incidents,
        status=status,
        search=search
    )


@supervisor_bp.route('/incidents/new', methods=['GET', 'POST'])
def new_incident():
    """CLI logs unusual incident observed during footplate or reported by crew."""
    cli = User.query.get(session.get('user_id'))
    if request.method == 'POST':
        incident_date_str = request.form.get('incident_date', '').strip()
        incident_date = parse_date_value(incident_date_str) or date.today()
        incident_time = request.form.get('incident_time', '').strip()
        section = request.form.get('section', '').strip()
        station_location = request.form.get('station_location', '').strip()
        train_no = request.form.get('train_no', '').strip()
        loco_no = request.form.get('loco_no', '').strip()
        traction_type = request.form.get('traction_type', 'ELECTRIC').strip()
        incident_category = request.form.get('incident_category', 'MISC').strip()
        crew_id_raw = request.form.get('crew_id')
        crew_id = int(crew_id_raw) if crew_id_raw and crew_id_raw.isdigit() else None
        crew_name_manual = request.form.get('crew_name_manual', '').strip()
        alp_name_manual = request.form.get('alp_name_manual', '').strip()
        brief_description = request.form.get('brief_description', '').strip()
        primary_cause = request.form.get('primary_cause', '').strip()
        immediate_action = request.form.get('immediate_action', '').strip()
        delay_minutes = int(request.form.get('delay_minutes', 0) or 0)

        if not section or not brief_description:
            flash('Section and Brief Description are mandatory.', 'danger')
            assigned_crews = User.query.filter_by(assigned_cli_id=cli.id).order_by(User.full_name.asc()).all()
            return render_template('supervisor/incident_form.html', crews=assigned_crews)

        inc_number = UnusualIncident.generate_incident_number()
        incident = UnusualIncident(
            incident_number=inc_number,
            incident_date=incident_date,
            incident_time=incident_time,
            section=section,
            station_location=station_location,
            train_no=train_no,
            loco_no=loco_no,
            traction_type=traction_type,
            incident_category=incident_category,
            crew_id=crew_id,
            crew_name_manual=crew_name_manual,
            alp_name_manual=alp_name_manual,
            lobby_id=cli.lobby_id,
            cli_id=cli.id,
            brief_description=brief_description,
            primary_cause=primary_cause,
            immediate_action=immediate_action,
            delay_minutes=delay_minutes,
            status='REPORTED',
            reported_by_id=cli.id,
            reported_by_role='CLI'
        )
        db.session.add(incident)
        db.session.commit()
        flash(f'Unusual Incident registered as [{inc_number}] and forwarded for monitoring.', 'success')
        return redirect(url_for('supervisor.incidents'))

    assigned_crews = User.query.filter_by(assigned_cli_id=cli.id).order_by(User.full_name.asc()).all()
    return render_template('supervisor/incident_form.html', crews=assigned_crews)


@supervisor_bp.route('/incidents/<int:incident_id>', methods=['GET'])
def view_incident(incident_id):
    """View incident dossier by CLI."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    return render_template('admin/incident_detail.html', incident=incident, is_supervisor_view=True)


@supervisor_bp.route('/incidents/<int:incident_id>/action', methods=['POST'])
def record_investigation(incident_id):
    """CLI records joint inspection findings and crew counselling remarks."""
    incident = UnusualIncident.query.get_or_404(incident_id)
    findings = request.form.get('findings', '').strip()
    cause = request.form.get('primary_cause', '').strip()
    new_status = request.form.get('status', '').strip()
    cli = User.query.get(session.get('user_id'))

    if cause:
        incident.primary_cause = cause
    if findings:
        existing = incident.immediate_action or ''
        ts_str = datetime.now().strftime('%d-%m-%Y %H:%M')
        incident.immediate_action = f"{existing}\\n[{ts_str} CLI {cli.full_name} Joint Check]: {findings}".strip()
    if new_status in ('UNDER_INVESTIGATION', 'ACTION_COMPLETED', 'CLOSED'):
        incident.status = new_status

    db.session.commit()
    flash(f'Investigation and corrective counselling logged on [{incident.incident_number}].', 'success')
    return redirect(url_for('supervisor.view_incident', incident_id=incident.id))
'''

if 'def sheets():' not in sup_code:
    sup_code = sup_code + phase6_sup_code
    with open(sup_path, 'w', encoding='utf-8') as f:
        f.write(sup_code)
    print("blueprints/supervisor.py updated with Phase 6.")
else:
    print("blueprints/supervisor.py already has Phase 6 routes.")

# ---------------------------------------------------------------------------
# 5. Update blueprints/crew.py
# ---------------------------------------------------------------------------
crew_path = os.path.join(base_dir, 'blueprints', 'crew.py')
with open(crew_path, 'r', encoding='utf-8') as f:
    crew_code = f.read()

if 'GoogleSheetLink' not in crew_code:
    crew_code = crew_code.replace(
        'CrewCounsellingRecord, CrewCounsellingLog',
        'CrewCounsellingRecord, CrewCounsellingLog, GoogleSheetLink, UnusualIncident'
    )

phase6_crew_code = '''

# ---------------------------------------------------------------------------
# PHASE 6: CREW RUNNING ROSTER SHEETS & SAFETY UNUSUAL CASE STUDIES
# ---------------------------------------------------------------------------

@crew_bp.route('/sheets', methods=['GET'])
def sheets():
    """View permitted Google Sheets & Rosters for Crew."""
    crew = User.query.get(session.get('user_id'))
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()

    query = GoogleSheetLink.query.filter_by(is_active=True)
    if category and category != 'ALL':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            db.or_(
                GoogleSheetLink.title.ilike(f'%{search}%'),
                GoogleSheetLink.description.ilike(f'%{search}%')
            )
        )

    all_sheets = [s for s in query.order_by(GoogleSheetLink.display_order.asc()).all() if s.is_accessible_by(crew)]
    categories = [
        ('CREW_MONITORING', 'Crew Duty & Rosters'),
        ('TRAINING', 'Training Schedule & Circulars'),
        ('SAFETY_MONITORING', 'Safety Guidelines & Drives'),
        ('OPERATIONAL', 'Operational Instructions'),
        ('GENERAL', 'General Links')
    ]
    return render_template(
        'crew/sheets.html',
        sheets=all_sheets,
        categories=categories,
        selected_category=category,
        search=search
    )


@crew_bp.route('/unusual-reports', methods=['GET'])
def unusual_reports():
    """Safety Case Studies & Unusual Incident Alerts for running crews."""
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()

    query = UnusualIncident.query
    if category and category != 'ALL':
        query = query.filter_by(incident_category=category)
    if search:
        query = query.filter(
            db.or_(
                UnusualIncident.incident_number.ilike(f'%{search}%'),
                UnusualIncident.brief_description.ilike(f'%{search}%'),
                UnusualIncident.primary_cause.ilike(f'%{search}%')
            )
        )

    # Show recent safety incidents with cause analysis and corrective learnings
    recent_incidents = query.order_by(UnusualIncident.incident_date.desc(), UnusualIncident.id.desc()).limit(30).all()
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
        'crew/unusual_reports.html',
        incidents=recent_incidents,
        categories=categories,
        selected_category=category,
        search=search
    )
'''

if 'def sheets():' not in crew_code:
    crew_code = crew_code + phase6_crew_code
    with open(crew_path, 'w', encoding='utf-8') as f:
        f.write(crew_code)
    print("blueprints/crew.py updated with Phase 6.")
else:
    print("blueprints/crew.py already has Phase 6 routes.")

print("All blueprint updates completed!")
