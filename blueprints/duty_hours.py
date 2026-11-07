import os
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

def _unpack_file_meta(meta):
    if isinstance(meta, dict):
        return meta.get("header_row"), meta.get("sl_col"), meta.get("sign_off_col"), meta.get("headers_json")
    return meta

def _unpack_db_row(row):
    if isinstance(row, dict):
        return row.get("row_index"), row.get("sl_no"), row.get("sign_off_date"), row.get("row_data_json")
    return row

def init_db_tables():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS duty_hours_files (
            id VARCHAR(50) PRIMARY KEY,
            filename VARCHAR(255),
            upload_time DATETIME,
            headers_json LONGTEXT,
            header_row INT,
            sl_col INT,
            sign_off_col INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS duty_hours_rows (
            id INT AUTO_INCREMENT PRIMARY KEY,
            file_id VARCHAR(50),
            row_index INT,
            sl_no VARCHAR(50),
            sign_off_date VARCHAR(20),
            row_data_json LONGTEXT,
            INDEX idx_file_date (file_id, sign_off_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tbl_duty_hours_master (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_batch_id VARCHAR(50),
            record_hash VARCHAR(64) UNIQUE,
            crew_id VARCHAR(50),
            crew_name VARCHAR(255),
            designation VARCHAR(100),
            total_duty VARCHAR(50),
            sign_on_date DATE,
            sign_on_time TIME,
            sign_on_stn VARCHAR(50),
            departure TIME,
            pdd VARCHAR(50),
            arrival TIME,
            sign_off_date DATE,
            sign_off_time TIME,
            sign_off_stn VARCHAR(50),
            duty_hrs VARCHAR(50),
            duty_type VARCHAR(50),
            train_no VARCHAR(50),
            loco_no VARCHAR(50),
            wheel_movement VARCHAR(50),
            avg_speed DOUBLE,
            route_km DOUBLE,
            total_km DOUBLE,
            mk VARCHAR(50),
            cto VARCHAR(100),
            cmo VARCHAR(100),
            section VARCHAR(255),
            route_name VARCHAR(255),
            row_data_json LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_crew_date (crew_id, sign_on_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

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
        conn.commit()
    except Exception as e:
        print(f"Error initializing duty hours database tables: {e}")
    finally:
        cursor.close()
        conn.close()

init_db_tables()

# Clean up files older than 1 hour periodically on requests
def cleanup_temp_files():
    try:
        now = datetime.now()
        for filename in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                # 1 hour = 3600 seconds
                if (now - datetime.fromtimestamp(stat.st_mtime)).total_seconds() > 3600:
                    os.remove(file_path)
    except Exception as e:
        print(f"Cleanup error: {e}")

# Helper: Extract date portion as DD-MM-YYYY
def extract_date_portion(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    
    text = str(value).strip()
    if not text:
        return None
    
    # Check DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})", text)
    if m:
        d, m_val, y = m.groups()
        if len(y) == 2:
            y = "20" + y
        return f"{int(d):02d}-{int(m_val):02d}-{y}"
    
    # Check YYYY-MM-DD
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if m:
        y, m_val, d = m.groups()
        return f"{int(d):02d}-{int(m_val):02d}-{y}"
    
    # Strptime try
    for fmt in ("%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(text, fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            pass
            
    return None

import hashlib

def get_row_value(row_values, mapping, keys_list, default=None):
    for key in keys_list:
        clean_key = key.lower().replace(" ", "").replace("_", "").replace("-", "").replace(".", "")
        if clean_key in mapping:
            col_idx = mapping[clean_key]
            if col_idx < len(row_values):
                return row_values[col_idx]
    return default

def parse_date_yyyy_mm_dd(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    val_str = str(val).strip()
    if not val_str or val_str == "-" or val_str == "None":
        return None
    if " " in val_str:
        val_str = val_str.split(" ")[0]
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def parse_time_hh_mm_ss(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val.strftime("%H:%M:%S")
    if isinstance(val, time):
        return val.strftime("%H:%M:%S")
    val_str = str(val).strip()
    if not val_str or val_str == "-" or val_str == "None":
        return None
    if " " in val_str:
        parts = val_str.split(" ")
        if len(parts) > 1:
            val_str = parts[1]
    parts = val_str.split(":")
    if len(parts) >= 2:
        try:
            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            return f"{h:02d}:{m:02d}:{s:02d}"
        except ValueError:
            return None
    return None

def clean_float(val):
    if val is None or str(val).strip() in ("", "-", "None"):
        return 0.0
    try:
        return float(str(val).replace(",", "").strip())
    except ValueError:
        return 0.0

# Helper: Parse duty hours into float decimal hours
def parse_duty_hours_to_float(val):
    if val is None:
        return 0.0
    if isinstance(val, timedelta):
        return val.total_seconds() / 3600.0
    if isinstance(val, time):
        return float(val.hour) + float(val.minute) / 60.0 + float(val.second) / 3600.0
    if isinstance(val, (int, float)):
        return float(val * 24.0)
    text = str(val).strip()
    m = re.match(r'^(\d+):(\d+)(?::(\d+))?$', text)
    if m:
        h, mins = m.group(1), m.group(2)
        return float(h) + float(mins) / 60.0
    try:
        return float(text)
    except ValueError:
        return 0.0

# Helper: Format float decimal hours to HH:MM format
def format_float_hours_to_hhmm(hours_float):
    if hours_float is None or hours_float < 0:
        return "00:00"
    total_minutes = int(round(hours_float * 60.0))
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"

# Helper: Detect header row and S.L. No. and Sign Off Date columns
def detect_header_and_columns(sheet):
    # Scan first 20 rows using iter_rows for compatibility with read_only mode
    for r_idx, row in enumerate(sheet.iter_rows(max_row=20, values_only=True), start=1):
        for c_idx, cell_val in enumerate(row, start=1):
            val = str(cell_val or "").strip().lower()
            val_clean = val.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
            if any(x in val_clean for x in ["sno", "slno", "serial"]):
                # S.L. No column found
                sign_off_col = 11  # Default to K (11th column)
                total_duty_col = 5  # Default to E (5th column)
                
                found_signoff = False
                found_totalduty = False
                
                for c2_idx, cell_val2 in enumerate(row, start=1):
                    val2 = str(cell_val2 or "").strip().lower()
                    val2_clean = val2.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
                    if "signoff" in val2_clean and not any(x in val2_clean for x in ["sttn", "stn", "station"]):
                        if not found_signoff:
                            sign_off_col = c2_idx
                            found_signoff = True
                    elif "totalduty" in val2_clean:
                        total_duty_col = c2_idx
                        found_totalduty = True
                        
                # Fallback to dutyhrs if totalduty was not found in the row
                if not found_totalduty:
                    for c2_idx, cell_val2 in enumerate(row, start=1):
                        val2 = str(cell_val2 or "").strip().lower()
                        val2_clean = val2.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
                        if "dutyhrs" in val2_clean or "workinghours" in val2_clean:
                            total_duty_col = c2_idx
                            break
                            
                return r_idx, c_idx, sign_off_col, total_duty_col
    raise ValueError("Could not find the header row containing S.L. No.")

# Helper: Check if row is a footer or summary row
def is_footer_row(sheet, r, max_col):
    for c in range(1, max_col + 1):
        val = str(sheet.cell(row=r, column=c).value or "").strip().lower()
        if any(x in val for x in ["total", "grand total", "summary", "count"]):
            return True
    return False

# Helper: Detect consecutive duty groups
def detect_duty_groups(sheet, header_row, sl_col, sign_off_col):
    groups = []
    current_group = []
    current_sl = None
    
    # Pre-load all rows as values to run 1000x faster
    rows = list(sheet.iter_rows(values_only=True))
    max_row = len(rows)
    
    for r_idx in range(header_row + 1, max_row + 1):
        row_tuple = rows[r_idx - 1]
        
        # Check if empty row
        is_empty = True
        for val in row_tuple:
            if val is not None:
                is_empty = False
                break
        if is_empty:
            continue
            
        # Check if footer row
        is_footer = False
        for val in row_tuple:
            if isinstance(val, str) and any(x in val.lower() for x in ["total", "group", "row"]):
                is_footer = True
                break
        if is_footer:
            continue
            
        cell_val = row_tuple[sl_col - 1] if len(row_tuple) >= sl_col else None
        clean_val = str(cell_val).strip() if cell_val is not None else ""
        
        if clean_val != "":
            if current_group and clean_val == current_sl:
                current_group.append(r_idx)
            else:
                if current_group:
                    groups.append(current_group)
                current_group = [r_idx]
                current_sl = clean_val
        else:
            if current_group:
                current_group.append(r_idx)
            else:
                current_group = [r_idx]
                current_sl = ""
                
    if current_group:
        groups.append(current_group)
        
    # Find Sign Off Date for each group
    duty_groups = []
    for g in groups:
        group_date = None
        for r_idx in g:
            row_tuple = rows[r_idx - 1]
            val = row_tuple[sign_off_col - 1] if len(row_tuple) >= sign_off_col else None
            dt = extract_date_portion(val)
            if dt:
                group_date = dt
                break
        duty_groups.append({
            "rows": g,
            "sign_off_date": group_date
        })
        
    return duty_groups

# Helper: Update text in spreadsheet indicating totals
def update_total_labels_in_sheet(sheet, total_duties, total_rows):
    for r in range(1, (sheet.max_row or 0) + 1):
        for c in range(1, (sheet.max_column or 20) + 1):
            val = sheet.cell(row=r, column=c).value
            if isinstance(val, str):
                # Update Total Duties/Groups
                val_updated = re.sub(
                    r"(total\s+(duty\s+groups|duties|groups))\s*:\s*\d+",
                    f"\\1 : {total_duties}",
                    val,
                    flags=re.IGNORECASE
                )
                # Update Total Rows
                val_updated = re.sub(
                    r"(total\s+rows)\s*:\s*\d+",
                    f"\\1 : {total_rows}",
                    val_updated,
                    flags=re.IGNORECASE
                )
                if val_updated != val:
                    sheet.cell(row=r, column=c).value = val_updated

# Helper: Update the main heading in sheet to include the selected date
def update_heading_in_sheet(sheet, selected_date):
    for r in range(1, 6):
        for c in range(1, (sheet.max_column or 20) + 1):
            val = sheet.cell(row=r, column=c).value
            if isinstance(val, str) and ("report" in val.lower() or "working hours" in val.lower()):
                date_match = re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", val)
                if date_match:
                    new_val = val[:date_match.start()] + selected_date + val[date_match.end():]
                    sheet.cell(row=r, column=c).value = new_val
                else:
                    clean_val = val.rstrip()
                    if clean_val.lower().endswith("for"):
                        sheet.cell(row=r, column=c).value = f"{clean_val} {selected_date}"
                    elif clean_val.lower().endswith("date") or clean_val.lower().endswith("date:"):
                        sheet.cell(row=r, column=c).value = f"{clean_val} {selected_date}"
                    else:
                        sheet.cell(row=r, column=c).value = f"{clean_val} FOR {selected_date}"
                return

# Helper: Generate HTML table preview with styles
# Helper: Generate HTML table preview with styles on the fly (no sheet modifications needed)
def generate_html_table(sheet, rows_to_keep, sl_col, filtered_groups, total_groups, total_rows_count, selected_date, header_row):
    merged_ranges = list(sheet.merged_cells.ranges)
    html = ['<table class="excel-preview-table table-bordered">']
    
    # Pre-load all cells as objects in memory to run 1000x faster
    cells = list(sheet.iter_rows(values_only=False))
    if not cells:
        html.append('</table>')
        return "\n".join(html)
        
    max_row = len(cells)
    max_col = max(len(row) for row in cells) if cells else 0
    
    # Map row index to new serial number
    row_to_serial = {}
    for idx, g in enumerate(filtered_groups, start=1):
        for r in g["rows"]:
            row_to_serial[r] = idx
            
    # colgroup
    html.append('<colgroup>')
    for col_idx in range(1, max_col + 1):
        col_letter = openpyxl.utils.get_column_letter(col_idx)
        col_dim = sheet.column_dimensions.get(col_letter)
        col_width = col_dim.width if (col_dim and col_dim.width) else 10
        width_px = int(col_width * 8)
        html.append(f'<col style="width: {width_px}px;">')
    html.append('</colgroup>')
    
    skipped_cells = set()
    
    for r in range(1, max_row + 1):
        if r not in rows_to_keep:
            continue
            
        row_cells = cells[r - 1]
        row_dim = sheet.row_dimensions.get(r)
        row_height = row_dim.height if (row_dim and row_dim.height) else 15
        height_px = int(row_height * 1.33)
        
        html.append(f'<tr style="height: {height_px}px;">')
        
        for c in range(1, max_col + 1):
            if (r, c) in skipped_cells:
                continue
                
            cell = row_cells[c - 1] if c <= len(row_cells) else None
            if cell is None:
                html.append('<td></td>')
                continue
                
            is_merged = False
            rowspan = 1
            colspan = 1
            
            for rg in merged_ranges:
                if rg.min_row <= r <= rg.max_row and rg.min_col <= c <= rg.max_col:
                    is_merged = True
                    if r == rg.min_row and c == rg.min_col:
                        # Count how many of the merged rows are actually kept
                        kept_merged_rows = [mr for mr in range(rg.min_row, rg.max_row + 1) if mr in rows_to_keep]
                        rowspan = len(kept_merged_rows)
                        colspan = rg.max_col - rg.min_col + 1
                        for r_skip in range(rg.min_row, rg.max_row + 1):
                            for c_skip in range(rg.min_col, rg.max_col + 1):
                                if (r_skip, c_skip) != (r, c):
                                    skipped_cells.add((r_skip, c_skip))
                    else:
                        colspan = 0
                        rowspan = 0
                    break
                    
            if is_merged and (colspan == 0 or rowspan == 0):
                continue
                
            styles = []
            
            # BG Color
            if cell.fill and cell.fill.fill_type == 'solid':
                color = cell.fill.start_color
                if color and color.rgb and str(color.rgb) != '00000000':
                    rgb = str(color.rgb)
                    hex_color = rgb[2:] if len(rgb) == 8 else rgb
                    styles.append(f"background-color: #{hex_color}")
                    
            # Font
            if cell.font:
                if cell.font.name:
                    styles.append(f"font-family: '{cell.font.name}'")
                if cell.font.size:
                    styles.append(f"font-size: {cell.font.size}pt")
                if cell.font.bold:
                    styles.append("font-weight: bold")
                if cell.font.italic:
                    styles.append("font-style: italic")
                if cell.font.color and cell.font.color.rgb and str(cell.font.color.rgb) != '00000000':
                    rgb = str(cell.font.color.rgb)
                    hex_color = rgb[2:] if len(rgb) == 8 else rgb
                    styles.append(f"color: #{hex_color}")
                    
            # Alignment
            if cell.alignment:
                if cell.alignment.horizontal:
                    styles.append(f"text-align: {cell.alignment.horizontal}")
                if cell.alignment.vertical:
                    valign = cell.alignment.vertical
                    if valign == 'center':
                        valign = 'middle'
                    styles.append(f"vertical-align: {valign}")
                if cell.alignment.wrap_text:
                    styles.append("white-space: normal")
                else:
                    styles.append("white-space: nowrap")
            else:
                styles.append("white-space: nowrap")
                
            # Borders
            border_map = {
                'thin': '1px solid',
                'medium': '2px solid',
                'thick': '3px solid',
                'double': '3px double',
                'dashed': '1px dashed',
                'dotted': '1px dotted',
            }
            for side in ['left', 'right', 'top', 'bottom']:
                border_side = getattr(cell.border, side, None)
                if border_side and border_side.style:
                    b_style = border_map.get(border_side.style, '1px solid')
                    b_color = '#cbd5e1'
                    if border_side.color and border_side.color.rgb and str(border_side.color.rgb) != '00000000':
                        rgb = str(border_side.color.rgb)
                        b_color = f"#{rgb[2:]}" if len(rgb) == 8 else f"#{rgb}"
                    styles.append(f"border-{side}: {b_style} {b_color}")
                else:
                    styles.append(f"border-{side}: 1px solid #e2e8f0")
                    
            style_str = "; ".join(styles) + ";" if styles else ""
            
            # Value replacement on the fly
            val = cell.value
            if r in row_to_serial and c == sl_col:
                val = row_to_serial[r]
            elif isinstance(val, str):
                # Update totals on the fly
                val = re.sub(
                    r"(total\s+(duty\s+groups|duties|groups))\s*:\s*\d+",
                    f"\\1 : {total_groups}",
                    val,
                    flags=re.IGNORECASE
                )
                val = re.sub(
                    r"(total\s+rows)\s*:\s*\d+",
                    f"\\1 : {total_rows_count}",
                    val,
                    flags=re.IGNORECASE
                )
                # Update title/heading on the fly
                if r <= 5 and ("report" in val.lower() or "working hours" in val.lower()):
                    date_match = re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", val)
                    if date_match:
                        val = val[:date_match.start()] + selected_date + val[date_match.end():]
                    else:
                        clean_val = val.rstrip()
                        if clean_val.lower().endswith("for"):
                            val = f"{clean_val} {selected_date}"
                        elif clean_val.lower().endswith("date") or clean_val.lower().endswith("date:"):
                            val = f"{clean_val} {selected_date}"
                        else:
                            val = f"{clean_val} FOR {selected_date}"
            
            val_str = ""
            if val is not None:
                if isinstance(val, datetime):
                    val_str = val.strftime("%d-%m-%Y %H:%M")
                else:
                    val_str = str(val)
                    
            val_escaped = html_escapers.escape(val_str)
            
            attrs = []
            if rowspan > 1:
                attrs.append(f'rowspan="{rowspan}"')
            if colspan > 1:
                attrs.append(f'colspan="{colspan}"')
            attrs_str = " " + " ".join(attrs) if attrs else ""
            
            html.append(f'<td style="{style_str}"{attrs_str}>{val_escaped}</td>')
            
        html.append('</tr>')
        
    html.append('</table>')
    return "\n".join(html)

# ROUTES
@duty_hours_bp.route("/tools/duty-hours-count", methods=["GET"])
def duty_hours_count():
    return render_template("control/tools/duty_hours_count.html")

@duty_hours_bp.route("/upload", methods=["POST"])
def upload_duty_hours():
    if "file" not in request.files:
        raise HTTPException(status_code=400, detail="Please select a valid Excel file.")
    file = request.files["file"]
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Please select a valid Excel file.")
    cleanup_temp_files()
    
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload a valid Excel file (.xlsx or .xls).")
        
    file_uuid = str(uuid.uuid4())
    temp_filename = f"uploaded_{file_uuid}.xlsx"
    temp_path = os.path.join(TEMP_DIR, temp_filename)
    
    try:
        # Save file to temp path
        file.save(temp_path)
            
        # Check and delete the metadata row (row 2) if it contains report details
        try:
            wb_check = openpyxl.load_workbook(temp_path, data_only=True)
            sheet_check = wb_check.active
            val_row2 = sheet_check.cell(row=2, column=1).value
            wb_check.close()
            
            if isinstance(val_row2, str) and ("report" in val_row2.lower() or "working hours" in val_row2.lower() or "lobby" in val_row2.lower()):
                wb_edit = openpyxl.load_workbook(temp_path, data_only=False)
                sheet_edit = wb_edit.active
                
                # Unmerge any merged ranges intersecting with row 2 to prevent shifting ranges from merging the headers
                merged_ranges = list(sheet_edit.merged_cells.ranges)
                for r in merged_ranges:
                    if r.min_row <= 2 <= r.max_row:
                        sheet_edit.unmerge_cells(str(r))
                        
                sheet_edit.delete_rows(2, 1)
                wb_edit.save(temp_path)
                wb_edit.close()
        except Exception as e:
            # Non-blocking, continue if edit fails
            print(f"Metadata row deletion failed: {e}")
            
        # Parse dates using openpyxl in read_only mode for high performance
        wb = openpyxl.load_workbook(temp_path, read_only=True, data_only=True)
        sheet = wb.active
        
        try:
            header_row, sl_col, sign_off_col, total_duty_col = detect_header_and_columns(sheet)
        except ValueError as e:
            wb.close()
            os.remove(temp_path)
            print(f"UPLOAD VALIDATION ERROR: {e}")
            raise HTTPException(status_code=400, detail=str(e))
            
        # Group duties and read row values while workbook is open
        duty_groups = detect_duty_groups(sheet, header_row, sl_col, sign_off_col)
        all_rows = list(sheet.iter_rows(values_only=True))
        wb.close()
        
        # Connect to database and truncate tables first as requested by the user
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("DELETE FROM duty_hours_rows")
            cursor.execute("DELETE FROM duty_hours_files")
            conn.commit()
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"Database truncation error: {str(e)}")
            
        try:
            # Extract headers list
            headers = list(all_rows[header_row - 1]) if header_row <= len(all_rows) else []
            
            # Insert file metadata
            cursor.execute(
                "INSERT INTO duty_hours_files (id, filename, upload_time, headers_json, header_row, sl_col, sign_off_col) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (temp_filename, file.filename, datetime.now(), json.dumps(headers, default=excel_json_default), header_row, sl_col, sign_off_col)
            )
            
            # Map row index to its sign_off_date
            row_to_date = {}
            for g in duty_groups:
                for r in g["rows"]:
                    row_to_date[r] = g["sign_off_date"]
                    
            row_inserts = []
            unique_dates = set()
            
            for r_idx, row_values in enumerate(all_rows, start=1):
                date_val = None
                if r_idx <= header_row:
                    date_val = "HEADER"
                else:
                    # Check if it is a footer row
                    is_footer = False
                    for val in row_values:
                        if isinstance(val, str) and any(x in val.lower() for x in ["total", "group", "row"]):
                            is_footer = True
                            break
                            
                    if is_footer:
                        date_val = "FOOTER"
                    elif r_idx in row_to_date:
                        date_val = row_to_date[r_idx]
                        if date_val:
                            unique_dates.add(date_val)
                            
                row_inserts.append((
                    temp_filename,
                    r_idx,
                    str(row_values[sl_col - 1]).strip() if (sl_col <= len(row_values) and row_values[sl_col - 1] is not None) else "",
                    date_val,
                    json.dumps(list(row_values), default=excel_json_default)
                ))
                
            # Batch insert rows in chunks of 1000
            chunk_size = 1000
            for i in range(0, len(row_inserts), chunk_size):
                chunk = row_inserts[i:i + chunk_size]
                cursor.executemany(
                    "INSERT INTO duty_hours_rows (file_id, row_index, sl_no, sign_off_date, row_data_json) VALUES (%s, %s, %s, %s, %s)",
                    chunk
                )
            # Create clean headers mapping
            mapping = {}
            for col_idx, h in enumerate(headers):
                ch = str(h or "").lower().replace("\n", "").replace(" ", "").replace("_", "").replace("-", "").replace(".", "")
                mapping[ch] = col_idx

            master_inserts = []
            for r_idx, row_values in enumerate(all_rows, start=1):
                if r_idx <= header_row:
                    continue
                is_empty = True
                for val in row_values:
                    if val is not None:
                        is_empty = False
                        break
                if is_empty:
                    continue
                    
                is_footer = False
                for val in row_values:
                    if isinstance(val, str) and any(x in val.lower() for x in ["total", "group", "row"]):
                        is_footer = True
                        break
                if is_footer:
                    continue
                    
                crew_id = get_row_value(row_values, mapping, ['crewid', 'crewcode'])
                if not crew_id:
                    continue
                    
                crew_name = get_row_value(row_values, mapping, ['crewname', 'name'])
                designation = get_row_value(row_values, mapping, ['desig', 'designation'])
                total_duty = get_row_value(row_values, mapping, ['totalduty'])
                sign_on_date_raw = get_row_value(row_values, mapping, ['signondate'])
                sign_on_stn = get_row_value(row_values, mapping, ['signonsttn', 'signonstn'])
                departure_raw = get_row_value(row_values, mapping, ['departure'])
                pdd = get_row_value(row_values, mapping, ['pdd'])
                arrival_raw = get_row_value(row_values, mapping, ['arrival'])
                sign_off_date_raw = get_row_value(row_values, mapping, ['signoffdate'])
                sign_off_stn = get_row_value(row_values, mapping, ['signoffsttn', 'signoffstn'])
                duty_hrs = get_row_value(row_values, mapping, ['dutyhrs'])
                duty_type = get_row_value(row_values, mapping, ['dutytype'])
                train_no = get_row_value(row_values, mapping, ['trainno'])
                loco_no = get_row_value(row_values, mapping, ['locono', 'loco'])
                wheel_movement = get_row_value(row_values, mapping, ['wheelmovement'])
                avg_speed_raw = get_row_value(row_values, mapping, ['avgspeedkmhrs', 'avgspeed'])
                route_km_raw = get_row_value(row_values, mapping, ['routekm'])
                total_km_raw = get_row_value(row_values, mapping, ['totalkm'])
                mk = get_row_value(row_values, mapping, ['mk'])
                cto = get_row_value(row_values, mapping, ['cto'])
                cmo = get_row_value(row_values, mapping, ['cmo'])
                section = get_row_value(row_values, mapping, ['section'])
                route_name = get_row_value(row_values, mapping, ['routename'])
                
                s_date = parse_date_yyyy_mm_dd(sign_on_date_raw)
                s_time = parse_time_hh_mm_ss(sign_on_date_raw)
                dep_time = parse_time_hh_mm_ss(departure_raw)
                arr_time = parse_time_hh_mm_ss(arrival_raw)
                so_date = parse_date_yyyy_mm_dd(sign_off_date_raw)
                so_time = parse_time_hh_mm_ss(sign_off_date_raw)
                
                # Generate hash
                unique_str = f"{crew_id}_{s_date}_{s_time}_{train_no}_{loco_no}"
                record_hash = hashlib.sha256(unique_str.encode("utf-8")).hexdigest()
                
                master_inserts.append((
                    temp_filename, record_hash, crew_id, crew_name, designation, total_duty,
                    s_date, s_time, sign_on_stn, dep_time, pdd, arr_time,
                    so_date, so_time, sign_off_stn, duty_hrs, duty_type, train_no, loco_no,
                    wheel_movement, clean_float(avg_speed_raw), clean_float(route_km_raw), clean_float(total_km_raw),
                    mk, str(cto or ""), str(cmo or ""), str(section or ""), str(route_name or ""),
                    json.dumps(list(row_values), default=excel_json_default)
                ))
                
            # Perform master upsert
            for i in range(0, len(master_inserts), 500):
                chunk = master_inserts[i:i + 500]
                cursor.executemany("""
                    INSERT INTO tbl_duty_hours_master (
                        upload_batch_id, record_hash, crew_id, crew_name, designation, total_duty,
                        sign_on_date, sign_on_time, sign_on_stn, departure, pdd, arrival,
                        sign_off_date, sign_off_time, sign_off_stn, duty_hrs, duty_type, train_no, loco_no,
                        wheel_movement, avg_speed, route_km, total_km, mk, cto, cmo, section, route_name, row_data_json
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON DUPLICATE KEY UPDATE
                        upload_batch_id = VALUES(upload_batch_id),
                        crew_name = VALUES(crew_name),
                        designation = VALUES(designation),
                        total_duty = VALUES(total_duty),
                        sign_on_stn = VALUES(sign_on_stn),
                        departure = VALUES(departure),
                        pdd = VALUES(pdd),
                        arrival = VALUES(arrival),
                        sign_off_date = VALUES(sign_off_date),
                        sign_off_time = VALUES(sign_off_time),
                        sign_off_stn = VALUES(sign_off_stn),
                        duty_hrs = VALUES(duty_hrs),
                        duty_type = VALUES(duty_type),
                        wheel_movement = VALUES(wheel_movement),
                        avg_speed = VALUES(avg_speed),
                        route_km = VALUES(route_km),
                        total_km = VALUES(total_km),
                        mk = VALUES(mk),
                        cto = VALUES(cto),
                        cmo = VALUES(cmo),
                        section = VALUES(section),
                        route_name = VALUES(route_name),
                        row_data_json = VALUES(row_data_json)
                """, chunk)

            # Sync with Long Hours master (non-blocking)
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
            conn.commit()
        except Exception as e:
            conn.rollback()
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise HTTPException(status_code=500, detail=f"Database write error: {str(e)}")
        finally:
            cursor.close()
            conn.close()
            
        if not unique_dates:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail="No valid Sign Off Dates found in Column K.")
            
        # Sort dates
        sorted_dates = []
        def key_func(date_str):
            try:
                return datetime.strptime(date_str, "%d-%m-%Y")
            except ValueError:
                return datetime.min
        sorted_dates = sorted(list(unique_dates), key=key_func)
        
        # Calculate group counts per sign_off_date with slab breakdowns
        date_counts = {}
        for g in duty_groups:
            dt = g["sign_off_date"]
            if not dt:
                continue
            if dt not in date_counts:
                date_counts[dt] = {
                    "total": 0,
                    "le_4": 0,
                    "4_9": 0,
                    "9_12": 0,
                    "12_14": 0,
                    "over_14": 0
                }
            
            # Fetch first row total duty to parse slab
            first_row_idx = g["rows"][0]
            row_vals = all_rows[first_row_idx - 1] if first_row_idx <= len(all_rows) else []
            total_duty_val = row_vals[total_duty_col - 1] if len(row_vals) >= total_duty_col else None
            hours = parse_duty_hours_to_float(total_duty_val)
            
            date_counts[dt]["total"] += 1
            if hours <= 4.0:
                date_counts[dt]["le_4"] += 1
            elif hours <= 9.0:
                date_counts[dt]["4_9"] += 1
            elif hours <= 12.0:
                date_counts[dt]["9_12"] += 1
            elif hours <= 14.0:
                date_counts[dt]["12_14"] += 1
            else:
                date_counts[dt]["over_14"] += 1
                
        def calc_pct(count, tot):
            if tot == 0:
                return "0.0%"
            return f"{(count / tot * 100):.1f}%"

        # Generate summary string and list with nos and percentage for each slab
        summary_parts = []
        summary_data = []
        tot_all = 0
        tot_le_4 = 0
        tot_4_9 = 0
        tot_9_12 = 0
        tot_12_14 = 0
        tot_over_14 = 0

        for dt in sorted_dates:
            stats = date_counts.get(dt, {
                "total": 0,
                "le_4": 0,
                "4_9": 0,
                "9_12": 0,
                "12_14": 0,
                "over_14": 0
            })
            total = stats["total"]
            tot_all += total
            tot_le_4 += stats["le_4"]
            tot_4_9 += stats["4_9"]
            tot_9_12 += stats["9_12"]
            tot_12_14 += stats["12_14"]
            tot_over_14 += stats["over_14"]

            # Format date from DD-MM-YYYY to DD.MM.YY
            try:
                dt_obj = datetime.strptime(dt, "%d-%m-%Y")
                dt_formatted = dt_obj.strftime("%d.%m.%y")
            except Exception:
                dt_formatted = dt.replace("-", ".")

            p_le_4 = calc_pct(stats["le_4"], total)
            p_4_9 = calc_pct(stats["4_9"], total)
            p_9_12 = calc_pct(stats["9_12"], total)
            p_12_14 = calc_pct(stats["12_14"], total)
            p_over_14 = calc_pct(stats["over_14"], total)

            summary_parts.append(
                f"{dt_formatted} = {total} (<=4h: {stats['le_4']} [{p_le_4}], "
                f"04-09h: {stats['4_9']} [{p_4_9}], "
                f"09-12h: {stats['9_12']} [{p_9_12}], "
                f"12-14h: {stats['12_14']} [{p_12_14}], "
                f">14h: {stats['over_14']} [{p_over_14}])"
            )
            summary_data.append({
                "date": dt_formatted,
                "raw_date": dt,
                "total": total,
                "le_4": stats["le_4"],
                "le_4_pct": p_le_4,
                "slab_4_9": stats["4_9"],
                "slab_4_9_pct": p_4_9,
                "slab_9_12": stats["9_12"],
                "slab_9_12_pct": p_9_12,
                "12_14": stats["12_14"],
                "12_14_pct": p_12_14,
                "over_14": stats["over_14"],
                "over_14_pct": p_over_14
            })
            
        summary_totals = {
            "total": tot_all,
            "le_4": tot_le_4,
            "le_4_pct": calc_pct(tot_le_4, tot_all),
            "slab_4_9": tot_4_9,
            "slab_4_9_pct": calc_pct(tot_4_9, tot_all),
            "slab_9_12": tot_9_12,
            "slab_9_12_pct": calc_pct(tot_9_12, tot_all),
            "12_14": tot_12_14,
            "12_14_pct": calc_pct(tot_12_14, tot_all),
            "over_14": tot_over_14,
            "over_14_pct": calc_pct(tot_over_14, tot_all)
        }
        dates_summary_str = " | ".join(summary_parts)
        
        return {
            "file_id": temp_filename,
            "unique_dates": sorted_dates,
            "dates_summary": dates_summary_str,
            "dates_summary_data": summary_data,
            "summary_totals": summary_totals
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error reading workbook: {str(e)}")

@duty_hours_bp.route("/filter", methods=["POST"])
def filter_duty_hours():
    payload = request.get_json(silent=True) or {}
    cleanup_temp_files()
    
    file_id = payload.get("file_id")
    from_date = payload.get("from_date")
    to_date = payload.get("to_date")
    selected_date = payload.get("selected_date") # fallback
    duty_slab = payload.get("duty_slab", "all")
    
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing file_id.")
        
    if not from_date and not to_date and selected_date:
        from_date = selected_date
        to_date = selected_date
        
    if not from_date or not to_date:
        raise HTTPException(status_code=400, detail="Missing sign off date selection.")
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get file metadata
            cursor.execute("SELECT header_row, sl_col, sign_off_col, headers_json FROM duty_hours_files WHERE id = %s", (file_id,))
            file_meta = cursor.fetchone()
            if not file_meta:
                raise HTTPException(status_code=404, detail="Session expired. Please upload your file again.")
                
            header_row, sl_col, sign_off_col, headers_json = _unpack_file_meta(file_meta)
            
            # Query matching rows (HEADER, FOOTER, or within the date range)
            if getattr(conn, "is_sqlite", False):
                fd_iso = f"{from_date[6:10]}-{from_date[3:5]}-{from_date[0:2]}" if len(from_date) == 10 else from_date
                td_iso = f"{to_date[6:10]}-{to_date[3:5]}-{to_date[0:2]}" if len(to_date) == 10 else to_date
                cursor.execute(
                    """
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND (
                        (sign_off_date NOT IN ('HEADER', 'FOOTER') 
                         AND (substr(sign_off_date, 7, 4) || '-' || substr(sign_off_date, 4, 2) || '-' || substr(sign_off_date, 1, 2)) BETWEEN %s AND %s)
                        OR sign_off_date = 'HEADER' 
                        OR sign_off_date = 'FOOTER'
                      )
                    ORDER BY row_index
                    """,
                    (file_id, fd_iso, td_iso)
                )
            else:
                cursor.execute(
                    """
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND (
                        (sign_off_date NOT IN ('HEADER', 'FOOTER') 
                         AND STR_TO_DATE(sign_off_date, '%%d-%%m-%%Y') BETWEEN STR_TO_DATE(%s, '%%d-%%m-%%Y') AND STR_TO_DATE(%s, '%%d-%%m-%%Y'))
                        OR sign_off_date = 'HEADER' 
                        OR sign_off_date = 'FOOTER'
                      )
                    ORDER BY row_index
                    """,
                    (file_id, from_date, to_date)
                )
            db_rows = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        
        if not db_rows:
            raise HTTPException(status_code=404, detail=f"No duties found for the selected date range.")
            
        # Parse headers_json to find total_duty_col dynamically
        headers = json.loads(headers_json)
        total_duty_col = 5  # Default to E (5th column)
        found_totalduty = False
        for idx, h in enumerate(headers, start=1):
            h_clean = str(h or "").strip().lower()
            h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
            if "totalduty" in h_clean:
                total_duty_col = idx
                found_totalduty = True
                
        if not found_totalduty:
            for idx, h in enumerate(headers, start=1):
                h_clean = str(h or "").strip().lower()
                h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
                if "dutyhrs" in h_clean or "workinghours" in h_clean:
                    total_duty_col = idx
                    break
            
        # Filter data rows to compute groups
        groups = []
        current_group = []
        current_sl = None
        
        for row in db_rows:
            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)
            if sign_off_date in ("HEADER", "FOOTER"):
                continue
                
            clean_val = str(sl_no).strip()
            if clean_val != "":
                if current_group and clean_val == current_sl:
                    current_group.append(r_idx)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [r_idx]
                    current_sl = clean_val
            else:
                if current_group:
                    current_group.append(r_idx)
                else:
                    current_group = [r_idx]
                    current_sl = ""
                    
        if current_group:
            groups.append(current_group)
            
        # Map row index to row data & sign_off_date
        row_values_map = {}
        row_date_map = {}
        for row in db_rows:
            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)
            row_values_map[r_idx] = json.loads(row_data_json)
            row_date_map[r_idx] = sign_off_date
            
        # Filter groups by duty slab
        kept_groups = []
        for g in groups:
            first_row_idx = g[0]
            row_vals = row_values_map.get(first_row_idx, [])
            total_duty_val = row_vals[total_duty_col - 1] if len(row_vals) >= total_duty_col else None
            
            hours = parse_duty_hours_to_float(total_duty_val)
            
            keep = False
            if duty_slab == "all":
                keep = True
            elif duty_slab in ("0-4", "le_4"):
                keep = (hours <= 4.0)
            elif duty_slab in ("4-9", "04-09"):
                keep = (4.0 < hours <= 9.0)
            elif duty_slab == "under_9":
                keep = (hours <= 9.0)
            elif duty_slab in ("9-12", "09-12"):
                keep = (9.0 < hours <= 12.0)
            elif duty_slab == "12-14":
                keep = (12.0 <= hours <= 14.0)
            elif duty_slab == "over_14":
                keep = (hours > 14.0)
                
            if keep:
                kept_groups.append({
                    "rows": g,
                    "sign_off_date": row_date_map.get(first_row_idx)
                })
                
        total_groups = len(kept_groups)
        total_rows_count = sum(len(g["rows"]) for g in kept_groups)
        
        if total_groups == 0:
            raise HTTPException(status_code=404, detail="No duties found matching the selected filters.")
            
        # Find route column: prioritize "route name", then check "route" excluding kms/distance/hours/etc.
        route_col = None
        # Try finding "route name" or "route_name" first
        for idx, h in enumerate(headers, start=1):
            h_clean = str(h or "").strip().lower()
            if "route name" in h_clean or "route_name" in h_clean:
                route_col = idx
                break
        
        # If not found, look for "route" without kms/distance/hours/time/etc.
        if route_col is None:
            for idx, h in enumerate(headers, start=1):
                h_clean = str(h or "").strip().lower()
                if "route" in h_clean and not any(x in h_clean for x in ["km", "distance", "dist", "hr", "time"]):
                    route_col = idx
                    break
                    
        # Fallback to the last column
        if route_col is None:
            route_col = len(headers)
            
        # Find wheel movement column dynamically
        wheel_mov_col = None
        for idx, h in enumerate(headers, start=1):
            h_clean = str(h or "").strip().lower()
            h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
            if "wheelmovement" in h_clean:
                wheel_mov_col = idx
                break
                
        # Calculate Route-wise summary
        route_summary = {}
        for g in kept_groups:
            first_row_idx = g["rows"][0]
            row_vals = row_values_map.get(first_row_idx, [])
            total_duty_val = row_vals[total_duty_col - 1] if len(row_vals) >= total_duty_col else None
            hours = parse_duty_hours_to_float(total_duty_val)
            
            # Extract wheel movement hours
            wheel_val = None
            if wheel_mov_col:
                wheel_val = row_vals[wheel_mov_col - 1] if len(row_vals) >= wheel_mov_col else None
            wheel_hours = parse_duty_hours_to_float(wheel_val) if wheel_val else 0.0
            
            # Find route name
            route_name = ""
            for r_idx in g["rows"]:
                r_row_vals = row_values_map.get(r_idx, [])
                if len(r_row_vals) >= route_col:
                    r_val = str(r_row_vals[route_col - 1] or "").strip()
                    if r_val:
                        route_name = r_val
                        break
            if not route_name:
                route_name = "Not Specified"
                
            if route_name not in route_summary:
                route_summary[route_name] = {"count": 0, "total_hours": 0.0, "total_wheel_hours": 0.0}
            route_summary[route_name]["count"] += 1
            route_summary[route_name]["total_hours"] += hours
            route_summary[route_name]["total_wheel_hours"] += wheel_hours
            
        route_list = []
        for name, stats in route_summary.items():
            avg_hours = stats["total_hours"] / stats["count"] if stats["count"] > 0 else 0.0
            avg_wheel = stats["total_wheel_hours"] / stats["count"] if stats["count"] > 0 else 0.0
            route_list.append({
                "route": name,
                "duty_count": stats["count"],
                "avg_duty_hours": format_float_hours_to_hhmm(avg_hours),
                "avg_wheel_movement": format_float_hours_to_hhmm(avg_wheel)
            })
        route_list = sorted(route_list, key=lambda x: x["duty_count"], reverse=True)
            
        # Generate styled HTML preview from DB rows
        html = ['<table class="excel-preview-table table table-bordered table-striped">']
        
        # Map row index to new serial number
        row_to_serial = {}
        for idx, g in enumerate(kept_groups, start=1):
            for r in g["rows"]:
                row_to_serial[r] = idx
                
        # Format date display string
        display_date = from_date
        if from_date != to_date:
            display_date = f"{from_date} TO {to_date}"
            
        # Render rows
        rows_rendered = 0
        MAX_PREVIEW_ROWS = 50
        for row in db_rows:
            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)
            row_values = json.loads(row_data_json)
            
            # Skip data rows that belong to filtered-out duty groups
            if sign_off_date not in ("HEADER", "FOOTER") and r_idx > header_row and r_idx not in row_to_serial:
                continue
                
            if rows_rendered >= MAX_PREVIEW_ROWS:
                html.append(f'<tr><td colspan="{len(row_values)}" style="text-align: center; padding: 15px; color: #64748b; font-style: italic;">Preview limited to {MAX_PREVIEW_ROWS} rows for performance. Download the Excel file to view all {total_rows_count} rows.</td></tr>')
                break
            rows_rendered += 1
                
            # Determine if header/footer/data row for styling
            tr_style = ""
            if sign_off_date == "HEADER":
                tr_style = ' style="background-color: #d9e1f2; font-weight: bold; text-align: center;"'
            elif sign_off_date == "FOOTER":
                tr_style = ' style="background-color: #f2f2f2; font-weight: bold;"'
                
            html.append(f'<tr{tr_style}>')
            
            if r_idx == 1:
                # Merge the entire first row across all columns
                val = row_values[0]
                if isinstance(val, str):
                    date_match = re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", val)
                    if date_match:
                        val = val[:date_match.start()] + display_date + val[date_match.end():]
                    else:
                        clean_val = val.rstrip()
                        if clean_val.lower().endswith("for"):
                            val = f"{clean_val} {display_date}"
                        elif clean_val.lower().endswith("date") or clean_val.lower().endswith("date:"):
                            val = f"{clean_val} {display_date}"
                        else:
                            val = f"{clean_val} FOR {display_date}"
                val_str = str(val) if val is not None else ""
                val_escaped = html_escapers.escape(val_str)
                html.append(f'<td colspan="{len(row_values)}" style="text-align: center; font-weight: bold; font-size: 1.15rem; background-color: #f8fafc; padding: 10px; color: #1e293b;">{val_escaped}</td>')
            else:
                for c_idx, cell_val in enumerate(row_values, start=1):
                    # On the fly replacements
                    val = cell_val
                    if r_idx in row_to_serial and c_idx == sl_col:
                        val = row_to_serial[r_idx]
                    elif isinstance(val, str):
                        # Update totals on the fly
                        val = re.sub(
                            r"(total\s+(duty\s+groups|duties|groups))\s*:\s*\d+",
                            f"\\1 : {total_groups}",
                            val,
                            flags=re.IGNORECASE
                        )
                        val = re.sub(
                            r"(total\s+rows)\s*:\s*\d+",
                            f"\\1 : {total_rows_count}",
                            val,
                            flags=re.IGNORECASE
                        )
                        # Update title/heading on the fly
                        if r_idx <= 5 and ("report" in val.lower() or "working hours" in val.lower()):
                            date_match = re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", val)
                            if date_match:
                                val = val[:date_match.start()] + display_date + val[date_match.end():]
                            else:
                                clean_val = val.rstrip()
                                if clean_val.lower().endswith("for"):
                                    val = f"{clean_val} {display_date}"
                                elif clean_val.lower().endswith("date") or clean_val.lower().endswith("date:"):
                                    val = f"{clean_val} {display_date}"
                                else:
                                    val = f"{clean_val} FOR {display_date}"
                                    
                    val_str = ""
                    if val is not None:
                        val_str = str(val)
                    val_escaped = html_escapers.escape(val_str)
                    
                    html.append(f'<td>{val_escaped}</td>')
                    
            html.append('</tr>')
            
        html.append('</table>')
        html_preview = "\n".join(html)
        
        # Build download query params range
        download_id = f"{file_id}?from_date={from_date}&to_date={to_date}&duty_slab={duty_slab}"
        
        return {
            "total_groups": total_groups,
            "total_rows": total_rows_count,
            "html_preview": html_preview,
            "download_id": download_id,
            "route_summary": route_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error filtering workbook: {str(e)}")


@duty_hours_bp.route("/download/<download_id>", methods=["GET"])
def download_duty_hours(download_id):
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    selected_date = request.args.get("selected_date")
    duty_slab = request.args.get("duty_slab", "all")
    # check if download_id is the original file
    file_path = os.path.join(TEMP_DIR, download_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Download link expired or invalid.")
        
    if not from_date and not to_date and selected_date:
        from_date = selected_date
        to_date = selected_date
        
    if not from_date and not to_date:
        # Fallback to direct file download
        return FileResponse(
            path=file_path,
            filename="Filtered_Continuous_Working_Hours.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    try:
        # Perform the actual row deletion and formatting on download
        wb = openpyxl.load_workbook(file_path, data_only=False)
        sheet = wb.active
        
        header_row, sl_col, sign_off_col, total_duty_col = detect_header_and_columns(sheet)
        
        # Group duties
        duty_groups = detect_duty_groups(sheet, header_row, sl_col, sign_off_col)
        
        # Filter duties by date range
        if from_date and to_date:
            try:
                fd = datetime.strptime(from_date, "%d-%m-%Y")
                td = datetime.strptime(to_date, "%d-%m-%Y")
                
                def is_in_range(g_date_str):
                    if not g_date_str:
                        return False
                    try:
                        gd = datetime.strptime(g_date_str, "%d-%m-%Y")
                        return fd <= gd <= td
                    except ValueError:
                        return False
                        
                date_groups = [g for g in duty_groups if is_in_range(g["sign_off_date"])]
            except Exception as e:
                print(f"Error parsing date range for download: {e}")
                date_groups = []
        else:
            date_groups = [g for g in duty_groups if g["sign_off_date"] == selected_date]
            
        if not date_groups:
            wb.close()
            raise HTTPException(status_code=404, detail="No duties found for the selected range.")
            
        # Filter duties by slab
        kept_groups = []
        for g in date_groups:
            first_row_idx = g["rows"][0]
            total_duty_val = sheet.cell(row=first_row_idx, column=total_duty_col).value
            
            hours = parse_duty_hours_to_float(total_duty_val)
            
            keep = False
            if duty_slab == "all":
                keep = True
            elif duty_slab in ("0-4", "le_4"):
                keep = (hours <= 4.0)
            elif duty_slab in ("4-9", "04-09"):
                keep = (4.0 < hours <= 9.0)
            elif duty_slab == "under_9":
                keep = (hours <= 9.0)
            elif duty_slab in ("9-12", "09-12"):
                keep = (9.0 < hours <= 12.0)
            elif duty_slab == "12-14":
                keep = (12.0 <= hours <= 14.0)
            elif duty_slab == "over_14":
                keep = (hours > 14.0)
                
            if keep:
                kept_groups.append(g)
                
        if not kept_groups:
            wb.close()
            raise HTTPException(status_code=404, detail="No duties found matching the selected filters.")
            
        # Determine rows to keep vs delete
        kept_rows = set()
        for g in kept_groups:
            kept_rows.update(g["rows"])
        for r in range(1, header_row + 1):
            kept_rows.add(r)
            
        rows_data = list(sheet.iter_rows(values_only=True))
        max_row = len(rows_data)
        for r in range(header_row + 1, max_row + 1):
            row_tuple = rows_data[r - 1]
            is_footer = False
            for val in row_tuple:
                if isinstance(val, str) and any(x in val.lower() for x in ["total", "group", "row"]):
                    is_footer = True
                    break
            if is_footer:
                kept_rows.add(r)
                
        # Rows to delete
        all_data_rows = set(range(header_row + 1, max_row + 1))
        
        def get_contiguous_ranges(indices):
            if not indices:
                return []
            sorted_indices = sorted(list(indices))
            ranges = []
            start = sorted_indices[0]
            prev = sorted_indices[0]
            for val in sorted_indices[1:]:
                if val == prev + 1:
                    prev = val
                else:
                    ranges.append((start, prev - start + 1))
                    start = val
                    prev = val
            ranges.append((start, prev - start + 1))
            return ranges

        ranges_to_delete = get_contiguous_ranges(all_data_rows - kept_rows)
        for start_idx, count in sorted(ranges_to_delete, key=lambda x: x[0], reverse=True):
            sheet.delete_rows(start_idx, count)
            
        # Group again and renumber
        filtered_duty_groups = detect_duty_groups(sheet, header_row, sl_col, sign_off_col)
        total_groups = len(filtered_duty_groups)
        total_rows_count = sum(len(g["rows"]) for g in filtered_duty_groups)
        
        for idx, g in enumerate(filtered_duty_groups, start=1):
            for r in g["rows"]:
                sheet.cell(row=r, column=sl_col).value = idx
                
        update_total_labels_in_sheet(sheet, total_groups, total_rows_count)
        
        # Heading text includes date and slab if not all
        if from_date and to_date:
            if from_date == to_date:
                heading_suffix = from_date
            else:
                heading_suffix = f"{from_date} TO {to_date}"
        else:
            heading_suffix = selected_date or "SELECTED DATES"
            
        if duty_slab != "all":
            slab_labels = {
                "0-4": "<= 4 hrs",
                "le_4": "<= 4 hrs",
                "4-9": "04-09 hrs",
                "04-09": "04-09 hrs",
                "under_9": "< 9 hrs",
                "9-12": "09-12 hrs",
                "09-12": "09-12 hrs",
                "12-14": "12-14 hrs",
                "over_14": "> 14 hrs"
            }
            heading_suffix += f" ({slab_labels.get(duty_slab, duty_slab)})"
        update_heading_in_sheet(sheet, heading_suffix)
        
        # Save to a temporary download path
        temp_download_id = f"output_{str(uuid.uuid4())}.xlsx"
        temp_download_path = os.path.join(TEMP_DIR, temp_download_id)
        wb.save(temp_download_path)
        wb.close()
        
        filename_slab = f"_{duty_slab}" if duty_slab != "all" else ""
        date_filename_part = f"{from_date}_to_{to_date}" if from_date != to_date else from_date
        return FileResponse(
            path=temp_download_path,
            filename=f"Filtered_Continuous_Working_Hours_{date_filename_part}{filename_slab}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating download file: {str(e)}")


@duty_hours_bp.route("/download-route-summary", methods=["GET"])
def download_route_summary():
    file_id = request.args.get("file_id")
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    duty_slab = request.args.get("duty_slab", "all")
    if not file_id or not from_date or not to_date:
        raise HTTPException(status_code=400, detail="Missing required parameters.")
        
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get file metadata
            cursor.execute("SELECT header_row, sl_col, sign_off_col, headers_json FROM duty_hours_files WHERE id = %s", (file_id,))
            file_meta = cursor.fetchone()
            if not file_meta:
                raise HTTPException(status_code=404, detail="Session expired. Please upload your file again.")
                
            header_row, sl_col, sign_off_col, headers_json = _unpack_file_meta(file_meta)
            
            # Query matching rows
            if getattr(conn, "is_sqlite", False):
                fd_iso = f"{from_date[6:10]}-{from_date[3:5]}-{from_date[0:2]}" if len(from_date) == 10 else from_date
                td_iso = f"{to_date[6:10]}-{to_date[3:5]}-{to_date[0:2]}" if len(to_date) == 10 else to_date
                cursor.execute(
                    """
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND sign_off_date NOT IN ('HEADER', 'FOOTER') 
                      AND (substr(sign_off_date, 7, 4) || '-' || substr(sign_off_date, 4, 2) || '-' || substr(sign_off_date, 1, 2)) BETWEEN %s AND %s
                    ORDER BY row_index
                    """,
                    (file_id, fd_iso, td_iso)
                )
            else:
                cursor.execute(
                    """
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND sign_off_date NOT IN ('HEADER', 'FOOTER') 
                      AND STR_TO_DATE(sign_off_date, '%%d-%%m-%%Y') BETWEEN STR_TO_DATE(%s, '%%d-%%m-%%Y') AND STR_TO_DATE(%s, '%%d-%%m-%%Y')
                    ORDER BY row_index
                    """,
                    (file_id, from_date, to_date)
                )
            db_rows = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
            
        if not db_rows:
            raise HTTPException(status_code=404, detail="No duties found for the selected date range.")
            
        # Parse headers_json to find total_duty_col dynamically
        headers = json.loads(headers_json)
        total_duty_col = 5  # Default to E (5th column)
        found_totalduty = False
        for idx, h in enumerate(headers, start=1):
            h_clean = str(h or "").strip().lower()
            h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
            if "totalduty" in h_clean:
                total_duty_col = idx
                found_totalduty = True
                
        if not found_totalduty:
            for idx, h in enumerate(headers, start=1):
                h_clean = str(h or "").strip().lower()
                h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
                if "dutyhrs" in h_clean or "workinghours" in h_clean:
                    total_duty_col = idx
                    break
            
        # Filter data rows to compute groups
        groups = []
        current_group = []
        current_sl = None
        
        for row in db_rows:
            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)
            
            clean_val = str(sl_no).strip()
            if clean_val != "":
                if current_group and clean_val == current_sl:
                    current_group.append(r_idx)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [r_idx]
                    current_sl = clean_val
            else:
                if current_group:
                    current_group.append(r_idx)
                else:
                    current_group = [r_idx]
                    current_sl = ""
                    
        if current_group:
            groups.append(current_group)
            
        # Map row index to row data & sign_off_date
        row_values_map = {}
        row_date_map = {}
        for row in db_rows:
            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)
            row_values_map[r_idx] = json.loads(row_data_json)
            row_date_map[r_idx] = sign_off_date
            
        # Filter groups by duty slab
        kept_groups = []
        for g in groups:
            first_row_idx = g[0]
            row_vals = row_values_map.get(first_row_idx, [])
            total_duty_val = row_vals[total_duty_col - 1] if len(row_vals) >= total_duty_col else None
            
            hours = parse_duty_hours_to_float(total_duty_val)
            
            keep = False
            if duty_slab == "all":
                keep = True
            elif duty_slab in ("0-4", "le_4"):
                keep = (hours <= 4.0)
            elif duty_slab in ("4-9", "04-09"):
                keep = (4.0 < hours <= 9.0)
            elif duty_slab == "under_9":
                keep = (hours <= 9.0)
            elif duty_slab in ("9-12", "09-12"):
                keep = (9.0 < hours <= 12.0)
            elif duty_slab == "12-14":
                keep = (12.0 <= hours <= 14.0)
            elif duty_slab == "over_14":
                keep = (hours > 14.0)
                
            if keep:
                kept_groups.append({
                    "rows": g,
                    "sign_off_date": row_date_map.get(first_row_idx)
                })
                
        if not kept_groups:
            raise HTTPException(status_code=404, detail="No duties match the current filters.")
            
        # Find route column: prioritize "route name", then check "route" excluding kms/distance/hours/etc.
        route_col = None
        # Try finding "route name" or "route_name" first
        for idx, h in enumerate(headers, start=1):
            h_clean = str(h or "").strip().lower()
            if "route name" in h_clean or "route_name" in h_clean:
                route_col = idx
                break
        
        # If not found, look for "route" without kms/distance/hours/time/etc.
        if route_col is None:
            for idx, h in enumerate(headers, start=1):
                h_clean = str(h or "").strip().lower()
                if "route" in h_clean and not any(x in h_clean for x in ["km", "distance", "dist", "hr", "time"]):
                    route_col = idx
                    break
                    
        # Fallback to the last column
        if route_col is None:
            route_col = len(headers)
            
        # Find wheel movement column dynamically
        wheel_mov_col = None
        for idx, h in enumerate(headers, start=1):
            h_clean = str(h or "").strip().lower()
            h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
            if "wheelmovement" in h_clean:
                wheel_mov_col = idx
                break

        # Calculate Route-wise summary
        route_summary = {}
        for g in kept_groups:
            first_row_idx = g["rows"][0]
            row_vals = row_values_map.get(first_row_idx, [])
            total_duty_val = row_vals[total_duty_col - 1] if len(row_vals) >= total_duty_col else None
            hours = parse_duty_hours_to_float(total_duty_val)
            
            # Extract wheel movement hours
            wheel_val = None
            if wheel_mov_col:
                wheel_val = row_vals[wheel_mov_col - 1] if len(row_vals) >= wheel_mov_col else None
            wheel_hours = parse_duty_hours_to_float(wheel_val) if wheel_val else 0.0
            
            # Find route name
            route_name = ""
            for r_idx in g["rows"]:
                r_row_vals = row_values_map.get(r_idx, [])
                if len(r_row_vals) >= route_col:
                    r_val = str(r_row_vals[route_col - 1] or "").strip()
                    if r_val:
                        route_name = r_val
                        break
            if not route_name:
                route_name = "Not Specified"
                
            if route_name not in route_summary:
                route_summary[route_name] = {"count": 0, "total_hours": 0.0, "total_wheel_hours": 0.0}
            route_summary[route_name]["count"] += 1
            route_summary[route_name]["total_hours"] += hours
            route_summary[route_name]["total_wheel_hours"] += wheel_hours
            
        route_list = []
        for name, stats in route_summary.items():
            avg_hours = stats["total_hours"] / stats["count"] if stats["count"] > 0 else 0.0
            avg_wheel = stats["total_wheel_hours"] / stats["count"] if stats["count"] > 0 else 0.0
            route_list.append({
                "route": name,
                "duty_count": stats["count"],
                "avg_duty_hours": format_float_hours_to_hhmm(avg_hours),
                "avg_wheel_movement": format_float_hours_to_hhmm(avg_wheel)
            })
        route_list = sorted(route_list, key=lambda x: x["duty_count"], reverse=True)
        
        # Create Excel workbook using openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Route-wise Summary"
        
        # Show grid lines
        ws.views.sheetView[0].showGridLines = True
        
        # Styling
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark blue
        center_align = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")
        right_align = Alignment(horizontal="right", vertical="center")
        
        title_font = Font(name="Segoe UI", size=14, bold=True, color="1E3A8A")
        subtitle_font = Font(name="Segoe UI", size=10, italic=True)
        data_font = Font(name="Segoe UI", size=10)
        
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        
        # Write Title and metadata
        ws.cell(row=1, column=1, value="Route-wise Duty Summary").font = title_font
        date_range_str = f"Date Range: {from_date} to {to_date}" if from_date != to_date else f"Date: {from_date}"
        ws.cell(row=2, column=1, value=f"{date_range_str} | Slab Filter: {duty_slab}").font = subtitle_font
        
        # Table Headers
        headers_row = ["Route", "Duty Count", "Avg Duty Hours (HH:MM)", "Avg Wheel Movement (HH:MM)"]
        for col_idx, h in enumerate(headers_row, start=1):
            cell = ws.cell(row=4, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align if col_idx > 1 else left_align
            cell.border = thin_border
            
        # Write data
        for row_idx, item in enumerate(route_list, start=5):
            c1 = ws.cell(row=row_idx, column=1, value=item["route"])
            c2 = ws.cell(row=row_idx, column=2, value=item["duty_count"])
            c3 = ws.cell(row=row_idx, column=3, value=item["avg_duty_hours"])
            c4 = ws.cell(row=row_idx, column=4, value=item["avg_wheel_movement"])
            
            for c_cell in (c1, c2, c3, c4):
                c_cell.font = data_font
                c_cell.border = thin_border
                
            c1.alignment = left_align
            c2.alignment = right_align
            c3.alignment = center_align
            c4.alignment = center_align
            
        # Set column widths
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 28
        
        # Save workbook to file
        temp_download_id = f"route_summary_{str(uuid.uuid4())}.xlsx"
        temp_download_path = os.path.join(TEMP_DIR, temp_download_id)
        wb.save(temp_download_path)
        wb.close()
        
        date_filename_part = f"{from_date}_to_{to_date}" if from_date != to_date else from_date
        return FileResponse(
            path=temp_download_path,
            filename=f"Route_Wise_Summary_{date_filename_part}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating route-wise summary Excel: {str(e)}")


@duty_hours_bp.route("/download-dates-summary", methods=["GET"])
def download_dates_summary():
    file_id = request.args.get("file_id")
    if not file_id:
        raise HTTPException(status_code=400, detail="Missing required parameters.")
        
    try:
        conn = get_connection()
        cursor = conn.conn.cursor() if hasattr(conn, 'conn') else conn.cursor()
        
        try:
            # Get file metadata
            cursor.execute("SELECT header_row, sl_col, sign_off_col, headers_json FROM duty_hours_files WHERE id = %s", (file_id,))
            file_meta = cursor.fetchone()
            if not file_meta:
                raise HTTPException(status_code=404, detail="Session expired. Please upload your file again.")
                
            header_row, sl_col, sign_off_col, headers_json = _unpack_file_meta(file_meta)
            
            # Query all rows to compute groups correctly
            cursor.execute(
                """
                SELECT row_index, sl_no, sign_off_date, row_data_json 
                FROM duty_hours_rows 
                WHERE file_id = %s 
                ORDER BY row_index
                """,
                (file_id,)
            )
            db_rows = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        
        if not db_rows:
            raise HTTPException(status_code=404, detail="No duties found.")
            
        # Group duties using the exact same logic as detection
        groups = []
        current_group = []
        current_sl = None
        
        for row in db_rows:
            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)
            if sign_off_date in ("HEADER", "FOOTER"):
                continue
                
            clean_val = str(sl_no).strip()
            if clean_val != "":
                if current_group and clean_val == current_sl:
                    current_group.append(r_idx)
                else:
                    if current_group:
                        groups.append(current_group)
                    current_group = [r_idx]
                    current_sl = clean_val
            else:
                if current_group:
                    current_group.append(r_idx)
                else:
                    current_group = [r_idx]
                    current_sl = ""
                    
        if current_group:
            groups.append(current_group)
            
        # Parse headers to locate total_duty_col dynamically
        headers = json.loads(headers_json)
        total_duty_col = 5
        found_totalduty = False
        for idx, h in enumerate(headers, start=1):
            h_clean = str(h or "").strip().lower()
            h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
            if "totalduty" in h_clean:
                total_duty_col = idx
                found_totalduty = True
        if not found_totalduty:
            for idx, h in enumerate(headers, start=1):
                h_clean = str(h or "").strip().lower()
                h_clean = h_clean.replace(" ", "").replace(".", "").replace("_", "").replace("-", "")
                if "dutyhrs" in h_clean or "workinghours" in h_clean:
                    total_duty_col = idx
                    break

        # Map row index to row data & sign_off_date
        row_values_map = {}
        row_to_date = {}
        for row in db_rows:
            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)
            if sign_off_date not in ("HEADER", "FOOTER"):
                row_to_date[r_idx] = sign_off_date
                row_values_map[r_idx] = json.loads(row_data_json)
                
        # Count groups per sign off date with breakdowns
        date_counts = {}
        unique_dates = set()
        for g in groups:
            group_date = None
            for r_idx in g:
                if r_idx in row_to_date:
                    group_date = row_to_date[r_idx]
                    break
            if group_date:
                unique_dates.add(group_date)
                if group_date not in date_counts:
                    date_counts[group_date] = {
                        "total": 0,
                        "le_4": 0,
                        "4_9": 0,
                        "9_12": 0,
                        "12_14": 0,
                        "over_14": 0
                    }
                
                # Fetch total duty hours of the group
                first_row_idx = g[0]
                row_vals = row_values_map.get(first_row_idx, [])
                total_duty_val = row_vals[total_duty_col - 1] if len(row_vals) >= total_duty_col else None
                hours = parse_duty_hours_to_float(total_duty_val)
                
                date_counts[group_date]["total"] += 1
                if hours <= 4.0:
                    date_counts[group_date]["le_4"] += 1
                elif hours <= 9.0:
                    date_counts[group_date]["4_9"] += 1
                elif hours <= 12.0:
                    date_counts[group_date]["9_12"] += 1
                elif hours <= 14.0:
                    date_counts[group_date]["12_14"] += 1
                else:
                    date_counts[group_date]["over_14"] += 1
                
        # Sort dates chronologically
        from datetime import datetime
        def key_func(date_str):
            try:
                return datetime.strptime(date_str, "%d-%m-%Y")
            except Exception:
                return datetime.min
                
        sorted_dates = sorted(list(unique_dates), key=key_func)
        
        # Generate Excel using openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Dates Summary"
        
        # Show grid lines
        ws.views.sheetView[0].showGridLines = True
        
        # Styling
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
        sub_header_font = Font(name="Segoe UI", size=9, bold=True, color="FFFFFF")
        header_fill_dark = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Dark blue
        header_fill_medium = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid") # Royal blue
        total_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        
        left_align = Alignment(horizontal="left", vertical="center")
        right_align = Alignment(horizontal="right", vertical="center")
        center_align = Alignment(horizontal="center", vertical="center")
        
        title_font = Font(name="Segoe UI", size=14, bold=True, color="1E3A8A")
        subtitle_font = Font(name="Segoe UI", size=10, italic=True, color="64748B")
        data_font = Font(name="Segoe UI", size=10)
        total_font = Font(name="Segoe UI", size=10, bold=True, color="0F172A")
        
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )
        
        total_cell_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='94A3B8'),
            bottom=Side(style='double', color='1E293B')
        )
        
        # Title block
        ws.cell(row=1, column=1, value="Available Sign Off Dates Summary").font = title_font
        ws.cell(row=2, column=1, value="Date-wise duty counts & slab breakdowns (Nos and %)").font = subtitle_font
        
        # Row 4: Top Header Tier
        ws.merge_cells("A4:A5")
        ws.cell(row=4, column=1, value="Sign Off Date")
        
        ws.merge_cells("B4:B5")
        ws.cell(row=4, column=2, value="Total Duties")
        
        ws.merge_cells("C4:D4")
        ws.cell(row=4, column=3, value="<= 4 Hours")
        
        ws.merge_cells("E4:F4")
        ws.cell(row=4, column=5, value="04-09 Hours")
        
        ws.merge_cells("G4:H4")
        ws.cell(row=4, column=7, value="09-12 Hours")
        
        ws.merge_cells("I4:J4")
        ws.cell(row=4, column=9, value="12-14 Hours")
        
        ws.merge_cells("K4:L4")
        ws.cell(row=4, column=11, value="> 14 Hours")
        
        # Row 5: Sub-headers (Nos / %)
        sub_headers = {
            3: "Nos", 4: "%",
            5: "Nos", 6: "%",
            7: "Nos", 8: "%",
            9: "Nos", 10: "%",
            11: "Nos", 12: "%"
        }
        for col_idx, text in sub_headers.items():
            ws.cell(row=5, column=col_idx, value=text)
            
        # Apply styles to header rows (4 and 5)
        for col in range(1, 13):
            c4 = ws.cell(row=4, column=col)
            c4.font = header_font
            c4.fill = header_fill_dark
            c4.alignment = center_align if col > 2 else (left_align if col == 1 else right_align)
            c4.border = thin_border
            
            c5 = ws.cell(row=5, column=col)
            c5.font = sub_header_font
            c5.fill = header_fill_medium if col > 2 else header_fill_dark
            c5.alignment = right_align if col > 1 else left_align
            c5.border = thin_border
            
        # Write data
        tot_all = 0
        tot_le_4 = 0
        tot_4_9 = 0
        tot_9_12 = 0
        tot_12_14 = 0
        tot_over_14 = 0
        
        current_row = 6
        for dt in sorted_dates:
            stats = date_counts.get(dt, {
                "total": 0, "le_4": 0, "4_9": 0, "9_12": 0, "12_14": 0, "over_14": 0
            })
            tot = stats["total"]
            tot_all += tot
            tot_le_4 += stats["le_4"]
            tot_4_9 += stats["4_9"]
            tot_9_12 += stats["9_12"]
            tot_12_14 += stats["12_14"]
            tot_over_14 += stats["over_14"]
            
            p_le_4 = f"{(stats['le_4'] / tot * 100):.1f}%" if tot > 0 else "0.0%"
            p_4_9 = f"{(stats['4_9'] / tot * 100):.1f}%" if tot > 0 else "0.0%"
            p_9_12 = f"{(stats['9_12'] / tot * 100):.1f}%" if tot > 0 else "0.0%"
            p_12_14 = f"{(stats['12_14'] / tot * 100):.1f}%" if tot > 0 else "0.0%"
            p_over_14 = f"{(stats['over_14'] / tot * 100):.1f}%" if tot > 0 else "0.0%"
            
            row_vals = [
                dt,
                tot,
                stats["le_4"], p_le_4,
                stats["4_9"], p_4_9,
                stats["9_12"], p_9_12,
                stats["12_14"], p_12_14,
                stats["over_14"], p_over_14
            ]
            
            for col_idx, val in enumerate(row_vals, start=1):
                cell = ws.cell(row=current_row, column=col_idx, value=val)
                cell.font = data_font
                cell.border = thin_border
                cell.alignment = left_align if col_idx == 1 else right_align
                
            current_row += 1
            
        # Summary Total row
        p_tot_le_4 = f"{(tot_le_4 / tot_all * 100):.1f}%" if tot_all > 0 else "0.0%"
        p_tot_4_9 = f"{(tot_4_9 / tot_all * 100):.1f}%" if tot_all > 0 else "0.0%"
        p_tot_9_12 = f"{(tot_9_12 / tot_all * 100):.1f}%" if tot_all > 0 else "0.0%"
        p_tot_12_14 = f"{(tot_12_14 / tot_all * 100):.1f}%" if tot_all > 0 else "0.0%"
        p_tot_over_14 = f"{(tot_over_14 / tot_all * 100):.1f}%" if tot_all > 0 else "0.0%"
        
        total_vals = [
            "Total",
            tot_all,
            tot_le_4, p_tot_le_4,
            tot_4_9, p_tot_4_9,
            tot_9_12, p_tot_9_12,
            tot_12_14, p_tot_12_14,
            tot_over_14, p_tot_over_14
        ]
        
        for col_idx, val in enumerate(total_vals, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = total_font
            cell.fill = total_fill
            cell.border = total_cell_border
            cell.alignment = left_align if col_idx == 1 else right_align
            
        # Column widths
        ws.column_dimensions['A'].width = 16
        ws.column_dimensions['B'].width = 14
        for col_letter in ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
            ws.column_dimensions[col_letter].width = 12
        
        # Save workbook to file
        temp_download_id = f"dates_summary_{str(uuid.uuid4())}.xlsx"
        temp_download_path = os.path.join(TEMP_DIR, temp_download_id)
        wb.save(temp_download_path)
        wb.close()
        
        return FileResponse(
            path=temp_download_path,
            filename="Available_Sign_Off_Dates_Summary.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dates summary Excel: {str(e)}")
