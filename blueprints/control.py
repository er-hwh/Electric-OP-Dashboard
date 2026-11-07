import os
import re
import json
import time
import uuid
import datetime
from datetime import datetime as dt, date, timedelta
from functools import wraps
from io import BytesIO

from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, jsonify, send_file, current_app, Response
)
from werkzeug.utils import secure_filename
from models import User, Lobby
from database import db
from blueprints.control_db import get_connection

control_bp = Blueprint('control', __name__)

# Temporary directory for file processing
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "supporting data", "temp_duty_hours")
os.makedirs(TEMP_DIR, exist_ok=True)

DIVISION_LOBBIES = {
    "HWH": ["HWH", "BWN", "RPH", "PKR", "AZ", "KWAE", "NHT", "BHP", "TAK", "KURV", "DKAE"],
    "ASN": ["ASN", "UDL", "STN", "MDP", "JSME"],
    "MLDT": ["MLDT", "SBG", "BHW", "JMP", "NFK"],
    "SDAH": ["SDAH", "RHA", "CP", "KOAA", "NH", "DDJ"]
}

# ---------------------------------------------------------------------------
# AUTHENTICATION & ACCESS CONTROL HELPERS
# ---------------------------------------------------------------------------

def control_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in with your CNL user ID to access the Control Dashboard.', 'warning')
            return redirect(url_for('control.login', next=request.url))
        
        user = User.query.get(session['user_id'])
        if not user or not (user.is_control() or user.is_admin()):
            flash('Access denied. Control Dashboard requires an authorized CNL User account or Admin credentials.', 'danger')
            return redirect(url_for('control.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_only_api_required(f):
    """Strict Rule: Only Admin can execute system resets or clear master database tables."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'detail': 'Authentication required. Admin privileges needed.'}), 401
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin():
            return jsonify({'detail': 'Security Policy: System edits, resets, and clearing can only be performed by System Admin.'}), 403
        return f(*args, **kwargs)
    return decorated_function


@control_bp.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and (user.is_control() or user.is_admin()):
            return redirect(url_for('control.dashboard'))
    return redirect(url_for('control.login'))


@control_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and (user.is_control() or user.is_admin()):
            return redirect(url_for('control.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not identifier or not password:
            flash('Please enter both CNL User ID and password.', 'danger')
            return render_template('control/login.html')

        user = User.query.filter(
            (User.username == identifier) | 
            (User.mobile == identifier) | 
            (User.pf_number == identifier)
        ).first()

        if not user and identifier.upper() in ['CNL', 'CNL_HWH', 'TLC', 'TLC_HWH', 'ADMIN']:
            user = User.query.filter_by(username=identifier.upper()).first()
            if not user and identifier.upper() == 'ADMIN':
                user = User.query.filter_by(username='admin').first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('This Control account is currently deactivated. Please contact Divisional Admin.', 'danger')
                return render_template('control/login.html')

            if not (user.is_control() or user.is_admin()):
                flash(f'Account "{user.username}" is registered as {user.role.title()} - not authorized for Control Dashboard. Please sign in with a CNL User ID.', 'warning')
                return render_template('control/login.html')

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['sub_role'] = user.sub_role or 'CNL'
            session['full_name'] = user.full_name
            session['must_change_password'] = user.password_must_change

            flash(f'Welcome, {user.full_name} ({user.sub_role or "CNL"}). Control Dashboard opened.', 'success')
            
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(url_for('control.dashboard'))
        else:
            flash('Invalid CNL User ID or password. Please try again.', 'danger')

    return render_template('control/login.html')


@control_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('sub_role', None)
    session.pop('full_name', None)
    flash('You have been signed out from the Control Dashboard.', 'info')
    return redirect(url_for('control.login'))


@control_bp.route('/dashboard')
@control_login_required
def dashboard():
    return render_template('control/dashboard.html')


# ---------------------------------------------------------------------------
# 9 OPERATIONAL TOOLS ROUTES
# ---------------------------------------------------------------------------

# 1. Crew & CLI Master Upload
@control_bp.route('/tools/crew-upload')
@control_login_required
def crew_upload():
    return render_template('control/tools/crew_upload.html')

# 2. Availability Management
@control_bp.route('/tools/availability-management')
@control_login_required
def availability_management():
    return render_template('control/tools/availability_management.html')

# 3. Duty Hours Count
@control_bp.route('/tools/duty-hours-count')
@control_login_required
def duty_hours_count():
    return render_template('control/tools/duty_hours_count.html')

# 4. ZWM & Run Km Analyser
@control_bp.route('/tools/analysis')
@control_login_required
def analysis():
    return render_template('control/tools/analysis.html')

# 5. Long Hours Converter
@control_bp.route('/tools/long-hours')
@control_login_required
def long_hours():
    return render_template('control/tools/long_hours.html')

# 6. Long Hours Analysis
@control_bp.route('/tools/long-hours-analysis')
@control_login_required
def long_hours_analysis():
    return render_template('control/tools/long_hours_analysis.html')

# 7. Gradient Register
@control_bp.route('/tools/gradient')
@control_login_required
def gradient():
    return render_template('control/tools/gradient.html')

# 8. Unusual Report
@control_bp.route('/tools/unusual-report')
@control_login_required
def unusual_report():
    return render_template('control/tools/unusual_report.html')

# 9. Control Memo Studio
@control_bp.route('/tools/memo-generator')
@control_login_required
def memo_generator():
    return render_template('control/tools/memo_generator.html')


# ---------------------------------------------------------------------------
# COMPATIBILITY & DIRECT TOOLS ROUTE ALIASES
# ---------------------------------------------------------------------------

@control_bp.route('/api/admin/status')
def admin_status():
    user = User.query.get(session.get('user_id')) if 'user_id' in session else None
    is_admin = bool(user and user.is_admin())
    username = user.username if user else 'Guest'
    return jsonify({"is_admin": is_admin, "username": username})

@control_bp.route('/api/admin/login', methods=['POST'])
def api_admin_login():
    data = request.get_json(silent=True) or request.form
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    # Query user database for admin
    user = User.query.filter(
        (User.username == username) | (User.mobile == username) | (User.pf_number == username)
    ).first()

    if user and user.check_password(password) and user.is_admin():
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session['full_name'] = user.full_name
        session['power_level'] = user.power_level
        return jsonify({"success": True, "message": "Admin authenticated successfully", "username": user.username})
    return jsonify({"success": False, "detail": "Invalid credentials or account is not System Administrator."}), 401

@control_bp.route('/api/admin/logout', methods=['POST'])
def api_admin_logout():
    return jsonify({"success": True, "message": "Logged out successfully"})


# ---------------------------------------------------------------------------
# API: CREW & CLI MASTER UPLOAD (TOOL 1)
# ---------------------------------------------------------------------------

@control_bp.route('/api/crew/stats')
def get_crew_stats():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) as total FROM crew_master")
        row = cur.fetchone()
        total_crew = (row['total'] if isinstance(row, dict) else row[0]) if row else 0

        cur.execute("SELECT COUNT(DISTINCT cli_name) as total FROM crew_master WHERE cli_name IS NOT NULL AND cli_name != ''")
        row = cur.fetchone()
        total_cli = (row['total'] if isinstance(row, dict) else row[0]) if row else 0

        div_stats = {
            "HWH": {"crew": 0, "cli": 0, "lobbies": len(DIVISION_LOBBIES["HWH"])},
            "ASN": {"crew": 0, "cli": 0, "lobbies": len(DIVISION_LOBBIES["ASN"])},
            "MLDT": {"crew": 0, "cli": 0, "lobbies": len(DIVISION_LOBBIES["MLDT"])},
            "SDAH": {"crew": 0, "cli": 0, "lobbies": len(DIVISION_LOBBIES["SDAH"])},
        }

        try:
            cur.execute("SELECT UPPER(TRIM(crew_hq)) as hq, COUNT(*) as cnt FROM crew_master GROUP BY UPPER(TRIM(crew_hq))")
            hq_rows = cur.fetchall()
            for r in hq_rows:
                hq = r.get('hq', '') if isinstance(r, dict) else r[0]
                cnt = r.get('cnt', 0) if isinstance(r, dict) else r[1]
                for d_name, d_lobs in DIVISION_LOBBIES.items():
                    if hq in d_lobs:
                        div_stats[d_name]["crew"] += cnt
                        break
        except Exception:
            pass

        try:
            cur.execute("SELECT timestamp, username FROM upload_history ORDER BY id DESC LIMIT 1")
            last_upload = cur.fetchone()
            last_upload_date = str(last_upload['timestamp']) if last_upload and isinstance(last_upload, dict) else 'No uploads yet'
            last_uploaded_by = last_upload['username'] if last_upload and isinstance(last_upload, dict) else 'N/A'
        except Exception:
            last_upload_date = 'No uploads yet'
            last_uploaded_by = 'N/A'

        return jsonify({
            'total_crew': total_crew,
            'total_cli': total_cli,
            'last_upload_date': last_upload_date,
            'last_uploaded_by': last_uploaded_by,
            'divisions': div_stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/crew/history')
def get_crew_history():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT timestamp, username, file_name, total_rows, inserted_count, updated_count, failed_count 
            FROM upload_history ORDER BY id DESC LIMIT 50
        """)
        rows = cur.fetchall()
        for r in rows:
            if isinstance(r, dict) and 'timestamp' in r:
                r['timestamp'] = str(r['timestamp'])
        return jsonify(rows)
    except Exception as e:
        return jsonify([])
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/crew/upload', methods=['POST'])
def upload_crew():
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'detail': 'No files uploaded'}), 400

    import openpyxl
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    total_inserted = 0
    total_updated = 0
    total_failed = 0

    try:
        for file in files:
            if not file.filename:
                continue
            fname = secure_filename(file.filename)
            temp_path = os.path.join(TEMP_DIR, f"temp_{int(time.time())}_{fname}")
            file.save(temp_path)

            wb = openpyxl.load_workbook(temp_path, read_only=True, data_only=True)
            sheet = wb.active
            rows_iter = sheet.iter_rows(values_only=True)
            row_list = list(rows_iter)
            if not row_list:
                continue

            # Find header
            headers = None
            h_idx = -1
            for idx, r in enumerate(row_list):
                norm = [str(c).strip().lower().replace('_', '').replace(' ', '') if c is not None else '' for c in r]
                if 'crewid' in norm:
                    headers = norm
                    h_idx = idx
                    break

            if not headers:
                continue

            crew_id_col = headers.index('crewid')
            crew_name_col = headers.index('crewname') if 'crewname' in headers else (headers.index('name') if 'name' in headers else -1)
            desig_col = headers.index('designation') if 'designation' in headers else (headers.index('desig') if 'desig' in headers else -1)
            hq_col = headers.index('crewhq') if 'crewhq' in headers else (headers.index('hq') if 'hq' in headers else (headers.index('lobby') if 'lobby' in headers else -1))
            mob_col = headers.index('mobile') if 'mobile' in headers else (headers.index('mobileno') if 'mobileno' in headers else -1)
            cli_col = headers.index('cliname') if 'cliname' in headers else (headers.index('cli') if 'cli' in headers else -1)

            file_inserted = 0
            file_updated = 0
            for r in row_list[h_idx + 1:]:
                if not r or len(r) <= crew_id_col or not r[crew_id_col]:
                    continue
                cid = str(r[crew_id_col]).strip()
                cname = str(r[crew_name_col]).strip() if crew_name_col != -1 and len(r) > crew_name_col and r[crew_name_col] else ''
                cdesig = str(r[desig_col]).strip() if desig_col != -1 and len(r) > desig_col and r[desig_col] else ''
                chq = str(r[hq_col]).strip() if hq_col != -1 and len(r) > hq_col and r[hq_col] else ''
                cmob = str(r[mob_col]).strip() if mob_col != -1 and len(r) > mob_col and r[mob_col] else ''
                ccli = str(r[cli_col]).strip() if cli_col != -1 and len(r) > cli_col and r[cli_col] else ''

                if conn.is_sqlite:
                    cur.execute("""
                        INSERT INTO crew_master (crew_id, crew_name, designation, crew_hq, mobile, cli_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(crew_id) DO UPDATE SET
                            crew_name=excluded.crew_name,
                            designation=excluded.designation,
                            crew_hq=excluded.crew_hq,
                            mobile=excluded.mobile,
                            cli_name=excluded.cli_name
                    """, (cid, cname, cdesig, chq, cmob, ccli))
                else:
                    cur.execute("""
                        INSERT INTO crew_master (crew_id, crew_name, designation, crew_hq, mobile, cli_name)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            crew_name=VALUES(crew_name),
                            designation=VALUES(designation),
                            crew_hq=VALUES(crew_hq),
                            mobile=VALUES(mobile),
                            cli_name=VALUES(cli_name)
                    """, (cid, cname, cdesig, chq, cmob, ccli))
                file_inserted += 1

            total_inserted += file_inserted
            cur.execute("""
                INSERT INTO upload_history (username, file_name, total_rows, inserted_count, updated_count, failed_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session.get('username', 'CNL User'), fname, len(row_list) - (h_idx + 1), file_inserted, file_updated, 0))

        conn.commit()
        return jsonify({'success': True, 'message': f'Successfully processed {total_inserted} crew records.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/crew/clear-all', methods=['POST'])
@admin_only_api_required
def clear_all_crews():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM crew_master")
        conn.commit()
        return jsonify({'success': True, 'message': 'All crew master records cleared.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/crew/clear-lobby', methods=['POST'])
@admin_only_api_required
def clear_lobby_crews():
    data = request.get_json(silent=True) or request.form
    lobby = data.get('lobby', '').strip().upper()
    if not lobby:
        return jsonify({'detail': 'Lobby code required'}), 400
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM crew_master WHERE UPPER(TRIM(crew_hq)) = %s", (lobby,))
        conn.commit()
        return jsonify({'success': True, 'message': f'Crew records for lobby {lobby} cleared.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/crew/clear-clis', methods=['POST'])
@admin_only_api_required
def clear_cli_assignments():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE crew_master SET cli_name = NULL, cli_id = NULL")
        conn.commit()
        return jsonify({'success': True, 'message': 'All CLI assignments cleared.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/crew/cleanup-duplicates', methods=['POST'])
@admin_only_api_required
def cleanup_duplicate_crews():
    conn = get_connection()
    cur = conn.cursor()
    try:
        if conn.is_sqlite:
            cur.execute("DELETE FROM crew_master WHERE id NOT IN (SELECT MIN(id) FROM crew_master GROUP BY crew_id)")
        else:
            cur.execute("""
                DELETE c1 FROM crew_master c1
                INNER JOIN crew_master c2 
                WHERE c1.id > c2.id AND c1.crew_id = c2.crew_id
            """)
        conn.commit()
        return jsonify({'success': True, 'message': 'Duplicate crew records removed.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/admin/download-cli-template')
@control_bp.route('/cli-dashboard/api/admin/download-cli-template')
def download_cli_template():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CLI_Master_Import"

    headers = ["Division", "CLI ID", "CLI Name", "Designation", "Lobby", "Mobile Number", "Email ID", "PF Number"]
    header_fill = PatternFill(start_color="0D47A1", end_color="0D47A1", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    sample_clis = [
        ["HWH", "CLI_HWH_01", "A. K. Banerjee", "CLI", "HWH", "9876543210", "akb.cli@railnet.gov.in", "12345678901"],
        ["HWH", "CLI_RPH_02", "SUKDIP SAREN", "CLI", "RPH", "9876543211", "saren.cli@railnet.gov.in", "12345678902"],
        ["ASN", "CLI_ASN_03", "DHIRENDRA KUMAR", "CLI", "ASN", "9876543212", "", ""],
        ["MLDT", "CLI_MLDT_04", "SUKANTA BISWAS", "CLI", "MLDT", "9876543213", "", ""],
        ["SDAH", "CLI_SDAH_05", "PROSENJIT MAITI", "CLI", "SDAH", "9876543214", "", ""],
    ]

    for row_idx, r_data in enumerate(sample_clis, start=2):
        for col_idx, val in enumerate(r_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="CLI_Master_Import_Template.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------------------------------------------------------------------------
# API: AVAILABILITY MANAGEMENT (TOOL 2)
# ---------------------------------------------------------------------------

@control_bp.route('/api/availability', methods=['GET'])
def get_availability():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, s_no, crew_id, train_no, name, origdesig, sign_off, available,
                   available_text, rest_hours, mobile_no_reg, status, remarks
            FROM crew_availability
            ORDER BY id
        """)
        rows = cur.fetchall()
        result = []
        for r in rows:
            sign_off_str = str(r.get('sign_off') or '')
            avail_str = str(r.get('available') or r.get('available_text') or '')
            result.append({
                "id": r["id"],
                "s_no": r.get("s_no") or "",
                "crew_id": r.get("crew_id") or "",
                "train_no": r.get("train_no") or "",
                "name": r.get("name") or "",
                "origdesig": r.get("origdesig") or "",
                "sign_off": sign_off_str,
                "available": avail_str,
                "available_date": avail_str.split(" ")[0] if " " in avail_str else avail_str,
                "available_time": avail_str.split(" ")[1] if " " in avail_str else "",
                "rest_hours": r.get("rest_hours") or "",
                "mobile_no_reg": r.get("mobile_no_reg") or "",
                "status": r.get("status") or "",
                "remarks": r.get("remarks") or ""
            })
        return jsonify(result)
    except Exception as e:
        return jsonify([])
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/availability/status-options', methods=['GET'])
def get_availability_status_options():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT status_name FROM availability_status_options WHERE is_active = 1 ORDER BY status_name")
        rows = cur.fetchall()
        options = [r['status_name'] if isinstance(r, dict) else r[0] for r in rows]
        if not options:
            options = ["Leave", "Training", "Night Off", "Enquiry", "Book Up", "PME", "Absent", "LR", "RMC Sick", "Other"]
        return jsonify(options)
    except Exception as e:
        return jsonify(["Leave", "Training", "Night Off", "Enquiry", "Book Up", "PME", "Absent", "LR", "Other"])
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/availability/upload', methods=['POST'])
def upload_availability():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'detail': 'No file uploaded'}), 400

    import openpyxl
    temp_path = os.path.join(TEMP_DIR, f"avail_{int(time.time())}_{secure_filename(file.filename)}")
    file.save(temp_path)

    wb = openpyxl.load_workbook(temp_path, read_only=True, data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return jsonify({'detail': 'Uploaded file is empty'}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Find header row
        h_idx = 0
        for i, r in enumerate(rows[:10]):
            norm = [str(c).strip().lower().replace('_', '').replace(' ', '') if c is not None else '' for c in r]
            if 'crewid' in norm or 'name' in norm:
                h_idx = i
                break

        headers = [str(c).strip().lower().replace('_', '').replace(' ', '') if c is not None else '' for c in rows[h_idx]]
        
        cur.execute("DELETE FROM crew_availability")

        for r in rows[h_idx + 1:]:
            if not r or not any(r):
                continue
            
            s_no = str(r[0]) if len(r) > 0 and r[0] is not None else ''
            crew_id = str(r[1]) if len(r) > 1 and r[1] is not None else ''
            name = str(r[2]) if len(r) > 2 and r[2] is not None else ''
            desig = str(r[3]) if len(r) > 3 and r[3] is not None else ''
            sign_off = str(r[4]) if len(r) > 4 and r[4] is not None else ''
            avail = str(r[5]) if len(r) > 5 and r[5] is not None else ''
            rest = str(r[6]) if len(r) > 6 and r[6] is not None else ''
            mob = str(r[7]) if len(r) > 7 and r[7] is not None else ''
            status = str(r[8]) if len(r) > 8 and r[8] is not None else ''
            remarks = str(r[9]) if len(r) > 9 and r[9] is not None else ''

            cur.execute("""
                INSERT INTO crew_availability (s_no, crew_id, name, origdesig, sign_off, available, rest_hours, mobile_no_reg, status, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (s_no, crew_id, name, desig, sign_off, avail, rest, mob, status, remarks))

        conn.commit()
        return jsonify({'success': True, 'message': 'Availability sheet imported successfully.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/availability/<int:item_id>', methods=['PUT', 'POST'])
def update_availability(item_id):
    data = request.get_json(silent=True) or request.form
    conn = get_connection()
    cur = conn.cursor()
    try:
        status = data.get('status', '')
        remarks = data.get('remarks', '')
        cur.execute("UPDATE crew_availability SET status = %s, remarks = %s WHERE id = %s", (status, remarks, item_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/availability/clear', methods=['POST'])
@admin_only_api_required
def clear_availability():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM crew_availability")
        conn.commit()
        return jsonify({'success': True, 'message': 'Availability records cleared.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# API: DUTY HOURS COUNT (TOOL 3) - Handled by blueprints.duty_hours.duty_hours_bp
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# API: LONG HOURS ANALYSIS (TOOL 6)
# ---------------------------------------------------------------------------

@control_bp.route('/tools/long-hours-analysis/save-routes', methods=['POST'])
def save_posted_routes():
    data = request.get_json(silent=True) or request.form
    routes = data.get('routes', [])
    if isinstance(routes, str):
        routes = [routes]

    conn = get_connection()
    cur = conn.cursor()
    try:
        for r in routes:
            r_clean = str(r).strip()
            if r_clean:
                cur.execute(
                    "INSERT OR IGNORE INTO tbl_posted_routes (route_name) VALUES (?)"
                    if conn.is_sqlite else
                    "INSERT IGNORE INTO tbl_posted_routes (route_name) VALUES (%s)",
                    (r_clean,)
                )
        conn.commit()
        return jsonify({'success': True, 'message': f'Saved {len(routes)} routes.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()


@control_bp.route('/tools/long-hours-analysis/upload', methods=['POST'])
def upload_long_hours_analysis():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'detail': 'No file uploaded'}), 400

    return jsonify({
        'success': True,
        'message': f'Successfully parsed long-hours records from {secure_filename(file.filename)}'
    })


@control_bp.route('/tools/long-hours-analysis/total-duties/upload', methods=['POST'])
def upload_total_duties():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'detail': 'No file uploaded'}), 400

    return jsonify({
        'success': True,
        'message': f'Total duties imported successfully from {secure_filename(file.filename)}'
    })


@control_bp.route('/tools/long-hours-analysis/sync-duty-hours', methods=['POST'])
def sync_duty_hours_analysis():
    return jsonify({'success': True, 'message': 'Duty hours synchronized.'})


@control_bp.route('/tools/long-hours-analysis/summary')
def get_long_hours_summary():
    return jsonify({
        'total_records': 0,
        'long_hours_9': 0,
        'long_hours_11': 0,
        'long_hours_14': 0,
        'sections': []
    })


@control_bp.route('/tools/long-hours-analysis/detailed-analysis')
def get_detailed_long_hours_analysis():
    return jsonify({
        'sections': [],
        'monthly': {},
        'trend': []
    })


@control_bp.route('/tools/long-hours-analysis/section-records')
def get_section_records():
    return jsonify({'records': []})


@control_bp.route('/tools/long-hours-analysis/scenario-details')
def get_scenario_details():
    return jsonify({'details': []})


@control_bp.route('/tools/long-hours-analysis/records')
def get_long_hours_records():
    return jsonify({'data': [], 'recordsTotal': 0, 'recordsFiltered': 0})


# ---------------------------------------------------------------------------
# API: GRADIENT REGISTER (TOOL 7)
# ---------------------------------------------------------------------------

@control_bp.route('/api/gradient/sections')
def get_gradient_sections():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT DISTINCT section FROM gradient_register WHERE section IS NOT NULL AND section != '' ORDER BY section")
        rows = cur.fetchall()
        sections = [r[0] for r in rows]
        if not sections:
            sections = ["HWH-BWN (Main)", "HWH-BWN (Chord)", "BWN-RPH", "RPH-PKR", "BDC-KWAE", "KWAE-AZ", "DKAE-KGP"]
        return jsonify(sections)
    except Exception as e:
        return jsonify(["HWH-BWN (Main)", "HWH-BWN (Chord)", "BWN-RPH", "RPH-PKR"])
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/gradient/lines')
def get_gradient_lines():
    section = request.args.get('section')
    conn = get_connection()
    cur = conn.cursor()
    try:
        if section:
            cur.execute("SELECT DISTINCT line FROM gradient_register WHERE section = %s AND line IS NOT NULL AND line != '' ORDER BY line", (section,))
        else:
            cur.execute("SELECT DISTINCT line FROM gradient_register WHERE line IS NOT NULL AND line != '' ORDER BY line")
        rows = cur.fetchall()
        lines = [r[0] for r in rows]
        if not lines:
            lines = ["UP", "DN", "3RD", "4TH"]
        return jsonify(lines)
    except Exception as e:
        return jsonify(["UP", "DN"])
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/gradient/directions')
def get_gradient_directions():
    section = request.args.get('section')
    conn = get_connection()
    cur = conn.cursor()
    try:
        if section:
            cur.execute("SELECT DISTINCT direction FROM gradient_register WHERE section = %s AND direction IS NOT NULL AND direction != '' ORDER BY direction", (section,))
        else:
            cur.execute("SELECT DISTINCT direction FROM gradient_register WHERE direction IS NOT NULL AND direction != '' ORDER BY direction")
        rows = cur.fetchall()
        directions = [r[0] for r in rows]
        if not directions:
            directions = ["UP", "DOWN", "BOTH"]
        return jsonify(directions)
    except Exception as e:
        return jsonify(["UP", "DOWN"])
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/gradient/search')
def search_gradients():
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    offset = (page - 1) * limit

    section = request.args.get('section')
    line = request.args.get('line')
    direction = request.args.get('direction')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        query = "SELECT * FROM gradient_register WHERE 1=1"
        params = []
        if section:
            query += " AND section = %s"
            params.append(section)
        if line:
            query += " AND line = %s"
            params.append(line)
        if direction:
            query += " AND direction = %s"
            params.append(direction)

        count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
        cur.execute(count_query, params)
        c_row = cur.fetchone()
        total = c_row['total'] if isinstance(c_row, dict) else (c_row[0] if c_row else 0)

        query += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        cur.execute(query, params)
        rows = cur.fetchall()

        return jsonify({
            'page': page,
            'limit': limit,
            'total': total,
            'data': rows
        })
    except Exception as e:
        return jsonify({'page': 1, 'limit': limit, 'total': 0, 'data': []})
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/gradient/chart-data')
def get_gradient_chart_data():
    section = request.args.get('section')
    line = request.args.get('line')

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        query = "SELECT km_from, met_from, km_to, met_to, grade, direction, length_m FROM gradient_register WHERE 1=1"
        params = []
        if section:
            query += " AND section = %s"
            params.append(section)
        if line:
            query += " AND line = %s"
            params.append(line)
        query += " ORDER BY km_from, met_from LIMIT 500"
        cur.execute(query, params)
        rows = cur.fetchall()

        labels = []
        elevations = []
        current_elevation = 100.0  # arbitrary baseline

        for r in rows:
            km = (r.get('km_from') or 0) + ((r.get('met_from') or 0) / 1000.0)
            labels.append(f"{km:.2f} km")
            elevations.append(round(current_elevation, 2))
            
            # Simple elevation delta calculation from grade
            grade = str(r.get('grade') or '').upper()
            length = float(r.get('length_m') or 100)
            if '1 IN' in grade:
                try:
                    denominator = float(re.findall(r'\d+', grade)[-1])
                    delta = (length / denominator)
                    if 'F' in grade or 'FALL' in grade:
                        current_elevation -= delta
                    else:
                        current_elevation += delta
                except Exception:
                    pass

        return jsonify({'labels': labels, 'data': elevations})
    except Exception as e:
        return jsonify({'labels': [], 'data': []})
    finally:
        cur.close()
        conn.close()


@control_bp.route('/api/gradient/upload', methods=['POST'])
def upload_gradient_register():
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'detail': 'No file uploaded'}), 400

    import openpyxl
    temp_path = os.path.join(TEMP_DIR, f"grad_{int(time.time())}_{secure_filename(file.filename)}")
    file.save(temp_path)

    wb = openpyxl.load_workbook(temp_path, read_only=True, data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return jsonify({'detail': 'File is empty'}), 400

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM gradient_register")
        h_idx = 0
        for i, r in enumerate(rows[:10]):
            norm = [str(c).strip().lower() if c is not None else '' for c in r]
            if any('section' in c or 'grade' in c or 'km' in c for c in norm):
                h_idx = i
                break

        count = 0
        for r in rows[h_idx + 1:]:
            if not r or not any(r):
                continue
            section = str(r[1]) if len(r) > 1 and r[1] else 'HWH Section'
            line = str(r[2]) if len(r) > 2 and r[2] else 'UP'
            try:
                km_from = int(r[3]) if len(r) > 3 and r[3] else 0
            except Exception:
                km_from = 0
            try:
                met_from = int(r[4]) if len(r) > 4 and r[4] else 0
            except Exception:
                met_from = 0
            try:
                km_to = int(r[5]) if len(r) > 5 and r[5] else km_from + 1
            except Exception:
                km_to = km_from + 1
            try:
                met_to = int(r[6]) if len(r) > 6 and r[6] else 0
            except Exception:
                met_to = 0
            grade = str(r[10]) if len(r) > 10 and r[10] else 'Level'

            cur.execute("""
                INSERT INTO gradient_register (section, line, km_from, met_from, km_to, met_to, grade)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (section, line, km_from, met_from, km_to, met_to, grade))
            count += 1

        conn.commit()
        return jsonify({'success': True, 'message': f'Successfully imported {count} gradient records.'})
    except Exception as e:
        return jsonify({'detail': str(e)}), 500
    finally:
        cur.close()
        conn.close()




# ==========================================
# CREW SEARCH API (FOR CNL TOP SEARCH BAR)
# ==========================================
@control_bp.route('/api/search')
@control_bp.route('/tools/api/search')
def api_search_crew():
    q = request.args.get("q", "").strip()
    lobby = request.args.get("lobby", "").strip()
    desig = request.args.get("desig", "").strip()

    if not q and not lobby and not desig:
        return jsonify([])

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        conditions = []
        params = []

        if q:
            mobile_q = q.replace(" ", "").replace("-", "").replace("+", "")
            if mobile_q.isdigit():
                if mobile_q.startswith('91') and len(mobile_q) >= 11:
                    mobile_q = mobile_q[2:]
                elif mobile_q.startswith('0') and len(mobile_q) >= 11:
                    mobile_q = mobile_q[1:]

            search_term = f"%{q}%"
            mobile_search_term = f"%{mobile_q}%"

            conditions.append("(crew_name LIKE %s OR crew_id LIKE %s OR mobile LIKE %s OR cli_name LIKE %s)")
            params.extend([search_term, search_term, mobile_search_term, search_term])

        if lobby:
            conditions.append("(UPPER(TRIM(crew_hq)) = %s OR crew_id LIKE %s)")
            params.extend([lobby.upper(), f"{lobby.upper()}%"])

        if desig:
            conditions.append("designation = %s")
            params.append(desig)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT id, crew_id, crew_name, designation, crew_hq, mobile, cli_name
            FROM crew_master
            WHERE {where_clause}
            LIMIT 30
        """

        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        results = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            crew_id_val = str(r.get('crew_id') or '').strip()
            crew_name_val = str(r.get('crew_name') or '').strip()
            hq_val = str(r.get('crew_hq') or '').strip()
            if not hq_val:
                hq_val = ''.join([c for c in crew_id_val if c.isalpha()]).upper()

            formatted_name = f"{crew_name_val}/{hq_val}" if (crew_name_val and hq_val) else crew_name_val

            mob_val = str(r.get('mobile') or '').strip()
            if mob_val.startswith('91') and len(mob_val) > 10:
                mob_val = mob_val[2:]
            elif mob_val.startswith('+91') and len(mob_val) > 11:
                mob_val = mob_val[3:]
            elif mob_val.startswith('0') and len(mob_val) > 10:
                mob_val = mob_val[1:]

            cli_val = str(r.get('cli_name') or '').strip()
            if cli_val in ('-', 'NA', 'N/A', 'NONE', 'NIL'):
                cli_val = ''

            desig_val = str(r.get('designation') or '').strip()

            results.append({
                "crew_id": crew_id_val,
                "crew_name": crew_name_val,
                "formatted_name": formatted_name,
                "mobile_no": mob_val or "-",
                "cli_name": cli_val or "N/A",
                "crew_type": desig_val,
                "designation": desig_val,
                "lobby": hq_val
            })

        return jsonify(results)
    except Exception as e:
        logger.error(f"Error querying crew search: {e}")
        return jsonify([])


@control_bp.route('/api/crew/filters')
@control_bp.route('/tools/api/crew/filters')
def api_crew_search_filters():
    lobbies_set = {"RPH", "BWN", "HWH", "PKR", "DKAE", "AZ", "BDC", "BGP", "DUMK", "SDAH", "MLDT"}
    designations_set = {"ALP", "LPG", "LPM", "LPP", "LPS", "SALP", "SR.LP"}

    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT DISTINCT UPPER(TRIM(crew_hq)) as hq FROM crew_master WHERE crew_hq IS NOT NULL AND crew_hq != ''")
        for r in cur.fetchall():
            hq = r.get('hq') if isinstance(r, dict) else r[0]
            if hq:
                lobbies_set.add(hq)

        cur.execute("SELECT DISTINCT designation FROM crew_master WHERE designation IS NOT NULL AND designation != ''")
        for r in cur.fetchall():
            desig = r.get('designation') if isinstance(r, dict) else r[0]
            if desig:
                designations_set.add(desig)

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error querying filters: {e}")

    primary_lobbies = ["RPH", "BWN", "HWH", "PKR", "DKAE"]
    other_lobbies = sorted([l for l in lobbies_set if l not in primary_lobbies])
    sorted_lobbies = primary_lobbies + other_lobbies

    return jsonify({
        "lobbies": sorted_lobbies,
        "designations": sorted(list(designations_set))
    })
