import os
import io
import re
from datetime import datetime, date
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def clean_cell_str(val):
    if val is None:
        return ""
    if isinstance(val, float):
        # Format whole floats as integers (e.g. 9876543210.0 -> 9876543210)
        if val.is_integer():
            return str(int(val)).strip()
    s = str(val).strip()
    if s.endswith('.0') and not s.endswith('..0'):
        base = s[:-2]
        if base.replace('-', '').isdigit():
            s = base
    return s

def clean_mobile_10(val):
    """Normalize mobile number to exactly 10 digits without country code 91."""
    s = clean_cell_str(val)
    digits = ''.join(c for c in s if c.isdigit())
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    return digits

def read_excel_to_dicts(file_path):
    """
    Reads an Excel file using openpyxl, automatically detecting the header row
    and preserving leading zeros for mobile numbers and PF numbers.
    """
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active
    
    rows_data = []
    for row in sheet.iter_rows(values_only=True):
        if any(cell is not None and str(cell).strip() != "" for cell in row):
            rows_data.append([clean_cell_str(c) for c in row])
            
    if not rows_data:
        return [], []

    # Find the header row
    header_keywords = {
        'CLI', 'CREW', 'NAME', 'MOBILE', 'PHONE', 'PF', 'EMP', 'DESIG', 
        'DESIGNATION', 'CATEGORY', 'CADRE', 'LOBBY', 'HQ', 'CUG', 'HRMS'
    }
    header_idx = 0
    for idx, r in enumerate(rows_data[:10]):
        non_empty = [c.upper() for c in r if c]
        match_count = sum(1 for c in non_empty if any(kw in c for kw in header_keywords))
        if match_count >= 2:
            header_idx = idx
            break

    raw_headers = rows_data[header_idx]
    headers = []
    for i, h in enumerate(raw_headers):
        clean_h = h.strip()
        if not clean_h:
            clean_h = f"COL_{i+1}"
        headers.append(clean_h)

    # Process data rows
    records = []
    for r in rows_data[header_idx + 1:]:
        if not any(c for c in r):
            continue
        rec = {}
        for i, h in enumerate(headers):
            rec[h] = r[i] if i < len(r) else ""
        records.append(rec)

    return records, headers

def map_crew_record(raw_dict, custom_fields=None):
    """
    Maps various column name variations to standard crew master schema:
    - cli_id, cli_name, cli_mobile
    - crew_name, pf_number, mobile, designation, category, lobby
    - custom_fields
    """
    mapped = {
        'cli_id': '',
        'cli_name': '',
        'cli_mobile': '',
        'crew_name': '',
        'pf_number': '',
        'mobile': '',
        'designation': '',
        'category': 'ALP',
        'lobby': '',
        'custom_fields': {}
    }
    
    cf_map = {cf.field_name.lower(): cf.field_name for cf in (custom_fields or [])}
    cf_label_map = {cf.field_label.lower(): cf.field_name for cf in (custom_fields or [])}

    for col, val in raw_dict.items():
        c_upper = col.upper().replace('_', ' ').replace('.', ' ').strip()
        val_clean = clean_cell_str(val)

        # CLI matching
        if c_upper in ['CLI ID', 'LI ID', 'CLI CODE', 'SUPERVISOR ID']:
            mapped['cli_id'] = val_clean
        elif c_upper in ['CLI NAME', 'LI NAME', 'SUPERVISOR NAME', 'NOMINATED CLI']:
            mapped['cli_name'] = val_clean
        elif c_upper in ['CLI MOBILE', 'LI MOBILE', 'CLI CUG', 'CLI PHONE']:
            mapped['cli_mobile'] = clean_mobile_10(val_clean)

        # Crew details
        elif c_upper in ['CREW NAME', 'STAFF NAME', 'NAME', 'EMPLOYEE NAME']:
            mapped['crew_name'] = val_clean
        elif c_upper in ['CREW MOBILE', 'MOBILE', 'MOBILE NO', 'MOBILE NUMBER', 'CUG', 'CUG NO', 'PHONE']:
            mapped['mobile'] = clean_mobile_10(val_clean)
        elif c_upper in ['PF NUMBER', 'PF NO', 'EMPLOYEE ID', 'EMP ID', 'EMP NO', 'STAFF NO', 'HRMS ID', 'CREW ID']:
            if not mapped['pf_number']:
                mapped['pf_number'] = val_clean
        elif c_upper in ['DESIGNATION', 'DESIG', 'OFFICIAL DESIGNATION']:
            mapped['designation'] = val_clean
        elif c_upper in ['CATEGORY', 'CREW CATEGORY', 'CADRE']:
            cat = val_clean.upper()
            valid_cats = ['LPM', 'LPP', 'MMAN', 'LPG', 'LPS-I', 'LPS-II', 'SALP', 'ALP', 'SR. ALP', 'SR ALP']
            for vc in valid_cats:
                if vc in cat:
                    mapped['category'] = 'SALP' if 'SR' in cat else vc
                    break
            else:
                mapped['category'] = val_clean
        elif c_upper in ['LOBBY', 'HQ', 'HEADQUARTERS', 'DEPOT', 'CREW HQ']:
            mapped['lobby'] = val_clean.upper()
        else:
            # Check dynamic custom fields
            col_lower = col.lower().strip()
            if col_lower in cf_map:
                mapped['custom_fields'][cf_map[col_lower]] = val_clean
            elif col_lower in cf_label_map:
                mapped['custom_fields'][cf_label_map[col_lower]] = val_clean

    if not mapped['category'] and mapped['designation']:
        desig_up = mapped['designation'].upper()
        for vc in ['LPM', 'LPP', 'MMAN', 'LPG', 'LPS-I', 'LPS-II', 'SALP', 'ALP']:
            if vc in desig_up:
                mapped['category'] = vc
                break

    return mapped

def export_crew_master_to_excel(crews, custom_fields=None):
    """
    Exports crew master database to a formatted Excel workbook.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Crew Master Database"
    ws.views.sheetView[0].showGridLines = True

    # Styles
    title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    border_thin = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # Title Block
    ws.merge_cells('A1:L1')
    ws['A1'] = "ELECTRIC OPERATION DEPARTMENT — HOWRAH DIVISION, EASTERN RAILWAY"
    ws['A1'].font = title_font
    ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells('A2:L2')
    ws['A2'] = f"Crew Master Database & Cadre Register — Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    ws['A2'].font = Font(name="Calibri", size=10, italic=True, color="475569")
    ws['A2'].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    # Headers
    headers = [
        "S.No", "CLI ID", "Nominated CLI Name", "CLI Mobile",
        "Crew Name", "Employee ID / PF", "Mobile Number (10-Digit)",
        "Designation", "Crew Category", "Lobby", "Jurisdiction", "Status"
    ]
    cf_keys = []
    if custom_fields:
        for cf in custom_fields:
            if cf.is_active:
                headers.append(cf.field_label)
                cf_keys.append(cf.field_name)

    row_idx = 4
    ws.row_dimensions[row_idx].height = 26
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=row_idx, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border_thin

    # Data Rows
    for s_no, c in enumerate(crews, 1):
        row_idx += 1
        ws.row_dimensions[row_idx].height = 20
        cli_id_str = c.nominated_cli.username if c.nominated_cli else ""
        cli_name_str = c.nominated_cli.full_name if c.nominated_cli else ""
        cli_mob_str = c.nominated_cli.mobile if c.nominated_cli else ""
        lobby_str = c.lobby.code if c.lobby else ""
        status_str = "Active" if c.is_active else "Inactive"

        row_vals = [
            s_no, cli_id_str, cli_name_str, cli_mob_str,
            c.full_name, c.pf_number or "", c.mobile or "",
            c.sub_role or "", c.sub_role or "", lobby_str,
            c.operational_jurisdiction or (c.lobby.operational_jurisdiction if c.lobby else ""),
            status_str
        ]

        # Dynamic custom field values
        cf_data = c.get_custom_fields()
        for k in cf_keys:
            row_vals.append(cf_data.get(k, ""))

        for col_idx, val in enumerate(row_vals, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.border = border_thin
            if s_no % 2 == 0:
                cell.fill = alt_fill
            if col_idx in [1, 2, 4, 6, 7, 9, 10, 12]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    # Auto-fit column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row > 2 and cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# PHASE 4: TRAINING & PERIODICAL MEDICAL EXAMINATION (PME) EXCEL ENGINE
# ---------------------------------------------------------------------------

def parse_excel_date(val):
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
    try:
        f = float(s)
        if f > 30000:
            return (datetime(1899, 12, 30) + timedelta(days=f)).date()
    except Exception:
        pass
    return None


def generate_training_medical_template():
    """Generates formatted Excel template for Weekly Training & PME Bulk Upload."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Training & PME Update"

    # Header styling
    title_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_sample = Font(name="Calibri", size=9, italic=True, color="555555")

    # Title Block
    ws.merge_cells("A1:J1")
    ws["A1"] = "EASTERN RAILWAY - HOWRAH DIVISION (ELECTRIC OPERATION) | WEEKLY TRAINING & PME UPDATE TEMPLATE"
    ws["A1"].font = font_title
    ws["A1"].fill = title_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 30

    headers = [
        "Employee PF / Mobile *",
        "Crew Name",
        "Record Type *",
        "Course / Exam Name *",
        "Institute / Hospital",
        "Last Done Date * (YYYY-MM-DD)",
        "Next Due Date (Auto if blank)",
        "Certificate / Memo No.",
        "Fitness / Result",
        "Remarks"
    ]
    ws.append([]) # blank row 2
    ws.append(headers) # row 3
    ws.row_dimensions[3].height = 24

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=3, column=col_idx)
        cell.font = font_header
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Sample rows demonstrating Refresher ELEC, DSL, GR&SR, ABS, and PME
    sample_rows = [
        ["5020999001", "Ramesh Kumar Sharma", "Training", "Refresher ELEC", "ZRTI Bhuli", "2026-03-15", "", "CERT-ELEC-4401", "Passed", "3-Year validity cycle auto-calculated"],
        ["5020999002", "Anoop Singh", "Training", "Refresher DSL", "ZRTI Bhuli", "2026-04-10", "", "CERT-DSL-3190", "Passed", "Diesel traction cycle"],
        ["5020999001", "Ramesh Kumar Sharma", "Training", "Refresher GR & SR", "ZRTI Bhuli", "2026-05-20", "", "CERT-GRSR-1122", "Passed", "Operating rules refresher"],
        ["5020999003", "Deepak Das", "Training", "Automatic Block System", "DTTC HWH", "2026-08-01", "", "ABS-HWH-882", "Certified", "6-Month validity auto-calculated"],
        ["5020999001", "Ramesh Kumar Sharma", "PME", "Periodic Medical Examination", "Divisional Hospital HWH", "2026-06-12", "", "FIT-A1-90123", "Fit A-One", "Age-based frequency auto-applied"]
    ]

    for r in sample_rows:
        ws.append(r)
        row_idx = ws.max_row
        for col_idx in range(1, len(r) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = font_sample

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def parse_training_medical_excel(file_stream):
    """
    Parses uploaded Weekly Training & PME Excel sheet, matching crew members
    and applying railway validity cycle calculations.
    """
    from models import User, TrainingRecord
    wb = openpyxl.load_workbook(file_stream, data_only=True)
    ws = wb.active

    # Detect header row (contains 'Employee' or 'PF' or 'Course')
    header_row_idx = 3
    for r in range(1, min(10, ws.max_row + 1)):
        row_vals = [clean_cell_str(ws.cell(r, c).value).lower() for c in range(1, min(15, ws.max_column + 1))]
        if any('pf' in v or 'employee' in v or 'mobile' in v for v in row_vals) and any('course' in v or 'exam' in v or 'type' in v for v in row_vals):
            header_row_idx = r
            break

    # Build col map
    col_map = {}
    for c in range(1, ws.max_column + 1):
        val = clean_cell_str(ws.cell(header_row_idx, c).value).lower()
        if 'pf' in val or 'employee' in val or 'mobile' in val or 'staff' in val:
            col_map['identifier'] = c
        elif 'name' in val:
            col_map['crew_name'] = c
        elif 'record' in val and 'type' in val:
            col_map['record_type'] = c
        elif 'course' in val or 'exam' in val or 'training' in val:
            col_map['course_name'] = c
        elif 'institute' in val or 'hospital' in val or 'place' in val:
            col_map['institute'] = c
        elif 'last' in val or 'done' in val:
            col_map['last_done_date'] = c
        elif 'due' in val:
            col_map['due_date'] = c
        elif 'cert' in val or 'memo' in val or 'no' in val:
            col_map['certificate_no'] = c
        elif 'fit' in val or 'result' in val or 'status' in val:
            col_map['status'] = c
        elif 'remark' in val or 'note' in val:
            col_map['remarks'] = c

    parsed_rows = []
    seen_identifiers = set()

    for r in range(header_row_idx + 1, ws.max_row + 1):
        raw_id = clean_cell_str(ws.cell(r, col_map.get('identifier', 1)).value)
        if not raw_id:
            continue

        raw_name = clean_cell_str(ws.cell(r, col_map.get('crew_name', 2)).value)
        rec_type = clean_cell_str(ws.cell(r, col_map.get('record_type', 3)).value) or 'Training'
        course = clean_cell_str(ws.cell(r, col_map.get('course_name', 4)).value)
        institute = clean_cell_str(ws.cell(r, col_map.get('institute', 5)).value)
        raw_done = ws.cell(r, col_map.get('last_done_date', 6)).value
        raw_due = ws.cell(r, col_map.get('due_date', 7)).value
        cert_no = clean_cell_str(ws.cell(r, col_map.get('certificate_no', 8)).value)
        status_val = clean_cell_str(ws.cell(r, col_map.get('status', 9)).value) or 'Passed'
        remarks = clean_cell_str(ws.cell(r, col_map.get('remarks', 10)).value)

        done_date = parse_excel_date(raw_done)
        due_date = parse_excel_date(raw_due)

        # Match Crew in Database
        id_clean = clean_mobile_10(raw_id) or raw_id
        crew_user = User.query.filter(
            (User.mobile == id_clean) |
            (User.pf_number == raw_id) |
            (User.username == raw_id)
        ).first()

        row_errors = []
        if not crew_user:
            row_errors.append(f"No matching crew found for '{raw_id}'")
        if not done_date:
            row_errors.append("Invalid or missing Last Done Date")
        if not course:
            row_errors.append("Course or Exam Name is required")

        # Auto-calculate due date if missing
        is_pme = 'PME' in rec_type.upper() or 'PME' in course.upper() or 'MEDICAL' in course.upper()
        if done_date and not due_date:
            if is_pme and crew_user:
                due_date = crew_user.calculate_next_pme_due(done_date)
            elif is_pme:
                # Default age <= 45 (4 years) if user not found yet
                due_date = done_date.replace(year=done_date.year + 4)
            else:
                due_date = TrainingRecord.calculate_due_date(done_date, course)

        parsed_rows.append({
            'row_num': r,
            'identifier': raw_id,
            'crew_user_id': crew_user.id if crew_user else None,
            'crew_name': crew_user.full_name if crew_user else (raw_name or 'Unknown'),
            'record_type': 'PME' if is_pme else 'Training',
            'course_name': course,
            'institute': institute or ('Divisional Hospital HWH' if is_pme else 'ZRTI Bhuli'),
            'last_done_date': done_date.strftime('%Y-%m-%d') if done_date else '',
            'due_date': due_date.strftime('%Y-%m-%d') if due_date else '',
            'certificate_no': cert_no,
            'status': status_val,
            'remarks': remarks,
            'is_valid': len(row_errors) == 0,
            'errors': row_errors
        })

    return parsed_rows

