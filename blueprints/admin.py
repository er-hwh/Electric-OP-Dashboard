from blueprints.reporting_helper import (
    get_crew_overview_stats, get_cli_crew_matrix, get_lobby_crew_matrix,
    filter_crews_query, export_crews_to_excel, export_crews_to_csv
)
import os
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, current_app, send_file, session, jsonify, Response
)
try:
    import pandas as pd
except ImportError:
    pd = None
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, Notice, NoticeAcknowledgement, CounsellingTopic, CounsellingAcknowledgement, 
    CrewCounsellingLog, TrainingRecord, MedicalRecord, FootplateInspection, 
    Message, OfficerSay, CrewCounsellingRecord, PhotoGallery, CustomField, CLIMovement,
    GoogleSheetLink, UnusualIncident
)
from blueprints.auth import role_required
from blueprints.excel_helper import (
    read_excel_to_dicts, map_crew_record, export_crew_master_to_excel, clean_mobile_10,
    generate_training_medical_template, parse_training_medical_excel
)

admin_bp = Blueprint('admin', __name__)

@admin_bp.before_request
@role_required('admin')
def admin_protection():
    pass

@admin_bp.route('/')
def dashboard():
    crew_count = User.query.filter_by(role='crew').count()
    cli_count = User.query.filter_by(role='supervisor', sub_role='CLI').count()
    ccc_count = User.query.filter_by(role='supervisor', sub_role='CCC').count()
    officer_count = User.query.filter_by(role='officer').count()
    lobby_count = Lobby.query.count()
    notice_count = Notice.query.count()
    counselling_count = CounsellingTopic.query.count()
    training_count = TrainingRecord.query.count()
    counselling_records_count = CrewCounsellingRecord.query.count()

    recent_users = User.query.order_by(User.created_at.desc()).limit(8).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()

    return render_template(
        'admin/dashboard.html',
        crew_count=crew_count,
        cli_count=cli_count,
        ccc_count=ccc_count,
        officer_count=officer_count,
        lobby_count=lobby_count,
        notice_count=notice_count,
        counselling_count=counselling_count,
        training_count=training_count,
        counselling_records_count=counselling_records_count,
        recent_users=recent_users,
        lobbies=lobbies
    )

@admin_bp.route('/users')
def users():
    role_filter = request.args.get('role', 'ALL')
    lobby_filter = request.args.get('lobby', 'ALL')
    search_query = request.args.get('q', '').strip()

    query = User.query
    if role_filter != 'ALL':
        query = query.filter_by(role=role_filter)
    if lobby_filter != 'ALL':
        query = query.filter_by(lobby_id=int(lobby_filter))
    if search_query:
        query = query.filter(
            (User.full_name.ilike(f'%{search_query}%')) |
            (User.username.ilike(f'%{search_query}%')) |
            (User.mobile.ilike(f'%{search_query}%')) |
            (User.pf_number.ilike(f'%{search_query}%'))
        )

    user_list = query.order_by(User.id.desc()).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI').all()

    return render_template(
        'admin/users.html',
        users=user_list,
        lobbies=lobbies,
        clis=clis,
        current_role=role_filter,
        current_lobby=lobby_filter,
        search_query=search_query
    )

@admin_bp.route('/create-control-user', methods=['POST'])
def create_control_user():
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    sub_role = request.form.get('sub_role', 'CNL').strip() or 'CNL'
    mobile = request.form.get('mobile', '').strip()
    password = request.form.get('password', '12345').strip() or '12345'
    lobby_id = request.form.get('lobby_id')

    if not username or not full_name:
        flash('CNL User ID and Staff Name are required.', 'danger')
        return redirect(url_for('admin.users'))

    # Check if username exists
    existing = User.query.filter_by(username=username).first()
    if existing:
        flash(f"User ID '{username}' is already in use. Please choose another ID.", 'warning')
        return redirect(url_for('admin.users'))

    new_user = User(
        username=username,
        role='control',
        sub_role=sub_role,
        full_name=full_name,
        mobile=mobile if mobile else None,
        lobby_id=int(lobby_id) if lobby_id and lobby_id.isdigit() else None,
        is_active=True
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    flash(f"Control (CNL) user '{username}' ({full_name}) created successfully with initial password '{password}'.", 'success')
    return redirect(url_for('admin.users', role='control'))

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        flash('Cannot deactivate system administrator.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    db.session.commit()
    status_str = "activated" if user.is_active else "deactivated"
    flash(f"User {user.full_name} ({user.username}) has been {status_str}.", "info")
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    user.set_password('12345')
    user.password_must_change = True
    db.session.commit()
    flash(f"Password for {user.full_name} ({user.username}) reset to default '12345'. User will be prompted to change it upon login.", "success")
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/assign-cli', methods=['POST'])
def assign_cli(user_id):
    crew = User.query.get_or_404(user_id)
    cli_id = request.form.get('cli_id')
    if cli_id:
        crew.cli_id = int(cli_id)
        db.session.commit()
        flash(f"Nominated CLI updated for {crew.full_name}.", "success")
    return redirect(url_for('admin.users'))


# ---------------------------------------------------------------------------
# PHASE 2: LOBBY MANAGEMENT (Main 9 + Sister 3 & CLI In-Charge Reassignment)
# ---------------------------------------------------------------------------

@admin_bp.route('/lobbies')
def lobbies():
    lobby_list = Lobby.query.order_by(Lobby.is_sister_lobby, Lobby.code).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI').order_by(User.full_name).all()
    
    lobby_stats = []
    for l in lobby_list:
        crew_cnt = User.query.filter_by(role='crew', lobby_id=l.id).count()
        cli_cnt = User.query.filter_by(role='supervisor', lobby_id=l.id).count()
        lobby_stats.append({
            'lobby': l,
            'crew_count': crew_cnt,
            'cli_count': cli_cnt,
            'in_charge': l.in_charge_cli
        })
        
    return render_template('admin/lobbies.html', lobby_stats=lobby_stats, clis=clis)


@admin_bp.route('/lobbies/<int:lobby_id>/update', methods=['POST'])
def update_lobby(lobby_id):
    lobby = Lobby.query.get_or_404(lobby_id)
    in_charge_id = request.form.get('in_charge_cli_id')
    ccc_name = request.form.get('ccc_name', '').strip()
    phone = request.form.get('phone', '').strip()
    jurisdiction = request.form.get('operational_jurisdiction', '').strip()
    description = request.form.get('description', '').strip()

    lobby.in_charge_cli_id = int(in_charge_id) if in_charge_id and in_charge_id.isdigit() else None
    lobby.ccc_name = ccc_name or lobby.ccc_name
    lobby.phone = phone
    lobby.operational_jurisdiction = jurisdiction
    lobby.description = description
    db.session.commit()

    flash(f"Lobby '{lobby.code}' ({lobby.name}) assignments updated successfully.", "success")
    return redirect(url_for('admin.lobbies'))


# ---------------------------------------------------------------------------
# PHASE 2: DYNAMIC CUSTOM FIELDS MANAGEMENT
# ---------------------------------------------------------------------------

@admin_bp.route('/custom-fields')
def custom_fields():
    fields = CustomField.query.order_by(CustomField.id.asc()).all()
    return render_template('admin/custom_fields.html', fields=fields)


@admin_bp.route('/custom-fields/add', methods=['POST'])
def add_custom_field():
    import re
    label = request.form.get('field_label', '').strip()
    f_name = request.form.get('field_name', '').strip()
    f_type = request.form.get('field_type', 'text').strip()
    is_req = bool(request.form.get('is_required'))
    options_raw = request.form.get('options', '').strip()

    if not label:
        flash("Field Label is required.", "danger")
        return redirect(url_for('admin.custom_fields'))

    if not f_name:
        f_name = re.sub(r'[^a-zA-Z0-9_]', '_', label.lower()).strip('_')
    else:
        f_name = re.sub(r'[^a-zA-Z0-9_]', '_', f_name.lower()).strip('_')

    existing = CustomField.query.filter_by(field_name=f_name).first()
    if existing:
        flash(f"A custom field with identifier '{f_name}' already exists.", "warning")
        return redirect(url_for('admin.custom_fields'))

    options_json = None
    if f_type == 'select' and options_raw:
        import json
        opts = [o.strip() for o in options_raw.split(',') if o.strip()]
        options_json = json.dumps(opts)

    new_field = CustomField(
        entity_type='crew',
        field_name=f_name,
        field_label=label,
        field_type=f_type,
        options_json=options_json,
        is_required=is_req,
        is_active=True
    )
    db.session.add(new_field)
    db.session.commit()
    flash(f"Custom field '{label}' added to crew master schema.", "success")
    return redirect(url_for('admin.custom_fields'))


@admin_bp.route('/custom-fields/<int:field_id>/toggle', methods=['POST'])
def toggle_custom_field(field_id):
    cf = CustomField.query.get_or_404(field_id)
    cf.is_active = not cf.is_active
    db.session.commit()
    status = "active" if cf.is_active else "inactive"
    flash(f"Custom field '{cf.field_label}' marked as {status}.", "info")
    return redirect(url_for('admin.custom_fields'))


@admin_bp.route('/custom-fields/<int:field_id>/delete', methods=['POST'])
def delete_custom_field(field_id):
    cf = CustomField.query.get_or_404(field_id)
    label = cf.field_label
    db.session.delete(cf)
    db.session.commit()
    flash(f"Custom field '{label}' has been removed.", "info")
    return redirect(url_for('admin.custom_fields'))


# ---------------------------------------------------------------------------
# PHASE 2: CREW MASTER DATABASE & EXCEL WORKFLOW
# ---------------------------------------------------------------------------

@admin_bp.route('/crew-master')
def crew_master():
    lobby_filter = request.args.get('lobby', 'ALL')
    cli_filter = request.args.get('cli', 'ALL')
    cat_filter = request.args.get('category', 'ALL')
    q = request.args.get('q', '').strip()

    query = User.query.filter_by(role='crew')

    if lobby_filter != 'ALL' and lobby_filter.isdigit():
        query = query.filter_by(lobby_id=int(lobby_filter))
    if cli_filter != 'ALL' and cli_filter.isdigit():
        query = query.filter_by(cli_id=int(cli_filter))
    if cat_filter != 'ALL':
        query = query.filter(User.sub_role.ilike(f'%{cat_filter}%'))
    if q:
        query = query.filter(
            (User.full_name.ilike(f'%{q}%')) |
            (User.mobile.ilike(f'%{q}%')) |
            (User.pf_number.ilike(f'%{q}%')) |
            (User.username.ilike(f'%{q}%'))
        )

    crews = query.order_by(User.full_name.asc()).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI').order_by(User.full_name).all()
    custom_fields_list = CustomField.query.filter_by(is_active=True).all()
    
    categories = ['LPM', 'LPP', 'MMAN', 'LPG', 'LPS-I', 'LPS-II', 'SALP', 'ALP']

    return render_template(
        'admin/crew_master.html',
        crews=crews,
        lobbies=lobbies,
        clis=clis,
        categories=categories,
        custom_fields=custom_fields_list,
        current_lobby=lobby_filter,
        current_cli=cli_filter,
        current_category=cat_filter,
        search_query=q,
        total_count=len(crews)
    )


@admin_bp.route('/crew-master/export')
def export_crew_master():
    crews = User.query.filter_by(role='crew').order_by(User.full_name.asc()).all()
    custom_fields_list = CustomField.query.filter_by(is_active=True).all()
    excel_buf = export_crew_master_to_excel(crews, custom_fields_list)
    filename = f"Howrah_Division_Crew_Master_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        excel_buf,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@admin_bp.route('/crew-master/<int:crew_id>/quick-update', methods=['POST'])
def quick_update_crew(crew_id):
    crew = User.query.get_or_404(crew_id)
    crew.full_name = request.form.get('full_name', crew.full_name).strip()
    crew.sub_role = request.form.get('sub_role', crew.sub_role).strip()
    new_mob = clean_mobile_10(request.form.get('mobile', crew.mobile))
    if new_mob and len(new_mob) == 10:
        crew.mobile = new_mob
    pf = request.form.get('pf_number', '').strip()
    if pf:
        crew.pf_number = pf
    lid = request.form.get('lobby_id')
    if lid and lid.isdigit():
        crew.lobby_id = int(lid)
    cli_id = request.form.get('cli_id')
    if cli_id and cli_id.isdigit():
        crew.cli_id = int(cli_id)
    
    # Custom fields update
    cfields = CustomField.query.filter_by(is_active=True).all()
    for cf in cfields:
        if cf.field_name in request.form:
            crew.set_custom_field(cf.field_name, request.form.get(cf.field_name))

    db.session.commit()
    flash(f"Updated crew profile for {crew.full_name}.", "success")
    return redirect(request.referrer or url_for('admin.crew_master'))


# ---------------------------------------------------------------------------
# PHASE 2: EXCEL UPLOAD WORKFLOW WITH INTERACTIVE EDITABLE TABLE
# ---------------------------------------------------------------------------

@admin_bp.route('/crew-master/upload')
def crew_upload_page():
    custom_fields_list = CustomField.query.filter_by(is_active=True).all()
    return render_template('admin/crew_upload.html', custom_fields=custom_fields_list)


@admin_bp.route('/crew-master/upload-preview', methods=['POST'])
def crew_upload_preview():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'No Excel file was selected.'}), 400

    fname = secure_filename(file.filename)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], f"preview_{fname}")
    file.save(file_path)

    try:
        cfields = CustomField.query.filter_by(is_active=True).all()
        records, headers = read_excel_to_dicts(file_path)
        if not records:
            return jsonify({'success': False, 'message': 'No data found in the uploaded Excel file.'}), 400

        mapped_rows = []
        seen_mobiles = set()
        seen_pfs = set()
        duplicates_in_file = []

        for idx, r in enumerate(records, 1):
            m = map_crew_record(r, cfields)
            mob = m['mobile']
            pf = m['pf_number']
            
            is_dup = False
            dup_reasons = []
            if mob:
                if mob in seen_mobiles:
                    is_dup = True
                    dup_reasons.append(f"Duplicate Mobile: {mob}")
                seen_mobiles.add(mob)

            if pf:
                if pf in seen_pfs:
                    is_dup = True
                    dup_reasons.append(f"Duplicate PF: {pf}")
                seen_pfs.add(pf)

            m['row_id'] = idx
            m['is_duplicate'] = is_dup
            m['duplicate_info'] = ', '.join(dup_reasons)
            mapped_rows.append(m)

            if is_dup:
                duplicates_in_file.append({'row': idx, 'info': ', '.join(dup_reasons)})

        lobbies = [{'id': l.id, 'code': l.code, 'name': l.name} for l in Lobby.query.order_by(Lobby.code).all()]
        clis = [{'id': u.id, 'username': u.username, 'name': u.full_name} for u in User.query.filter_by(role='supervisor', sub_role='CLI').all()]
        cf_defs = [{'field_name': cf.field_name, 'field_label': cf.field_label, 'field_type': cf.field_type} for cf in cfields]

        return jsonify({
            'success': True,
            'total_rows': len(mapped_rows),
            'duplicates_count': len(duplicates_in_file),
            'rows': mapped_rows,
            'lobbies': lobbies,
            'clis': clis,
            'custom_fields': cf_defs
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error reading Excel file: {str(e)}"}), 500
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass


@admin_bp.route('/crew-master/save-batch', methods=['POST'])
def save_crew_batch():
    data = request.get_json() or {}
    rows = data.get('rows', [])
    if not rows:
        return jsonify({'success': False, 'message': 'No crew records to save.'}), 400

    created_count = 0
    updated_count = 0
    errors = []

    lobbies_by_code = {l.code.upper(): l for l in Lobby.query.all()}
    clis_by_uname = {u.username.upper(): u for u in User.query.filter_by(role='supervisor').all()}
    clis_by_name = {u.full_name.strip().upper(): u for u in User.query.filter_by(role='supervisor').all()}

    for idx, r in enumerate(rows, 1):
        raw_mob = str(r.get('mobile', '')).strip()
        clean_mob = clean_mobile_10(raw_mob)
        crew_name = str(r.get('crew_name', '')).strip()
        pf = str(r.get('pf_number', '')).strip()
        desig = str(r.get('designation', '')).strip()
        cat = str(r.get('category', 'ALP')).strip() or 'ALP'
        lobby_code = str(r.get('lobby', '')).strip().upper()
        cli_id_str = str(r.get('cli_id', '')).strip().upper()
        cli_name_str = str(r.get('cli_name', '')).strip().upper()
        custom_vals = r.get('custom_fields', {})

        if not clean_mob or len(clean_mob) != 10:
            errors.append(f"Row {idx}: Invalid 10-digit mobile number ({raw_mob}) for {crew_name}.")
            continue
        if not crew_name:
            errors.append(f"Row {idx}: Missing Crew Name.")
            continue

        # Resolve Lobby
        lobby_obj = lobbies_by_code.get(lobby_code)

        # Resolve CLI
        cli_obj = None
        if cli_id_str and cli_id_str in clis_by_uname:
            cli_obj = clis_by_uname[cli_id_str]
        elif cli_name_str and cli_name_str in clis_by_name:
            cli_obj = clis_by_name[cli_name_str]
        elif cli_id_str:
            # Auto-create CLI account
            cli_mob = clean_mobile_10(r.get('cli_mobile', ''))
            new_cli = User(
                username=cli_id_str,
                role='supervisor',
                sub_role='CLI',
                full_name=r.get('cli_name', cli_id_str),
                mobile=cli_mob,
                password_must_change=True
            )
            new_cli.set_password('12345')
            db.session.add(new_cli)
            db.session.flush()
            clis_by_uname[cli_id_str] = new_cli
            cli_obj = new_cli

        # Find existing crew by mobile or PF
        user = User.query.filter(
            (User.mobile == clean_mob) |
            (User.username == clean_mob) |
            (User.pf_number == pf if pf else False)
        ).first()

        if user:
            user.full_name = crew_name
            user.mobile = clean_mob
            if pf:
                user.pf_number = pf
            user.sub_role = cat or desig or user.sub_role
            if lobby_obj:
                user.lobby_id = lobby_obj.id
            if cli_obj:
                user.cli_id = cli_obj.id
            for k, v in custom_vals.items():
                user.set_custom_field(k, v)
            updated_count += 1
        else:
            user = User(
                username=clean_mob,
                role='crew',
                sub_role=cat or desig or 'ALP',
                full_name=crew_name,
                mobile=clean_mob,
                pf_number=pf,
                lobby_id=lobby_obj.id if lobby_obj else None,
                cli_id=cli_obj.id if cli_obj else None,
                password_must_change=True,
                is_active=True
            )
            user.set_password('12345')
            for k, v in custom_vals.items():
                user.set_custom_field(k, v)
            db.session.add(user)
            created_count += 1

    db.session.commit()
    return jsonify({
        'success': True,
        'created': created_count,
        'updated': updated_count,
        'errors': errors,
        'message': f"Master Crew Database updated: {created_count} added, {updated_count} updated."
    })



# ─────────────────────────────────────────────────────────────────
#  EXCEL UPLOAD  — multi-file, 5 upload types
# ─────────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}

def _allowed_file(filename):
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS


def _safe_str(val):
    """Convert any cell value to a clean string, handling NaN/None while strictly keeping leading zeros."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ''
    s = str(val).strip()
    # If a float string like '12345.0' came through from raw pandas, remove trailing '.0' without losing leading zeros
    if s.endswith('.0') and not s.endswith('..0'):
        base = s[:-2]
        if base.replace('-', '').isdigit():
            s = base
    return s


def _find_header_row(df_raw):
    """
    CMS reports dump 1-2 title rows before the actual header.
    Detect the real header row by looking for the row that has the most
    non-empty cells and contains at least one recognisable keyword.
    Returns the 0-based index of the header row within df_raw.
    """
    keywords = {'NAME', 'CREW', 'CLI', 'LI ID', 'CREWID', 'CREW ID',
                'DESIGNATION', 'MOBILE', 'DESIG', 'HRMS', 'CADRE', 'SNO', 'S.NO',
                'SL NO.', 'SL NO', 'GRADE', 'HQ', 'DOB', 'DOA'}
    for i, row in df_raw.iterrows():
        cells = [str(v).strip().upper() for v in row if str(v).strip()]
        if any(kw in cells for kw in keywords) and len(cells) >= 3:
            return i
    return 0  # fallback: first row


def _load_cms_excel(file_path):
    """
    Load a CMS-style Excel that has 1-2 title rows before the real column
    header. Reads all columns strictly as string (dtype=str) to guarantee
    preservation of leading zeros in Staff PF, CUG, Mobile, Crew ID, etc.
    """
    df_raw = pd.read_excel(file_path, header=None, dtype=str)
    hdr_idx = _find_header_row(df_raw)
    # Use that row as header, reading all cells as string to preserve leading zeros
    df = pd.read_excel(file_path, header=hdr_idx, dtype=str)
    df.columns = [str(c).strip().upper() for c in df.columns]
    # Drop rows where all values are NaN
    df.dropna(how='all', inplace=True)
    return df


@admin_bp.route('/upload-excel', methods=['GET', 'POST'])
def upload_excel():
    lobbies = Lobby.query.order_by(Lobby.code).all()

    if request.method == 'POST':
        upload_type = request.form.get('upload_type')  # 'crew_data' | 'crew_summary' | 'cli_biodata' | 'counselling' | 'training'
        files = request.files.getlist('files')  # multiple files

        if not files or all(f.filename == '' for f in files):
            flash('No files selected. Please choose at least one Excel file.', 'danger')
            return redirect(url_for('admin.upload_excel'))

        total_processed = 0
        total_files = 0
        errors = []

        for file in files:
            if not file or not file.filename:
                continue
            filename = secure_filename(file.filename)
            if not _allowed_file(filename):
                errors.append(f"'{filename}' skipped — not an Excel file (.xlsx/.xls).")
                continue

            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            total_files += 1

            try:
                if upload_type == 'crew_data':
                    df = _load_cms_excel(file_path)
                    count = process_crew_data_excel(df)
                    total_processed += count

                elif upload_type == 'crew_summary':
                    df = _load_cms_excel(file_path)
                    count = process_crew_summary_excel(df)
                    total_processed += count

                elif upload_type == 'cli_biodata':
                    df = _load_cms_excel(file_path)
                    count = process_cli_biodata_excel(df)
                    total_processed += count

                elif upload_type == 'counselling':
                    # Counselling master sheet has proper headers in row 1; read as dtype=str to preserve leading zeros
                    df = pd.read_excel(file_path, dtype=str)
                    df.columns = [str(c).strip().upper() for c in df.columns]
                    df.dropna(how='all', inplace=True)
                    count = process_counselling_excel(df)
                    total_processed += count

                elif upload_type == 'training':
                    df = pd.read_excel(file_path, dtype=str)
                    df.columns = [str(c).strip().upper() for c in df.columns]
                    df.dropna(how='all', inplace=True)
                    count = process_training_excel(df)
                    total_processed += count

                else:
                    errors.append(f"Unknown upload type '{upload_type}'.")
                    break

            except Exception as e:
                errors.append(f"Error in '{filename}': {str(e)}")

        # Flash results
        label_map = {
            'crew_data': 'Crew Data (CMS)',
            'crew_summary': 'Crew Summary / Bio',
            'cli_biodata': 'CLI Bio Data',
            'counselling': 'Crew Counselling Records',
            'training': 'Training Records',
        }
        label = label_map.get(upload_type, upload_type)
        if total_processed > 0:
            flash(
                f"✅ {label}: {total_processed} records processed from {total_files} file(s). "
                f"All crew/CLI pre-activated with default password '12345'.",
                "success"
            )
        if errors:
            for err in errors:
                flash(err, 'warning')
        if total_processed == 0 and not errors:
            flash("No valid data rows found in the uploaded file(s). Check the format.", "warning")

        return redirect(url_for('admin.upload_excel'))

    return render_template('admin/upload_excel.html', lobbies=lobbies)


# ─────────────────────────────────────────────────────────────────
#  PARSER 1 — CMS Call Serve Report  (Crew Data)
#  Columns: SNO | CREW ID | CREW NAME | CREW DESIGNATION | MOBILE NO | EMAIL ID | CALL SERVE ADDRESS | PERMANENT ADDRESS
# ─────────────────────────────────────────────────────────────────

def process_crew_data_excel(df):
    """Parse CMS Call Serve / Crew Data report. Login username = mobile number."""
    from werkzeug.security import generate_password_hash
    default_hash = generate_password_hash('12345')
    
    success_count = 0
    lobby_map = {l.code.upper(): l.id for l in Lobby.query.all()}
    
    # Pre-load all users into in-memory dicts to avoid queries and autoflush locks
    existing_users = User.query.all()
    users_by_username = {u.username: u for u in existing_users if u.username}
    users_by_mobile = {u.mobile: u for u in existing_users if u.mobile}
    users_by_pf = {u.pf_number: u for u in existing_users if u.pf_number}

    DESIG_MAP = {
        'ASST LOCO PILOT': 'ALP',
        'ASSISTANT LOCO PILOT': 'ALP',
        'SR ASST LOCO PILOT': 'Sr. ALP',
        'SENIOR ASST LOCO PILOT': 'Sr. ALP',
        'LOCO PILOT PASSENGER': 'LPP',
        'LOCO PILOT GOODS': 'LPG',
        'LOCO PILOT MAIL': 'LPM',
        'LOCO PILOT MAIL/EXPRESS': 'LPM',
        'MOTORMAN': 'MMAN',
        'SR LOCO PILOT SHUNTER': 'LPS-II',
        'LOCO PILOT SHUNTER': 'LPS-I',
    }

    for idx, row in df.iterrows():
        # Skip header repeats or empty rows
        crew_id_str = _safe_str(row.get('CREW ID', ''))
        if not crew_id_str or crew_id_str.upper() in ('CREW ID', 'SNO', ''):
            continue

        mobile_raw = _safe_str(row.get('MOBILE NO', row.get('MOBILE', '')))
        # CMS stores mobile with country code prefix 91 — strip it
        mobile = mobile_raw.lstrip('91') if mobile_raw.startswith('91') and len(mobile_raw) == 12 else mobile_raw
        # Keep only digits
        mobile = ''.join(filter(str.isdigit, mobile))
        if len(mobile) < 10:
            mobile = mobile_raw  # fallback
        mobile = mobile[-10:]  # last 10 digits

        crew_name = _safe_str(row.get('CREW NAME', ''))
        if not crew_name:
            continue

        desig_raw = _safe_str(row.get('CREW DESIGNATION', row.get('DESIGNATION', 'ALP'))).upper()
        desig = DESIG_MAP.get(desig_raw, desig_raw) or 'ALP'

        # Derive lobby from Crew ID prefix (e.g. AZ1069 → AZ, HWH7009 → HWH)
        lobby_id = None
        for lcode in sorted(lobby_map.keys(), key=len, reverse=True):
            if crew_id_str.upper().startswith(lcode):
                lobby_id = lobby_map[lcode]
                break

        email = _safe_str(row.get('EMAIL ID', row.get('EMAIL', '')))

        # Username = mobile (10-digit); fallback = crew ID
        username = mobile if len(mobile) == 10 else crew_id_str

        # Check existing in-memory
        user = users_by_username.get(username) or (mobile and users_by_mobile.get(mobile)) or users_by_pf.get(crew_id_str)

        if not user:
            user = User(
                username=username,
                password_hash=default_hash,
                role='crew',
                sub_role=desig,
                full_name=crew_name,
                mobile=mobile if mobile else None,
                email=email if email else None,
                pf_number=crew_id_str,  # store CMS Crew ID in pf_number field
                lobby_id=lobby_id,
                is_active=True,
                password_must_change=True
            )
            db.session.add(user)
            users_by_username[username] = user
            if mobile:
                users_by_mobile[mobile] = user
            if crew_id_str:
                users_by_pf[crew_id_str] = user
        else:
            user.full_name = crew_name
            user.sub_role = desig
            if email:
                user.email = email
            if lobby_id:
                user.lobby_id = lobby_id
            if not user.pf_number:
                user.pf_number = crew_id_str
            user.is_active = True

        success_count += 1
        if success_count % 500 == 0:
            db.session.commit()

    db.session.commit()
    return success_count


# ─────────────────────────────────────────────────────────────────
#  PARSER 2 — CMS Crew Bio Summary
#  Cols: S.NO|CREWID|CREW NAME|FATHER|GENDER|HRMS ID|TRACTION|CADRE|MOBILE NO|CREW TYPE|
#        BASIC PAY|AVAIL DATE|EMP CODE|AU CODE|Edu.Qual.|Tech.Qual.|DOB|APP.DATE|
#        I.PME|LASTPROM.|B.Grp.|VISION|T.MARK|CLI Name|Crew Grade|Crew Photo
# ─────────────────────────────────────────────────────────────────

def process_crew_summary_excel(df):
    """Parse CMS Crew Bio Summary. Enriches existing crew accounts with bio data."""
    from werkzeug.security import generate_password_hash
    default_hash = generate_password_hash('12345')

    success_count = 0
    lobby_map = {l.code.upper(): l.id for l in Lobby.query.all()}
    all_clis_by_name = {c.full_name.strip().upper(): c.id for c in User.query.filter_by(role='supervisor').all()}

    existing_users = User.query.all()
    users_by_username = {u.username: u for u in existing_users if u.username}
    users_by_mobile = {u.mobile: u for u in existing_users if u.mobile}
    users_by_pf = {u.pf_number: u for u in existing_users if u.pf_number}

    TYPE_TO_DESIG = {
        'GDM': 'LPM', 'GD': 'LPG', 'GDS': 'LPS-I', 'GDS2': 'LPS-II',
        'EXP': 'LPP', 'MMAN': 'MMAN', 'ALP': 'ALP', 'SALP': 'Sr. ALP',
    }

    for _, row in df.iterrows():
        crew_id = _safe_str(row.get('CREWID', row.get('CREW ID', '')))
        if not crew_id or crew_id.upper() in ('CREWID', 'CREW ID', 'S.NO', 'SNO'):
            continue

        crew_name = _safe_str(row.get('CREW NAME', ''))
        if not crew_name:
            continue

        mobile_raw = _safe_str(row.get('MOBILE NO', row.get('MOBILE', '')))
        mobile = ''.join(filter(str.isdigit, mobile_raw))[-10:] if mobile_raw else ''

        hrms_id = _safe_str(row.get('HRMS ID', row.get('HRMS', '')))
        crew_type = _safe_str(row.get('CREW TYPE', '')).upper()
        cli_name = _safe_str(row.get('CLI NAME', '')).upper()

        desig = TYPE_TO_DESIG.get(crew_type, crew_type or 'ALP')

        # Lobby from crew ID prefix
        lobby_id = None
        for lcode in sorted(lobby_map.keys(), key=len, reverse=True):
            if crew_id.upper().startswith(lcode):
                lobby_id = lobby_map[lcode]
                break

        cli_user_id = all_clis_by_name.get(cli_name)

        username = mobile if len(mobile) == 10 else crew_id
        user = users_by_username.get(username) or (mobile and users_by_mobile.get(mobile)) or users_by_pf.get(crew_id)

        if not user:
            user = User(
                username=username,
                password_hash=default_hash,
                role='crew',
                sub_role=desig,
                full_name=crew_name,
                mobile=mobile if mobile else None,
                hrms_id=hrms_id if hrms_id else None,
                pf_number=crew_id,
                lobby_id=lobby_id,
                cli_id=cli_user_id,
                is_active=True,
                password_must_change=True
            )
            db.session.add(user)
            users_by_username[username] = user
            if mobile:
                users_by_mobile[mobile] = user
            users_by_pf[crew_id] = user
        else:
            user.full_name = crew_name
            user.sub_role = desig
            if hrms_id:
                user.hrms_id = hrms_id
            if lobby_id:
                user.lobby_id = lobby_id
            if cli_user_id:
                user.cli_id = cli_user_id
            if not user.pf_number:
                user.pf_number = crew_id
            user.is_active = True

        success_count += 1
        if success_count % 500 == 0:
            db.session.commit()

    db.session.commit()
    return success_count


# ─────────────────────────────────────────────────────────────────
#  PARSER 3 — CMS CLI/TI Bio Data
#  Cols (row 3+): 1(serial)|LI ID|NAME|FATHER NAME|HQ|DOB*|DOA*|DOP*|EMP NO|PAN NO|
#                 QUALIFICATION|BASIC PAY|DESIG|MOBILE NO|ADDRESS
# ─────────────────────────────────────────────────────────────────

def process_cli_biodata_excel(df):
    """Parse CMS CLI/TI Bio Data report. Creates or updates supervisor accounts."""
    from werkzeug.security import generate_password_hash
    default_hash = generate_password_hash('12345')

    success_count = 0
    lobby_map = {l.code.upper(): l.id for l in Lobby.query.all()}

    existing_users = User.query.all()
    users_by_username = {u.username: u for u in existing_users if u.username}

    for _, row in df.iterrows():
        li_id = _safe_str(row.get('LI ID', row.get('CLI ID', row.get('LI_ID', ''))))
        if not li_id or li_id.upper() in ('LI ID', 'CLI ID', 'NAME', ''):
            continue
        if li_id.isdigit():
            continue

        name = _safe_str(row.get('NAME', ''))
        if not name:
            continue

        hq = _safe_str(row.get('HQ', '')).upper()
        emp_no = _safe_str(row.get('EMP NO', row.get('EMP_NO', '')))
        desig = _safe_str(row.get('DESIG', 'Chief Loco Inspector'))

        mobile_raw = _safe_str(row.get('MOBILE NO', row.get('MOBILE', '')))
        mobile = ''.join(filter(str.isdigit, mobile_raw))
        if len(mobile) == 12 and mobile.startswith('91'):
            mobile = mobile[2:]
        mobile = mobile[-10:] if len(mobile) >= 10 else mobile_raw

        lobby_id = lobby_map.get(hq)

        desig_upper = desig.upper()
        if 'CHIEF' in desig_upper:
            sub_role = 'CLI'
        elif 'TRAINING' in desig_upper or 'TI' in desig_upper:
            sub_role = 'TI'
        else:
            sub_role = 'CLI'

        user = users_by_username.get(li_id)
        if not user:
            user = User(
                username=li_id,
                password_hash=default_hash,
                role='supervisor',
                sub_role=sub_role,
                full_name=name,
                mobile=mobile if mobile else None,
                pf_number=emp_no if emp_no else None,
                lobby_id=lobby_id,
                is_active=True,
                password_must_change=True
            )
            db.session.add(user)
            users_by_username[li_id] = user
        else:
            user.full_name = name
            if mobile:
                user.mobile = mobile
            if lobby_id:
                user.lobby_id = lobby_id
            if emp_no and not user.pf_number:
                user.pf_number = emp_no
            user.is_active = True

        success_count += 1

    db.session.commit()
    return success_count


# ─────────────────────────────────────────────────────────────────
#  PARSER 4 — Crew Counselling Master Sheet
#  Cols: Sl No.|CLI|CREW NAME|CREW ID|CREW HQ|CUG|DESG|DESG SINCE|PF NO|GRADE|
#        LAST FOOTPLATE|TECHINCAL COUNSELLING|SAFETY COUNSELLING|COUNSELLING VERIFIED BY|
#        LAST SPM CHECKING DATE|LAST CVVRS CHECKING DATE|BA FAIL TEST HISTORY|
#        Mobile habit|SPAD HISTORY|DA CASE|FAMILY ISSUE|HEALTH ISSUE|Baby below 6 month age|
#        Accident Prone|Remarks|Family issue|Health issue|DA Case
# ─────────────────────────────────────────────────────────────────

def process_counselling_excel(df):
    """Parse Crew Counselling Master Sheet into CrewCounsellingRecord table."""
    success_count = 0

    # Build crew lookup by crew ID or mobile
    crew_by_crew_id = {}
    for c in User.query.filter_by(role='crew').all():
        if c.pf_number:
            crew_by_crew_id[c.pf_number.strip().upper()] = c.id
        if c.username:
            crew_by_crew_id[c.username.strip().upper()] = c.id

    # Pre-load existing counselling records into memory
    existing_records = {r.crew_id_str: r for r in CrewCounsellingRecord.query.all() if r.crew_id_str}

    for _, row in df.iterrows():
        row_upper = {str(k).strip().upper(): v for k, v in row.items()}

        crew_id_str = _safe_str(row_upper.get('CREW ID', ''))
        crew_name = _safe_str(row_upper.get('CREW NAME', ''))

        if not crew_id_str or crew_id_str.upper() in ('CREW ID', ''):
            continue
        if not crew_name:
            continue

        cli_name = _safe_str(row_upper.get('CLI', ''))
        crew_hq = _safe_str(row_upper.get('CREW HQ', ''))
        cug = _safe_str(row_upper.get('CUG', ''))
        desig = _safe_str(row_upper.get('DESG', ''))
        desig_since = _safe_str(row_upper.get('DESG SINCE', ''))
        pf_no = _safe_str(row_upper.get('PF NO', ''))
        grade = _safe_str(row_upper.get('GRADE', ''))
        last_footplate = _safe_str(row_upper.get('LAST FOOTPLATE', ''))
        tech_counselling = _safe_str(row_upper.get('TECHINCAL COUNSELLING', row_upper.get('TECHNICAL COUNSELLING', '')))
        safety_counselling = _safe_str(row_upper.get('SAFETY COUNSELLING', ''))
        verified_by = _safe_str(row_upper.get('COUNSELLING VERIFIED BY', ''))
        last_spm = _safe_str(row_upper.get('LAST SPM CHECKING DATE', ''))
        last_cvvrs = _safe_str(row_upper.get('LAST CVVRS CHECKING DATE', ''))
        ba_fail = _safe_str(row_upper.get('BA FAIL TEST HISTORY', ''))
        mobile_habit = _safe_str(row_upper.get('MOBILE HABIT', ''))
        spad_history = _safe_str(row_upper.get('SPAD HISTORY', ''))
        da_case = _safe_str(row_upper.get('DA CASE', ''))
        family_issue_col = _safe_str(row_upper.get('FAMILY ISSUE', ''))
        health_issue_col = _safe_str(row_upper.get('HEALTH ISSUE', ''))
        baby_6m = _safe_str(row_upper.get('BABY BELOW 6 MONTH AGE', ''))
        accident_prone = _safe_str(row_upper.get('ACCIDENT PRONE', ''))
        remarks = _safe_str(row_upper.get('REMARKS', ''))

        crew_user_id = crew_by_crew_id.get(crew_id_str.upper())

        rec = existing_records.get(crew_id_str)
        if not rec:
            rec = CrewCounsellingRecord(crew_id_str=crew_id_str)
            db.session.add(rec)
            existing_records[crew_id_str] = rec

        rec.crew_user_id = crew_user_id
        rec.cli_name = cli_name
        rec.crew_name = crew_name
        rec.crew_hq = crew_hq
        rec.cug = cug[:30] if cug else ''
        rec.designation = desig[:30] if desig else ''
        rec.designation_since = desig_since[:50] if desig_since else ''
        rec.pf_no = pf_no[:50] if pf_no else ''
        rec.grade = grade[:10] if grade else ''
        rec.last_footplate = last_footplate[:100] if last_footplate else ''
        rec.technical_counselling = tech_counselling[:100] if tech_counselling else ''
        rec.safety_counselling = safety_counselling[:100] if safety_counselling else ''
        rec.counselling_verified_by = verified_by[:100] if verified_by else ''
        rec.last_spm_check = last_spm[:100] if last_spm else ''
        rec.last_cvvrs_check = last_cvvrs[:100] if last_cvvrs else ''
        rec.ba_fail_history = ba_fail[:100] if ba_fail else ''
        rec.mobile_habit = mobile_habit[:100] if mobile_habit else ''
        rec.spad_history = spad_history[:100] if spad_history else ''
        rec.da_case = da_case[:100] if da_case else ''
        rec.family_issue = family_issue_col[:100] if family_issue_col else ''
        rec.health_issue = health_issue_col[:100] if health_issue_col else ''
        rec.baby_below_6_months = baby_6m[:20] if baby_6m else ''
        rec.accident_prone = accident_prone[:20] if accident_prone else ''
        rec.remarks = remarks

        success_count += 1
        if success_count % 500 == 0:
            db.session.commit()

    db.session.commit()
    return success_count


# ─────────────────────────────────────────────────────────────────
#  PARSER 5 — Training Records (unchanged logic, kept here)
# ─────────────────────────────────────────────────────────────────

def process_training_excel(df):
    success_count = 0
    for _, row in df.iterrows():
        identifier = None
        for col in ['MOBILE', 'PF', 'PF NUMBER', 'STAFF NO', 'HRMS ID', 'CREW ID']:
            if col in row and pd.notna(row[col]):
                identifier = str(int(float(row[col])) if isinstance(row[col], (int, float)) else str(row[col])).strip()
                break
        if not identifier:
            continue

        crew = User.query.filter(
            (User.mobile == identifier) |
            (User.username == identifier) |
            (User.pf_number == identifier)
        ).first()

        if not crew:
            continue

        training_type = "Refresher GR & SR"
        for col in ['TRAINING TYPE', 'COURSE', 'TRAINING', 'NAME OF COURSE']:
            if col in row and pd.notna(row[col]):
                training_type = str(row[col]).strip()
                break

        institute = "ZRTI Bhuli"
        for col in ['INSTITUTE', 'TRAINING CENTRE', 'SCHOOL']:
            if col in row and pd.notna(row[col]):
                institute = str(row[col]).strip()
                break

        last_done = date.today()
        for col in ['LAST DONE', 'COMPLETED DATE', 'DATE OF COMPLETION', 'DONE DATE']:
            if col in row and pd.notna(row[col]):
                try:
                    last_done = pd.to_datetime(row[col]).date()
                except Exception:
                    pass
                break

        due_date = last_done + timedelta(days=365 * 3)
        for col in ['DUE DATE', 'NEXT DUE', 'EXPIRY DATE']:
            if col in row and pd.notna(row[col]):
                try:
                    due_date = pd.to_datetime(row[col]).date()
                except Exception:
                    pass
                break

        cert_no = ""
        for col in ['CERTIFICATE', 'CERT NO', 'CERTIFICATE NO', 'MEMO NO']:
            if col in row and pd.notna(row[col]):
                cert_no = str(row[col]).strip()
                break

        rec = TrainingRecord(
            crew_id=crew.id,
            training_type=training_type,
            institute=institute,
            last_done_date=last_done,
            due_date=due_date,
            certificate_no=cert_no
        )
        db.session.add(rec)
        success_count += 1

    db.session.commit()
    return success_count


# ─────────────────────────────────────────────────────────────────
#  COUNSELLING RECORDS VIEW (admin)
# ─────────────────────────────────────────────────────────────────

@admin_bp.route('/counselling-records')
def counselling_records():
    hq_filter = request.args.get('hq', 'ALL')
    cli_filter = request.args.get('cli', '')
    grade_filter = request.args.get('grade', 'ALL')
    search_q = request.args.get('q', '').strip()

    query = CrewCounsellingRecord.query

    if hq_filter != 'ALL':
        query = query.filter(CrewCounsellingRecord.crew_hq == hq_filter)
    if cli_filter:
        query = query.filter(CrewCounsellingRecord.cli_name.ilike(f'%{cli_filter}%'))
    if grade_filter != 'ALL':
        query = query.filter(CrewCounsellingRecord.grade == grade_filter)
    if search_q:
        query = query.filter(
            (CrewCounsellingRecord.crew_name.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.crew_id_str.ilike(f'%{search_q}%')) |
            (CrewCounsellingRecord.pf_no.ilike(f'%{search_q}%'))
        )

    records = query.order_by(CrewCounsellingRecord.crew_hq, CrewCounsellingRecord.crew_name).all()
    all_hqs = db.session.query(CrewCounsellingRecord.crew_hq).distinct().order_by(CrewCounsellingRecord.crew_hq).all()
    all_grades = db.session.query(CrewCounsellingRecord.grade).distinct().order_by(CrewCounsellingRecord.grade).all()

    return render_template(
        'admin/counselling_records.html',
        records=records,
        all_hqs=[h[0] for h in all_hqs if h[0]],
        all_grades=[g[0] for g in all_grades if g[0]],
        hq_filter=hq_filter,
        cli_filter=cli_filter,
        grade_filter=grade_filter,
        search_q=search_q,
        total=len(records)
    )


# ─────────────────────────────────────────────────────────────────
#  DOWNLOAD SAMPLE TEMPLATES
# ─────────────────────────────────────────────────────────────────

@admin_bp.route('/template/<template_type>')
def download_template(template_type):
    from io import BytesIO
    output = BytesIO()

    if template_type == 'crew_data':
        data = {
            'CREW ID': ['AZ1364', 'HWH7009', 'BWN1001'],
            'CREW NAME': ['Rajib Das', 'Narendra Kr Singh', 'Arun Ghosh'],
            'CREW DESIGNATION': ['ASST LOCO PILOT', 'LOCO PILOT MAIL/EXPRESS', 'MOTORMAN'],
            'MOBILE NO': ['9876543210', '9876543211', '9876543212'],
            'EMAIL ID': ['rajib@gmail.com', '', ''],
            'CALL SERVE ADDRESS': ['RAMPURHAT PVT', 'HWH', 'BWN'],
            'PERMANENT ADDRESS': ['Vill. Nadia 741238', 'Kolkata 700001', 'Burdwan 713101'],
        }
        fname = 'Template_Crew_Data_CMS.xlsx'

    elif template_type == 'crew_summary':
        data = {
            'CREWID': ['HWH7009', 'AZ1069', 'BWN1001'],
            'CREW NAME': ['Narendra Kr Singh', 'Ashok Biswas', 'Arun Ghosh'],
            'FATHER': ['Chandrika Prasad Singh', 'Ram Biswas', 'Birendra Ghosh'],
            'GENDER': ['M', 'M', 'M'],
            'HRMS ID': ['DMPFAA', 'MMMXYZ', 'BCDPQR'],
            'CADRE': ['T', 'T', 'T'],
            'MOBILE NO': ['919330020437', '919163352084', '919002072000'],
            'CREW TYPE': ['GDM', 'MMAN', 'GD'],
            'BASIC PAY': ['74300', '56900', '63100'],
            'DOB': ['01-01-1969', '15-03-1980', '20-07-1975'],
            'APP.DATE': ['18-10-1994', '11-07-2015', '01-06-2005'],
            'I. PME': ['16-10-2020', '23-09-2023', '14-04-2024'],
            'LASTPROM.': ['13-09-2007', '11-07-2025', '01-06-2020'],
            'B.Grp.': ['B', 'A+', 'O'],
            'VISION': ['NV/D', 'NORM', 'NV/D'],
            'CLI Name': ['Sri Bidhan Ch Ray', 'AMALENDU MALAKAR', 'Sri Pulin Roy'],
            'Crew Grade': ['A', 'A', 'B'],
        }
        fname = 'Template_Crew_Summary_Bio.xlsx'

    elif template_type == 'cli_biodata':
        data = {
            'LI ID': ['HWH0097', 'HWH0125', 'HWH0099'],
            'NAME': ['Bidhan Chandra Ray', 'Amalendu Malakar', 'Tapas Rakshit'],
            'FATHER NAME': ['Late Debdas Ray', 'Lt Hare Ram Malakar', 'Late Nirmal Ch Rakshit'],
            'HQ': ['AZ', 'AZ', 'BDC'],
            'DOB*': ['29-01-1975', '01-04-1978', '20-10-1974'],
            'DOA*': ['23-05-2006', '06-01-2003', '12-07-2000'],
            'DOP*': ['13-11-2021', '18-10-2023', '06-11-2021'],
            'EMP NO': ['50209516931', '50204720581', '50209723936'],
            'PAN NO': ['APDPR9782E', 'AUHPM9981B', 'AJSPR1822N'],
            'QUALIFICATION': ['DIPLOMA', 'DME', 'DIPLOMA'],
            'BASIC PAY': ['56900', '60400', '56900'],
            'DESIG': ['Chief Loco Inspector', 'Chief Loco Inspector', 'Chief Loco Inspector'],
            'MOBILE NO': ['919002072122', '919163352096', '919163352199'],
            'ADDRESS': ['Rayan, Burdwan(E), WB 713101', 'Murshidabad, WB', 'Barrackpur, Kolkata 700112'],
        }
        fname = 'Template_CLI_BioData.xlsx'

    elif template_type == 'counselling':
        data = {
            'Sl No.': [1, 2, 3],
            'CLI': ['AMALENDU MALAKAR', 'AMALENDU MALAKAR', 'BIDHAN CHANDRA RAY'],
            'CREW NAME': ['ASHOK BISWAS MMAN', 'DIPANKAR MALIK', 'SUNIL KR MONDAL'],
            'CREW ID': ['AZ1069', 'AZ1076', 'HWH7009'],
            'CREW HQ': ['AZ', 'AZ', 'HWH'],
            'CUG': ['9163352084', '9163352087', '9330020437'],
            'DESG': ['MMAN', 'LPP', 'LPM'],
            'DESG SINCE': ['11.07.2025', '12-12-2006', '15-09-2010'],
            'PF NO': ['50200400594', '502H4778522', '50212550024'],
            'GRADE': ['A', 'A', 'B'],
            'LAST FOOTPLATE': ['23.09.2026', '12-05-2025/HWH0125', '04.08.2026'],
            'TECHINCAL COUNSELLING': ['23.09.2026', '02-06-2026/HWH0125', '04.08.2026'],
            'SAFETY COUNSELLING': ['23.09.2026', '02-06-2026/HWH0125', '04.08.2026'],
            'COUNSELLING VERIFIED BY': ['', 'CLI HWH0125', ''],
            'LAST SPM CHECKING DATE': ['NA', '', 'NA'],
            'LAST CVVRS CHECKING DATE': ['NA', '', 'NA'],
            'BA FAIL TEST HISTORY': ['NA', '', 'NA'],
            'Mobile habit': ['NA', '', 'NA'],
            'SPAD HISTORY': ['NA', '', 'NA'],
            'DA CASE': ['NA', '', 'NA'],
            'FAMILY ISSUE': ['NA', '', 'NA'],
            'HEALTH ISSUE': ['NA', '', 'NA'],
            'Baby below 6 month age': ['No', '', 'No'],
            'Accident Prone': ['NO', '', 'NO'],
            'Remarks': ['Working Satisfactorily', '', 'Good'],
        }
        fname = 'Template_Crew_Counselling_Master.xlsx'

    elif template_type == 'training':
        data = {
            'MOBILE': ['9876543210', '9876543211', '9876543212'],
            'TRAINING TYPE': ['Refresher ELEC', 'Automatic Block System', 'Refresher GR & SR'],
            'INSTITUTE': ['ZRTI Bhuli', 'DTC Howrah', 'ZRTI Bhuli'],
            'LAST DONE': ['2024-05-10', '2026-04-15', '2023-11-20'],
            'DUE DATE': ['2027-05-10', '2026-10-15', '2026-11-20'],
            'CERTIFICATE NO': ['ZRTI/2024/991', 'DTC/2026/102', 'ZRTI/2023/55'],
        }
        fname = 'Template_Training_Records.xlsx'

    else:
        flash('Invalid template requested.', 'danger')
        return redirect(url_for('admin.upload_excel'))

    df = pd.DataFrame(data)
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(
        output,
        download_name=fname,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ─────────────────────────────────────────────────────────────────
#  PHOTO GALLERY MANAGEMENT (ADMIN EXCLUSIVE)
# ─────────────────────────────────────────────────────────────────

@admin_bp.route('/gallery', methods=['GET', 'POST'])
def gallery():
    """Admin upload and manage gallery photos and descriptions."""
    ALLOWED_IMG_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'Operations').strip()
        caption = request.form.get('caption', '').strip()
        file = request.files.get('photo')

        if not title:
            flash('Photo Title is mandatory.', 'danger')
            return redirect(url_for('admin.gallery'))

        if not file or not file.filename:
            flash('Please select an image file to upload.', 'danger')
            return redirect(url_for('admin.gallery'))

        ext = os.path.splitext(file.filename.lower())[1]
        if ext not in ALLOWED_IMG_EXTS:
            flash(f'Invalid image format. Allowed formats: {", ".join(ALLOWED_IMG_EXTS)}', 'danger')
            return redirect(url_for('admin.gallery'))

        filename = f"gallery_{int(datetime.utcnow().timestamp())}_{secure_filename(file.filename)}"
        target_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(target_path)

        photo = PhotoGallery(
            title=title,
            category=category,
            image_filename=filename,
            caption=caption
        )
        db.session.add(photo)
        db.session.commit()

        flash(f'Photo "{title}" successfully published to Divisional Gallery!', 'success')
        return redirect(url_for('admin.gallery'))

    items = PhotoGallery.query.order_by(PhotoGallery.created_at.desc()).all()
    return render_template('admin/gallery.html', items=items)


@admin_bp.route('/gallery/<int:item_id>/delete', methods=['POST'])
def delete_gallery_item(item_id):
    """Delete a photo from the gallery and remove its file."""
    item = PhotoGallery.query.get_or_404(item_id)
    title = item.title
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], item.image_filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    db.session.delete(item)
    db.session.commit()
    flash(f'Photo "{title}" has been deleted from the gallery.', 'info')
    return redirect(url_for('admin.gallery'))


# ---------------------------------------------------------------------------
# SECTION 13: IMPORTANT TOOLS (ADMIN ONLY)
# ---------------------------------------------------------------------------

@admin_bp.route('/important-tools')
def important_tools():
    """Important Tools Hub (Admin-only restricted section)."""
    return render_template('admin/important_tools.html')


@admin_bp.route('/important-tools/bulk-analysis')
def bulk_analysis_tool():
    """Bulk Signal & Speed Analysis Tool."""
    return render_template('admin/tools/bulk_analysis.html')


@admin_bp.route('/important-tools/pf-entry-speed')
def pf_entry_speed_tool():
    """Platform Entry & Turnout Speed Checking Tool."""
    return render_template('admin/tools/pf_entry_speed.html')


# ---------------------------------------------------------------------------
# CLI MOVEMENT RETENTION POLICY (3 MONTHS RETENTION)
# ---------------------------------------------------------------------------

@admin_bp.route('/retention-policy', methods=['GET', 'POST'])
def retention_policy():
    """
    Manages the 3-Month (90-Day) Data Retention Policy for CLI Daily Movement logs.
    Master Crew database, counselling history, training, and medical are permanent.
    """
    cutoff = date.today() - timedelta(days=90)
    
    total_count = CLIMovement.query.count()
    active_count = CLIMovement.query.filter(CLIMovement.activity_date >= cutoff).count()
    eligible_count = CLIMovement.query.filter(CLIMovement.activity_date < cutoff).count()
    oldest_record = CLIMovement.query.order_by(CLIMovement.activity_date.asc()).first()
    oldest_date = oldest_record.activity_date if oldest_record else None

    if request.method == 'POST':
        deleted = CLIMovement.clean_old_movements(days=90)
        flash(f'Data Retention Purge Completed: {deleted} old CLI movement records older than 90 days were safely purged. All Master Crew and permanent records remain 100% intact.', 'success')
        return redirect(url_for('admin.retention_policy'))

    return render_template(
        'admin/retention_policy.html',
        total_count=total_count,
        active_count=active_count,
        eligible_count=eligible_count,
        cutoff=cutoff,
        oldest_date=oldest_date
    )


# ---------------------------------------------------------------------------
# PHASE 4: TRAINING & MEDICAL (PME) MANAGEMENT MODULE
# ---------------------------------------------------------------------------

@admin_bp.route('/training-medical')
def training_medical():
    """Central Training & Medical (PME) Management Console."""
    record_type = request.args.get('type', 'ALL').strip().upper() # ALL, TRAINING, PME
    course_filter = request.args.get('course', 'ALL').strip()
    status_filter = request.args.get('status', 'ALL').strip().upper()
    lobby_filter = request.args.get('lobby', 'ALL').strip()
    cli_filter = request.args.get('cli', 'ALL').strip()
    q = request.args.get('q', '').strip()

    today = date.today()

    # Query Trainings
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
                (User.mobile.ilike(q_wild)) |
                (TrainingRecord.certificate_no.ilike(q_wild))
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
                (User.mobile.ilike(q_wild)) |
                (MedicalRecord.certificate_no.ilike(q_wild))
            )
        medicals = m_query.order_by(MedicalRecord.due_date.asc()).all()

    # Overall Summary Metrics
    total_crews = User.query.filter_by(role='crew', is_active=True).count()
    overdue_trainings = TrainingRecord.query.filter(TrainingRecord.due_date < today).count()
    due_trainings = TrainingRecord.query.filter(TrainingRecord.due_date >= today, TrainingRecord.due_date <= today + timedelta(days=30)).count()
    overdue_pmes = MedicalRecord.query.filter(MedicalRecord.due_date < today).count()
    due_pmes = MedicalRecord.query.filter(MedicalRecord.due_date >= today, MedicalRecord.due_date <= today + timedelta(days=30)).count()

    lobbies = Lobby.query.order_by(Lobby.code).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).order_by(User.full_name).all()
    all_crews = User.query.filter_by(role='crew', is_active=True).order_by(User.full_name).all()

    return render_template(
        'admin/training_medical.html',
        trainings=trainings,
        medicals=medicals,
        total_crews=total_crews,
        overdue_trainings=overdue_trainings,
        due_trainings=due_trainings,
        overdue_pmes=overdue_pmes,
        due_pmes=due_pmes,
        lobbies=lobbies,
        clis=clis,
        all_crews=all_crews,
        current_type=record_type,
        current_course=course_filter,
        current_status=status_filter,
        current_lobby=lobby_filter,
        current_cli=cli_filter,
        current_q=q
    )


@admin_bp.route('/training-medical/template')
def download_training_medical_template():
    """Generates and downloads the standard weekly Excel update template."""
    excel_stream = generate_training_medical_template()
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Weekly_Training_PME_Update_Template.xlsx"
    )


@admin_bp.route('/training-medical/upload', methods=['GET', 'POST'])
def upload_training_medical():
    """Interactive upload and validation preview for Weekly Training & PME Excel files."""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename:
            flash('Please select an Excel file (.xlsx) to upload.', 'danger')
            return redirect(url_for('admin.training_medical'))

        try:
            parsed_rows = parse_training_medical_excel(file.stream)
            valid_count = sum(1 for r in parsed_rows if r['is_valid'])
            error_count = len(parsed_rows) - valid_count

            return render_template(
                'admin/training_medical_preview.html',
                rows=parsed_rows,
                total_count=len(parsed_rows),
                valid_count=valid_count,
                error_count=error_count,
                filename=file.filename
            )
        except Exception as e:
            flash(f'Error reading Excel file: {str(e)}', 'danger')
            return redirect(url_for('admin.training_medical'))

    return redirect(url_for('admin.training_medical'))


@admin_bp.route('/training-medical/save-batch', methods=['POST'])
def save_training_medical_batch():
    """Commits reviewed weekly Excel rows into training_records and medical_records."""
    data = request.get_json(silent=True) or {}
    rows = data.get('rows', [])

    if not rows:
        return jsonify({'success': False, 'message': 'No data rows received.'}), 400

    created_cnt = 0
    updated_cnt = 0

    for r in rows:
        user_id = r.get('crew_user_id')
        if not user_id:
            # Try to resolve by identifier
            ident = clean_mobile_10(r.get('identifier', '')) or r.get('identifier', '')
            u = User.query.filter(
                (User.mobile == ident) |
                (User.pf_number == r.get('identifier')) |
                (User.username == r.get('identifier'))
            ).first()
            if u:
                user_id = u.id

        if not user_id:
            continue

        crew = User.query.get(user_id)
        if not crew:
            continue

        done_d = datetime.strptime(r['last_done_date'], '%Y-%m-%d').date() if r.get('last_done_date') else date.today()
        due_d = datetime.strptime(r['due_date'], '%Y-%m-%d').date() if r.get('due_date') else None

        rec_type = (r.get('record_type') or 'Training').strip().upper()
        course_name = (r.get('course_name') or 'Refresher ELEC').strip()
        institute = r.get('institute') or 'ZRTI Bhuli'
        cert_no = r.get('certificate_no') or ''
        status_val = r.get('status') or 'Passed'
        remarks = r.get('remarks') or ''

        if rec_type == 'PME' or 'PME' in course_name.upper():
            # Update MedicalRecord & User PME fields
            if not due_d:
                due_d = crew.calculate_next_pme_due(done_d)

            crew.pme_last_done_date = done_d
            crew.pme_due_date = due_d
            crew.pme_fitness_status = status_val

            med_rec = MedicalRecord.query.filter_by(crew_id=crew.id).first()
            if not med_rec:
                med_rec = MedicalRecord(
                    crew_id=crew.id,
                    last_pme_date=done_d,
                    due_date=due_d,
                    hospital_name=institute,
                    certificate_no=cert_no,
                    fitness_status=status_val,
                    age_at_pme=crew.get_age(done_d),
                    frequency_years=crew.compute_pme_frequency_years(crew.get_age(done_d)),
                    remarks=remarks
                )
                db.session.add(med_rec)
                created_cnt += 1
            else:
                med_rec.last_pme_date = done_d
                med_rec.due_date = due_d
                med_rec.hospital_name = institute
                med_rec.certificate_no = cert_no
                med_rec.fitness_status = status_val
                med_rec.age_at_pme = crew.get_age(done_d)
                med_rec.frequency_years = crew.compute_pme_frequency_years(crew.get_age(done_d))
                med_rec.remarks = remarks
                updated_cnt += 1
        else:
            # Training Record
            if not due_d:
                due_d = TrainingRecord.calculate_due_date(done_d, course_name)

            t_cat = 'REFRESHER'
            if 'ABS' in course_name.upper():
                t_cat = 'ABS'
            elif 'PROMOTIONAL' in course_name.upper():
                t_cat = 'PROMOTIONAL'
            elif 'CAMP' in course_name.upper():
                t_cat = 'SAFETY_CAMP'

            t_rec = TrainingRecord.query.filter_by(crew_id=crew.id, training_type=course_name).first()
            if not t_rec:
                t_rec = TrainingRecord(
                    crew_id=crew.id,
                    training_type=course_name,
                    training_category=t_cat,
                    institute=institute,
                    last_done_date=done_d,
                    due_date=due_d,
                    certificate_no=cert_no,
                    remarks=remarks
                )
                db.session.add(t_rec)
                created_cnt += 1
            else:
                t_rec.last_done_date = done_d
                t_rec.due_date = due_d
                t_rec.institute = institute
                t_rec.certificate_no = cert_no
                t_rec.remarks = remarks
                updated_cnt += 1

    db.session.commit()
    flash(f'Weekly Update Batch Applied: {created_cnt} records added, {updated_cnt} records updated successfully.', 'success')
    return jsonify({'success': True, 'created': created_cnt, 'updated': updated_cnt})


@admin_bp.route('/training-medical/add', methods=['POST'])
def add_training_medical_single():
    """Manual individual entry of Training or PME record."""
    crew_id_val = request.form.get('crew_id')
    rec_type = request.form.get('record_type', 'TRAINING').strip().upper()
    course_name = (request.form.get('course_name') or request.form.get('training_type') or ('Periodical Medical Examination (PME)' if rec_type == 'PME' else '')).strip()
    institute = (request.form.get('institute') or request.form.get('hospital') or '').strip()
    last_done_str = (request.form.get('last_done_date') or request.form.get('completion_date') or '').strip()
    due_date_str = request.form.get('due_date', '').strip()
    cert_no = (request.form.get('certificate_no') or request.form.get('fit_memo_no') or '').strip()
    status_val = (request.form.get('status') or request.form.get('pme_status') or 'Passed').strip()
    remarks = request.form.get('remarks', '').strip()

    if not crew_id_val or not last_done_str or not course_name:
        flash('Crew, Course/Exam Name, and Last Done Date are required.', 'danger')
        return redirect(url_for('admin.training_medical'))

    crew = User.query.get(int(crew_id_val))
    if not crew:
        flash('Selected crew not found.', 'danger')
        return redirect(url_for('admin.training_medical'))

    try:
        done_date = datetime.strptime(last_done_str, '%Y-%m-%d').date()
    except ValueError:
        done_date = date.today()

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if rec_type == 'PME' or 'PME' in course_name.upper():
        if not due_date:
            due_date = crew.calculate_next_pme_due(done_date)

        crew.pme_last_done_date = done_date
        crew.pme_due_date = due_date
        crew.pme_fitness_status = status_val

        med_rec = MedicalRecord.query.filter_by(crew_id=crew.id).first()
        if not med_rec:
            med_rec = MedicalRecord(
                crew_id=crew.id,
                last_pme_date=done_date,
                due_date=due_date,
                hospital_name=institute or 'Divisional Hospital Howrah',
                certificate_no=cert_no,
                fitness_status=status_val,
                age_at_pme=crew.get_age(done_date),
                frequency_years=crew.compute_pme_frequency_years(crew.get_age(done_date)),
                remarks=remarks
            )
            db.session.add(med_rec)
        else:
            med_rec.last_pme_date = done_date
            med_rec.due_date = due_date
            med_rec.hospital_name = institute or med_rec.hospital_name
            med_rec.certificate_no = cert_no or med_rec.certificate_no
            med_rec.fitness_status = status_val
            med_rec.remarks = remarks

        db.session.commit()
        flash(f'PME Record saved for {crew.full_name} (Next Due: {due_date.strftime("%d-%b-%Y")}).', 'success')
    else:
        if not due_date:
            due_date = TrainingRecord.calculate_due_date(done_date, course_name)

        t_rec = TrainingRecord.query.filter_by(crew_id=crew.id, training_type=course_name).first()
        if not t_rec:
            t_rec = TrainingRecord(
                crew_id=crew.id,
                training_type=course_name,
                institute=institute or 'ZRTI Bhuli',
                last_done_date=done_date,
                due_date=due_date,
                certificate_no=cert_no,
                remarks=remarks
            )
            db.session.add(t_rec)
        else:
            t_rec.last_done_date = done_date
            t_rec.due_date = due_date
            t_rec.institute = institute or t_rec.institute
            t_rec.certificate_no = cert_no or t_rec.certificate_no
            t_rec.remarks = remarks

        db.session.commit()
        flash(f'Training Course [{course_name}] saved for {crew.full_name} (Next Due: {due_date.strftime("%d-%b-%Y")}).', 'success')

    return redirect(url_for('admin.training_medical'))


# ---------------------------------------------------------------------------
# PHASE 5: NOTICE & CIRCULAR MANAGEMENT
# ---------------------------------------------------------------------------

@admin_bp.route('/notices')
@admin_bp.route('/notices', endpoint='notices_list')
def notices():
    """Notice & Circular Management Console."""
    category = request.args.get('category', 'ALL').strip()
    traction = request.args.get('traction', 'ALL').strip().upper()
    status_filter = request.args.get('status', 'ALL').strip().upper()
    q = request.args.get('q', '').strip()

    query = Notice.query
    if category != 'ALL' and category:
        query = query.filter_by(category=category)
    if traction != 'ALL' and traction:
        query = query.filter_by(traction_type=traction)
    if status_filter == 'ACTIVE':
        query = query.filter_by(is_active=True)
    elif status_filter == 'INACTIVE':
        query = query.filter_by(is_active=False)
    if q:
        query = query.filter(
            (Notice.title.ilike(f"%{q}%")) |
            (Notice.content.ilike(f"%{q}%"))
        )

    all_notices = query.order_by(Notice.created_at.desc()).all()
    lobbies = Lobby.query.order_by(Lobby.code).all()
    total_crew = User.query.filter_by(role='crew', is_active=True).count() or 1

    # Attach live stats to each notice
    notice_data = []
    for n in all_notices:
        stats = n.get_compliance_stats()
        notice_data.append({
            'notice': n,
            'stats': stats
        })

    active_count = Notice.query.filter_by(is_active=True).count()
    mandatory_count = Notice.query.filter_by(is_active=True, is_mandatory=True).count()

    return render_template(
        'admin/notices.html',
        notices=notice_data,
        lobbies=lobbies,
        total_crew=total_crew,
        active_count=active_count,
        mandatory_count=mandatory_count,
        current_category=category,
        current_traction=traction,
        current_status=status_filter,
        current_q=q
    )


@admin_bp.route('/notices/new', methods=['GET', 'POST'])
def new_notice():
    """Publish a new notice or circular."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'Safety Circular').strip()
        traction_type = request.form.get('traction_type', 'ALL').strip().upper()
        content = request.form.get('content', '').strip()
        target_audience = request.form.get('target_audience', 'ALL').strip().upper()
        target_lobby_id = request.form.get('target_lobby_id')
        is_urgent = bool(request.form.get('is_urgent'))
        is_mandatory = bool(request.form.get('is_mandatory'))
        requires_signature = bool(request.form.get('requires_signature'))

        if not title:
            flash('Notice title is mandatory.', 'danger')
            return redirect(url_for('admin.new_notice'))

        file = request.files.get('file')
        file_path = None
        if file and file.filename:
            fname = secure_filename(file.filename)
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if ext in {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}:
                unique_name = f"notice_{int(datetime.utcnow().timestamp())}_{fname}"
                target = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                file.save(target)
                file_path = f"uploads/{unique_name}"

        notice = Notice(
            title=title,
            category=category,
            traction_type=traction_type,
            content=content,
            file_path=file_path,
            target_audience=target_audience,
            target_lobby_id=int(target_lobby_id) if target_lobby_id and target_audience == 'LOBBY_WISE' else None,
            published_by_id=session.get('user_id'),
            is_urgent=is_urgent,
            is_mandatory=is_mandatory,
            requires_signature=requires_signature,
            is_active=True
        )
        db.session.add(notice)
        db.session.commit()
        flash(f'Circular "{title}" published successfully across target lobbies.', 'success')
        return redirect(url_for('admin.notices'))

    lobbies = Lobby.query.order_by(Lobby.code).all()
    return render_template('admin/notice_form.html', lobbies=lobbies, notice=None)


@admin_bp.route('/notices/<int:notice_id>/edit', methods=['GET', 'POST'])
def edit_notice(notice_id):
    """Edit an existing notice."""
    notice = Notice.query.get_or_404(notice_id)
    if request.method == 'POST':
        notice.title = request.form.get('title', '').strip() or notice.title
        notice.category = request.form.get('category', notice.category).strip()
        notice.traction_type = request.form.get('traction_type', notice.traction_type).strip().upper()
        notice.content = request.form.get('content', '').strip()
        target_audience = request.form.get('target_audience', 'ALL').strip().upper()
        notice.target_audience = target_audience
        target_lobby_id = request.form.get('target_lobby_id')
        notice.target_lobby_id = int(target_lobby_id) if target_lobby_id and target_audience == 'LOBBY_WISE' else None
        notice.is_urgent = bool(request.form.get('is_urgent'))
        notice.is_mandatory = bool(request.form.get('is_mandatory'))
        notice.requires_signature = bool(request.form.get('requires_signature'))
        notice.is_active = bool(request.form.get('is_active'))

        file = request.files.get('file')
        if file and file.filename:
            fname = secure_filename(file.filename)
            ext = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''
            if ext in {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}:
                unique_name = f"notice_{int(datetime.utcnow().timestamp())}_{fname}"
                target = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_name)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                file.save(target)
                notice.file_path = f"uploads/{unique_name}"

        db.session.commit()
        flash(f'Notice "{notice.title}" updated successfully.', 'success')
        return redirect(url_for('admin.notices'))

    lobbies = Lobby.query.order_by(Lobby.code).all()
    return render_template('admin/notice_form.html', lobbies=lobbies, notice=notice)


@admin_bp.route('/notices/<int:notice_id>/toggle', methods=['POST'])
def toggle_notice(notice_id):
    """Toggle notice active status."""
    notice = Notice.query.get_or_404(notice_id)
    notice.is_active = not notice.is_active
    db.session.commit()
    state = "activated" if notice.is_active else "deactivated"
    flash(f'Notice "{notice.title}" {state}.', 'info')
    return redirect(url_for('admin.notices'))


@admin_bp.route('/notices/<int:notice_id>/delete', methods=['POST'])
def delete_notice(notice_id):
    """Delete a notice and its acknowledgements."""
    notice = Notice.query.get_or_404(notice_id)
    title = notice.title
    db.session.delete(notice)
    db.session.commit()
    flash(f'Notice "{title}" and all related acknowledgement logs deleted.', 'warning')
    return redirect(url_for('admin.notices'))


@admin_bp.route('/notices/<int:notice_id>/compliance')
def notice_compliance(notice_id):
    """Division-wide real-time acknowledgement compliance report."""
    notice = Notice.query.get_or_404(notice_id)
    lobbies = Lobby.query.order_by(Lobby.code).all()
    status_filter = request.args.get('status', 'ALL').strip().upper() # ALL, ACKNOWLEDGED, PENDING
    lobby_filter = request.args.get('lobby', 'ALL').strip().upper()
    q = request.args.get('q', '').strip()

    # Target crews
    crew_query = User.query.filter_by(role='crew', is_active=True)
    if notice.target_lobby_id:
        crew_query = crew_query.filter_by(lobby_id=notice.target_lobby_id)
    elif lobby_filter != 'ALL' and lobby_filter:
        lob = Lobby.query.filter_by(code=lobby_filter).first()
        if lob:
            crew_query = crew_query.filter_by(lobby_id=lob.id)

    if q:
        crew_query = crew_query.filter(
            (User.full_name.ilike(f"%{q}%")) |
            (User.username.ilike(f"%{q}%")) |
            (User.mobile.ilike(f"%{q}%")) |
            (User.pf_number.ilike(f"%{q}%"))
        )

    all_target_crews = crew_query.order_by(User.full_name).all()
    acked_records = {a.user_id: a for a in notice.acknowledgements.all()}

    crew_rows = []
    for c in all_target_crews:
        ack = acked_records.get(c.id)
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
    lobby_breakdown = []
    for lob in lobbies:
        l_crews = User.query.filter_by(lobby_id=lob.id, role='crew', is_active=True).all()
        l_total = len(l_crews)
        if l_total == 0:
            continue
        l_acked = sum(1 for c in l_crews if c.id in acked_records)
        pct = round((l_acked / l_total) * 100, 1)
        lobby_breakdown.append({
            'lobby': lob,
            'total': l_total,
            'acknowledged': l_acked,
            'pending': l_total - l_acked,
            'percentage': pct
        })

    # CLI breakdown
    cli_users = User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).all()
    cli_breakdown = []
    for cli in cli_users:
        squad = cli.assigned_crews.filter_by(is_active=True).all()
        s_total = len(squad)
        if s_total == 0:
            continue
        s_acked = sum(1 for c in squad if c.id in acked_records)
        pct = round((s_acked / s_total) * 100, 1)
        cli_breakdown.append({
            'cli': cli,
            'total': s_total,
            'acknowledged': s_acked,
            'pending': s_total - s_acked,
            'percentage': pct
        })

    stats = notice.get_compliance_stats()

    return render_template(
        'admin/notice_compliance.html',
        notice=notice,
        crew_rows=crew_rows,
        lobby_breakdown=lobby_breakdown,
        cli_breakdown=cli_breakdown,
        stats=stats,
        current_status=status_filter,
        current_lobby=lobby_filter,
        current_q=q,
        lobbies=lobbies
    )


@admin_bp.route('/notices/<int:notice_id>/send-reminder', methods=['POST'])
@admin_bp.route('/notices/<int:notice_id>/send-reminder', methods=['POST'], endpoint='send_notice_reminder')
def notice_send_reminder(notice_id):
    """Broadcasts a compliance alert to all unacknowledged running staff."""
    notice = Notice.query.get_or_404(notice_id)
    acked_user_ids = {a.user_id for a in notice.acknowledgements.all()}
    
    target_crews = User.query.filter_by(role='crew', is_active=True)
    if notice.target_lobby_id:
        target_crews = target_crews.filter_by(lobby_id=notice.target_lobby_id)
    unacked = [c for c in target_crews.all() if c.id not in acked_user_ids]

    sent_cnt = 0
    admin_user = User.query.get(session.get('user_id'))
    sender_id = admin_user.id if admin_user else 1

    for c in unacked:
        msg = Message(
            sender_id=sender_id,
            recipient_id=c.id,
            subject=f"URGENT COMPLIANCE REMINDER: {notice.title[:60]}",
            body=(
                f"Attention Running Staff {c.full_name} ({c.username}):\n\n"
                f"Safety Circular/Notice '{notice.title}' requires mandatory digital acknowledgement. "
                f"Please log in to your Crew Running Desk immediately and digitally record your compliance acknowledgement.\n\n"
                f"Issued by Division Electric Operation HQ."
            ),
            status='SENT'
        )
        db.session.add(msg)
        sent_cnt += 1

    db.session.commit()
    flash(f"Urgent compliance reminder dispatched to {sent_cnt} unacknowledged running staff.", 'success')
    return redirect(url_for('admin.notice_compliance', notice_id=notice.id))


# ---------------------------------------------------------------------------
# PHASE 5: COUNSELLING TOPICS & SPECIAL SAFETY DRIVES
# ---------------------------------------------------------------------------

@admin_bp.route('/counselling')
@admin_bp.route('/counselling', endpoint='counselling_list')
def counselling():
    """Divisional Safety Counselling Topics & Drives Manager."""
    c_type = request.args.get('type', 'ALL').strip().upper()
    traction = request.args.get('traction', 'ALL').strip().upper()
    status_filter = request.args.get('status', 'ALL').strip().upper()

    query = CounsellingTopic.query
    if c_type != 'ALL' and c_type:
        query = query.filter_by(counselling_type=c_type)
    if traction != 'ALL' and traction:
        query = query.filter_by(traction_type=traction)
    if status_filter != 'ALL' and status_filter:
        query = query.filter_by(status=status_filter)

    topics = query.order_by(CounsellingTopic.topic_date.desc()).all()
    total_crew = User.query.filter_by(role='crew', is_active=True).count() or 1

    return render_template(
        'admin/counselling.html',
        topics=topics,
        total_crew=total_crew,
        current_type=c_type,
        current_traction=traction,
        current_status=status_filter
    )


@admin_bp.route('/counselling/new', methods=['GET', 'POST'])
def new_counselling_topic():
    """Create a new monthly safety topic or special drive."""
    if request.method == 'POST':
        c_type = request.form.get('counselling_type', 'MONTHLY').strip().upper()
        traction_type = request.form.get('traction_type', 'ALL').strip().upper()
        month_year = request.form.get('month_year', '').strip()
        drive_name = request.form.get('drive_name', '').strip()
        title = request.form.get('title', '').strip()
        rule_reference = request.form.get('rule_reference', '').strip()
        content = request.form.get('content', '').strip()
        case_analysis = request.form.get('case_analysis', '').strip()
        is_mandatory = bool(request.form.get('is_mandatory'))

        if not title or not content:
            flash('Topic title and instructions content are required.', 'danger')
            return redirect(url_for('admin.new_counselling_topic'))

        topic = CounsellingTopic(
            counselling_type=c_type,
            traction_type=traction_type,
            month_year=month_year or datetime.now().strftime('%B %Y'),
            drive_name=drive_name,
            title=title,
            rule_reference=rule_reference,
            content=content,
            case_analysis=case_analysis,
            status='APPROVED',
            is_mandatory=is_mandatory,
            issued_by_id=session.get('user_id'),
            approval_date=datetime.utcnow()
        )
        db.session.add(topic)
        db.session.commit()
        flash(f'Safety Counselling Topic "{title}" rolled out division-wide.', 'success')
        return redirect(url_for('admin.counselling'))

    return render_template('admin/counselling_form.html', topic=None)


@admin_bp.route('/counselling/<int:topic_id>/approve', methods=['POST'])
def approve_counselling_topic(topic_id):
    """Approve a CLI proposed counselling topic."""
    topic = CounsellingTopic.query.get_or_404(topic_id)
    topic.status = 'APPROVED'
    topic.approved_by_id = session.get('user_id')
    topic.approval_date = datetime.utcnow()
    db.session.commit()
    flash(f'Counselling Topic "{topic.title}" approved and published.', 'success')
    return redirect(url_for('admin.counselling'))






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
            lobbies = Lobby.query.order_by(Lobby.name.asc()).all()
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

    lobbies = Lobby.query.order_by(Lobby.name.asc()).all()
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

    lobbies = Lobby.query.order_by(Lobby.name.asc()).all()
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
            lobbies = Lobby.query.order_by(Lobby.name.asc()).all()
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

    lobbies = Lobby.query.order_by(Lobby.name.asc()).all()
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

    lobbies = Lobby.query.order_by(Lobby.name.asc()).all()
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
            incident.immediate_action = f"{existing}\n[{ts_str} Update by Admin]: {resolution_notes}".strip()
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


# ---------------------------------------------------------------------------
# PHASE 7: ADMIN ADVANCED REPORTING SUITE
# ---------------------------------------------------------------------------

@admin_bp.route('/reports', methods=['GET'])
def reports():
    """Admin Advanced Reporting Suite."""
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
        export_base_url=url_for('admin.reports'),
        is_admin_view=True
    )


@admin_bp.route('/reports/export/excel', methods=['GET'])
def export_reports_excel():
    """Download filtered crew records as styled Excel (.xlsx) by Admin."""
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
        download_name=f"Admin_Crew_Report_{ts}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@admin_bp.route('/reports/export/csv', methods=['GET'])
def export_reports_csv():
    """Download filtered crew records as standard CSV by Admin."""
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
        headers={"Content-Disposition": f"attachment; filename=Admin_Crew_Report_{ts}.csv"}
    )


@admin_bp.route('/crew/<int:crew_id>/remark', methods=['POST'])
def add_crew_remark(crew_id):
    """Admin record observation on running crew."""
    crew = User.query.get_or_404(crew_id)
    remark = request.form.get('officer_remark', '').strip()
    grading = request.form.get('safety_grading', '').strip()

    if grading in ('A', 'B', 'C'):
        crew.safety_grading = grading

    if remark:
        existing = crew.remarks or ''
        ts_str = datetime.now().strftime('%d-%m-%Y %H:%M')
        crew.remarks = f"{existing}\n[{ts_str} - Admin Note]: {remark}".strip()

    db.session.commit()
    flash(f'Observation recorded for {crew.full_name}.', 'success')
    return redirect(url_for('admin.reports', tab='filter'))
