import os
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file, session
import pandas as pd
from werkzeug.utils import secure_filename
from database import db
from models import (
    User, Lobby, Notice, CounsellingTopic, TrainingRecord, FootplateInspection, 
    Message, OfficerSay, CrewCounsellingRecord, PhotoGallery
)
from blueprints.auth import role_required

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

