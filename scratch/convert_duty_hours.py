import re
import os

src_path = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\hwh-division-operation-dashboard\app\routers\duty_hours.py"
dst_path = r"blueprints/duty_hours.py"

with open(src_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Header imports & helpers
header_old_regex = re.compile(r'^.*?def init_db_tables\(\):', re.DOTALL)

new_header = '''import os
import re
import uuid
import shutil
import html as html_escapers
from datetime import date, datetime, time, timedelta
import openpyxl
import json
import logging
from flask import Blueprint, request, jsonify, send_file, render_template
from blueprints.control_db import get_connection

logger = logging.getLogger(__name__)

duty_hours_bp = Blueprint("duty_hours", __name__, url_prefix="/api/duty-hours")

# Setup temp directory inside workspace
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(BASE_DIR, "temp_duty_hours")
os.makedirs(TEMP_DIR, exist_ok=True)

class HTTPException(Exception):
    def __init__(self, status_code=400, detail=""):
        super().__init__(detail)
        self.status_code = int(status_code)
        self.detail = str(detail)

@duty_hours_bp.errorhandler(HTTPException)
def handle_http_exception(e):
    return jsonify({"detail": e.detail}), e.status_code

def FileResponse(path, filename=None, media_type=None):
    return send_file(
        path,
        as_attachment=True,
        download_name=filename or os.path.basename(path),
        mimetype=media_type or "application/octet-stream"
    )

def excel_json_default(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, timedelta):
        return str(value)
    return str(value)

def init_db_tables():'''

code = header_old_regex.sub(new_header, code, count=1)

# Ensure init_db_tables creates tbl_long_hours_master, sections, upload_log
tables_addition = '''
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_long_hours_master (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_batch_id VARCHAR(50) NOT NULL,
            source_file_name VARCHAR(255) NOT NULL,
            record_hash VARCHAR(64) UNIQUE NOT NULL,
            sign_on_date DATE,
            sign_on_time VARCHAR(20),
            sign_off_date DATE,
            sign_off_time VARCHAR(20),
            lp_name VARCHAR(255),
            alp_name VARCHAR(255),
            crew_id VARCHAR(50),
            train_no VARCHAR(50),
            loco_no VARCHAR(50),
            long_hours_section VARCHAR(100),
            on_stn VARCHAR(50),
            cto_stn VARCHAR(50),
            dep_stn VARCHAR(50),
            arr_stn VARCHAR(50),
            cmo_stn VARCHAR(50),
            off_stn VARCHAR(50),
            hwh_div_seconds INT DEFAULT 0,
            oth_div_seconds INT DEFAULT 0,
            total_seconds INT DEFAULT 0,
            pdd_seconds INT DEFAULT 0,
            pad_seconds INT DEFAULT 0,
            wheel_movement_seconds INT DEFAULT 0,
            sign_on_to_dep_seconds INT DEFAULT 0,
            wheel_stop_to_off_seconds INT DEFAULT 0,
            detn_ic_point VARCHAR(255),
            remarks TEXT,
            scenario_type INT,
            row_data_json LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_sign_off_date (sign_off_date),
            INDEX idx_long_hours_section (long_hours_section),
            INDEX idx_scenario_type (scenario_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_long_hours_sections (
            section_name VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_long_hours_upload_log (
            upload_batch_id VARCHAR(50) PRIMARY KEY,
            original_file_name VARCHAR(255) NOT NULL,
            uploaded_by VARCHAR(100) NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_rows INT DEFAULT 0,
            inserted_rows INT DEFAULT 0,
            updated_rows INT DEFAULT 0,
            failed_rows INT DEFAULT 0,
            remarks TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        conn.commit()'''

code = code.replace(
    '        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n        """)\n        conn.commit()',
    '        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;\n        """)\n' + tables_addition,
    1
)

# Route 1: duty-hours-count template
route_tool_old = '''@router.get("/tools/duty-hours-count")
def duty_hours_count(request: Request):
    return templates.TemplateResponse(
        "duty_hours_count.html",
        {"request": request, "active_page": "duty-hours-count"}
    )'''

# Note: In the original file it might have had different indentation or parameters
# Let's use regex for duty_hours_count
code = re.sub(
    r'@router\.get\("/tools/duty-hours-count"\)\s*def duty_hours_count\([^)]*\):.*?return templates\.TemplateResponse\([^)]+\)',
    '''@duty_hours_bp.route("/tools/duty-hours-count", methods=["GET"])
def duty_hours_count():
    return render_template("control/tools/duty_hours_count.html")''',
    code,
    flags=re.DOTALL
)

# Route 2: Upload route
upload_old_pattern = r'@router\.post\("/api/duty-hours/upload"\)\s*def upload_duty_hours\(.*?\):'
upload_new_header = '''@duty_hours_bp.route("/upload", methods=["POST"])
def upload_duty_hours():
    if "file" not in request.files:
        raise HTTPException(status_code=400, detail="Please select a valid Excel file.")
    file = request.files["file"]
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Please select a valid Excel file.")'''

code = re.sub(upload_old_pattern, upload_new_header, code)

# In upload, replace file saving:
code = code.replace(
    '''        # Save file to temp path
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)''',
    '''        # Save file to temp path
        file.save(temp_path)'''
)

# Wrap long hours sync in upload
long_hours_sync_old = '''            # Sync with Long Hours master
            cursor.execute("""
                UPDATE tbl_long_hours_master l
                JOIN tbl_duty_hours_master d 
                  ON l.crew_id = d.crew_id AND l.sign_on_date = d.sign_on_date
                SET l.total_seconds = 
                    CAST(SUBSTRING_INDEX(d.total_duty, ':', 1) AS UNSIGNED) * 3600 + 
                    CAST(SUBSTRING_INDEX(d.total_duty, ':', -1) AS UNSIGNED) * 60
                WHERE d.total_duty REGEXP '^[0-9]+:[0-9]+$'
                  AND d.upload_batch_id = %s
            """, (temp_filename,))
            conn.commit()'''

long_hours_sync_new = '''            # Sync with Long Hours master (non-blocking)
            try:
                cursor.execute("""
                    UPDATE tbl_long_hours_master l
                    JOIN tbl_duty_hours_master d 
                      ON l.crew_id = d.crew_id AND l.sign_on_date = d.sign_on_date
                    SET l.total_seconds = 
                        CAST(SUBSTRING_INDEX(d.total_duty, ':', 1) AS UNSIGNED) * 3600 + 
                        CAST(SUBSTRING_INDEX(d.total_duty, ':', -1) AS UNSIGNED) * 60
                    WHERE d.total_duty REGEXP '^[0-9]+:[0-9]+$'
                      AND d.upload_batch_id = %s
                """, (temp_filename,))
            except Exception as sync_err:
                logger.warning(f"Long hours sync non-fatal: {sync_err}")
            conn.commit()'''

code = code.replace(long_hours_sync_old, long_hours_sync_new)

# Route 3: Filter route
filter_old_pattern = r'@router\.post\("/api/duty-hours/filter"\)\s*def filter_duty_hours\(payload:\s*dict\):'
filter_new_header = '''@duty_hours_bp.route("/filter", methods=["POST"])
def filter_duty_hours():
    payload = request.get_json(silent=True) or {}'''

code = re.sub(filter_old_pattern, filter_new_header, code)

# Route 4: Download route
download_old_pattern = r'@router\.get\("/api/duty-hours/download/\{download_id\}"\)\s*def download_duty_hours\([^)]*\):'
download_new_header = '''@duty_hours_bp.route("/download/<download_id>", methods=["GET"])
def download_duty_hours(download_id):
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    selected_date = request.args.get("selected_date")
    duty_slab = request.args.get("duty_slab", "all")'''

code = re.sub(download_old_pattern, download_new_header, code)

# Route 5: Download route summary
route_sum_old_pattern = r'@router\.get\("/api/duty-hours/download-route-summary"\)\s*def download_route_summary\([^)]*\):'
route_sum_new_header = '''@duty_hours_bp.route("/download-route-summary", methods=["GET"])
def download_route_summary():
    file_id = request.args.get("file_id")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    duty_slab = request.args.get("duty_slab", "all")'''

code = re.sub(route_sum_old_pattern, route_sum_new_header, code)

# Route 6: Download dates summary
dates_sum_old_pattern = r'@router\.get\("/api/duty-hours/download-dates-summary"\)\s*def download_dates_summary\([^)]*\):'
dates_sum_new_header = '''@duty_hours_bp.route("/download-dates-summary", methods=["GET"])
def download_dates_summary():
    file_id = request.args.get("file_id")'''

code = re.sub(dates_sum_old_pattern, dates_sum_new_header, code)

with open(dst_path, "w", encoding="utf-8") as f:
    f.write(code)

print("Clean conversion complete!")
