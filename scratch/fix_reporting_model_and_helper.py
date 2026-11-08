import os
import sys

base_dir = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard'

# 1. Update models.py
models_path = os.path.join(base_dir, 'models.py')
with open(models_path, 'r', encoding='utf-8') as f:
    models_code = f.read()

properties_code = '''
    # -----------------------------------------------------------------------
    # PHASE 7: CREW ACCESSOR PROPERTIES
    # -----------------------------------------------------------------------
    @property
    def crew_category(self):
        return self.sub_role or ''

    @crew_category.setter
    def crew_category(self, val):
        self.sub_role = val

    @property
    def assigned_cli_id(self):
        return self.cli_id

    @property
    def assigned_cli(self):
        if self.cli_id:
            return User.query.get(self.cli_id)
        return None

    @property
    def phone(self):
        return self.mobile

    @property
    def emp_no(self):
        return self.pf_number

    @property
    def dob(self):
        return self.date_of_birth

    @property
    def traction_type(self):
        c = self.get_custom_fields()
        return c.get('traction_type', 'BOTH')

    @property
    def safety_grading(self):
        c = self.get_custom_fields()
        return c.get('safety_grading', 'UNGRADED')

    @safety_grading.setter
    def safety_grading(self, val):
        self.set_custom_field('safety_grading', val)

    @property
    def remarks(self):
        c = self.get_custom_fields()
        return c.get('remarks', '')

    @remarks.setter
    def remarks(self, val):
        self.set_custom_field('remarks', val)
'''

if 'def crew_category(self):' not in models_code:
    target = '    def can_edit_system(self):'
    models_code = models_code.replace(target, properties_code + '\n    def can_edit_system(self):')
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(models_code)
    print("models.py updated with crew accessor properties.")
else:
    print("models.py already has crew accessor properties.")

# 2. Update blueprints/reporting_helper.py
helper_path = os.path.join(base_dir, 'blueprints', 'reporting_helper.py')
new_helper_code = '''import io
import csv
from datetime import date, datetime, timedelta
from collections import defaultdict
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from database import db
from models import User, Lobby, TrainingRecord, MedicalRecord, CrewCounsellingLog, CrewCounsellingRecord

def get_crew_overview_stats():
    """Calculates overall division running staff statistics."""
    crews = User.query.filter_by(role='crew').all()
    total_count = len(crews)
    active_count = sum(1 for c in crews if c.is_active)
    inactive_count = total_count - active_count

    # Category breakdown (LPM, LPP, MMAN, LPG, LPS-I, LPS-II, SALP, ALP)
    categories = ['LPM', 'LPP', 'MMAN', 'LPG', 'LPS-I', 'LPS-II', 'SALP', 'ALP']
    category_counts = {cat: 0 for cat in categories}
    other_cat_count = 0
    for c in crews:
        cat = (c.crew_category or c.sub_role or '').strip().upper()
        if cat in category_counts:
            category_counts[cat] += 1
        elif 'LPS' in cat and ('1' in cat or 'I' in cat):
            category_counts['LPS-I'] += 1
        elif 'LPS' in cat and ('2' in cat or 'II' in cat):
            category_counts['LPS-II'] += 1
        elif 'SALP' in cat or 'SR. ALP' in cat or 'SR.ALP' in cat:
            category_counts['SALP'] += 1
        elif cat:
            other_cat_count += 1
        else:
            other_cat_count += 1

    # Traction breakdown
    traction_counts = {'ELECTRIC': 0, 'DIESEL': 0, 'BOTH': 0}
    for c in crews:
        tr = (c.traction_type or 'BOTH').strip().upper()
        if tr in traction_counts:
            traction_counts[tr] += 1
        else:
            traction_counts['BOTH'] += 1

    # Safety grading (A, B, C)
    grading_counts = {'A': 0, 'B': 0, 'C': 0, 'UNGRADED': 0}
    for c in crews:
        gr = (c.safety_grading or 'UNGRADED').strip().upper()
        if gr in grading_counts:
            grading_counts[gr] += 1
        else:
            grading_counts['UNGRADED'] += 1

    return {
        'total_count': total_count,
        'active_count': active_count,
        'inactive_count': inactive_count,
        'category_counts': category_counts,
        'other_cat_count': other_cat_count,
        'traction_counts': traction_counts,
        'grading_counts': grading_counts
    }


def get_cli_crew_matrix():
    """Generates CLI-wise supervisory matrix with assigned crews and categories."""
    clis = User.query.filter_by(role='supervisor').order_by(User.full_name.asc()).all()
    crews = User.query.filter_by(role='crew').all()

    cli_crews_map = defaultdict(list)
    unassigned_crews = []
    for c in crews:
        if c.cli_id:
            cli_crews_map[c.cli_id].append(c)
        else:
            unassigned_crews.append(c)

    matrix = []
    for cli in clis:
        assigned = cli_crews_map.get(cli.id, [])
        cat_dist = defaultdict(int)
        grade_dist = defaultdict(int)
        for cr in assigned:
            cat = (cr.crew_category or cr.sub_role or 'OTHER').strip().upper()
            cat_dist[cat] += 1
            gr = (cr.safety_grading or 'U').strip().upper()
            grade_dist[gr] += 1

        matrix.append({
            'cli': cli,
            'total_crews': len(assigned),
            'lobby': cli.lobby.code if cli.lobby else 'N/A',
            'cat_dist': dict(cat_dist),
            'grade_a': grade_dist['A'],
            'grade_b': grade_dist['B'],
            'grade_c': grade_dist['C']
        })

    return {
        'matrix': matrix,
        'unassigned_count': len(unassigned_crews)
    }


def get_lobby_crew_matrix():
    """Generates lobby-wise deployment matrix across all 12 HWH division lobbies."""
    lobbies = Lobby.query.order_by(Lobby.code.asc()).all()
    crews = User.query.filter_by(role='crew').all()

    lobby_crews_map = defaultdict(list)
    unassigned_lobby = []
    for c in crews:
        if c.lobby_id:
            lobby_crews_map[c.lobby_id].append(c)
        else:
            unassigned_lobby.append(c)

    sister_lobbies_codes = {'NHT', 'SNT', 'KURV'}

    matrix = []
    for lob in lobbies:
        assigned = lobby_crews_map.get(lob.id, [])
        cat_dist = defaultdict(int)
        for cr in assigned:
            cat = (cr.crew_category or cr.sub_role or 'OTHER').strip().upper()
            cat_dist[cat] += 1

        is_sister = lob.is_sister_lobby or (lob.code in sister_lobbies_codes)
        in_charge = lob.in_charge_cli.full_name if lob.in_charge_cli else 'Unassigned'

        matrix.append({
            'lobby': lob,
            'is_sister': is_sister,
            'in_charge': in_charge,
            'total_crews': len(assigned),
            'cat_dist': dict(cat_dist)
        })

    return {
        'matrix': matrix,
        'unassigned_count': len(unassigned_lobby)
    }


def filter_crews_query(lobby_id=None, cli_id=None, category=None, traction=None,
                       grading=None, search=None, active_only=True):
    """Constructs dynamic SQLAlchemy query for filtering crews."""
    query = User.query.filter_by(role='crew')
    if active_only:
        query = query.filter_by(is_active=True)

    if lobby_id and str(lobby_id).upper() != 'ALL':
        try:
            query = query.filter_by(lobby_id=int(lobby_id))
        except ValueError:
            pass

    if cli_id and str(cli_id).upper() != 'ALL':
        try:
            query = query.filter_by(cli_id=int(cli_id))
        except ValueError:
            pass

    if category and str(category).upper() != 'ALL':
        query = query.filter(User.sub_role.ilike(f'%{category.strip()}%'))

    if search:
        s = f'%{search.strip()}%'
        query = query.filter(
            db.or_(
                User.full_name.ilike(s),
                User.username.ilike(s),
                User.pf_number.ilike(s),
                User.hrms_id.ilike(s),
                User.mobile.ilike(s)
            )
        )

    return query.order_by(User.full_name.asc())


def export_crews_to_excel(crews):
    """Exports list of crew objects to a styled Excel (.xlsx) workbook."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Crew Master Report"

    title_font = Font(name='Calibri', size=14, bold=True, color='FFFFFF')
    title_fill = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')
    header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    header_fill = PatternFill(start_color='2563EB', end_color='2563EB', fill_type='solid')
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    ws.merge_cells('A1:L1')
    title_cell = ws['A1']
    title_cell.value = f"ELECTRIC OPERATION DEPARTMENT - HOWRAH DIVISION - CREW MASTER REPORT (Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')})"
    title_cell.font = title_font
    title_cell.fill = title_fill
    title_cell.alignment = center_align
    ws.row_dimensions[1].height = 32

    headers = [
        "Sl No", "Crew ID / Mobile", "Emp No / HRMS ID", "Full Name",
        "Category", "Home Lobby", "Assigned CLI", "Traction",
        "Safety Grading", "Date of Birth", "PME Due Date", "Status"
    ]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border
    ws.row_dimensions[2].height = 24

    for row_idx, crew in enumerate(crews, 3):
        pme_due = crew.pme_due_date.strftime('%d-%m-%Y') if hasattr(crew, 'pme_due_date') and crew.pme_due_date else 'N/A'
        dob = crew.dob.strftime('%d-%m-%Y') if hasattr(crew, 'dob') and crew.dob else 'N/A'
        status_str = "ACTIVE" if crew.is_active else "INACTIVE"
        cli_name = crew.assigned_cli.full_name if crew.assigned_cli else "Unassigned"
        lobby_name = crew.lobby.code if crew.lobby else "N/A"

        row_data = [
            row_idx - 2,
            crew.username,
            crew.emp_no or crew.hrms_id or 'N/A',
            crew.full_name,
            crew.crew_category or 'N/A',
            lobby_name,
            cli_name,
            crew.traction_type or 'BOTH',
            crew.safety_grading or 'N/A',
            dob,
            pme_due,
            status_str
        ]

        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = Font(name='Calibri', size=10)
            cell.border = thin_border
            if col_idx in (1, 2, 5, 6, 8, 9, 10, 11, 12):
                cell.alignment = center_align
            else:
                cell.alignment = left_align

        ws.row_dimensions[row_idx].height = 20

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def export_crews_to_csv(crews):
    """Exports list of crew objects to standard CSV buffer."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Sl No", "Crew ID (Mobile)", "Emp No", "HRMS ID", "Full Name",
        "Category", "Home Lobby", "Assigned CLI", "Traction",
        "Safety Grading", "DOB", "PME Due Date", "Status"
    ])
    for idx, c in enumerate(crews, 1):
        pme_due = c.pme_due_date.strftime('%d-%m-%Y') if hasattr(c, 'pme_due_date') and c.pme_due_date else ''
        dob = c.dob.strftime('%d-%m-%Y') if hasattr(c, 'dob') and c.dob else ''
        writer.writerow([
            idx,
            c.username,
            c.emp_no or '',
            c.hrms_id or '',
            c.full_name,
            c.crew_category or '',
            c.lobby.code if c.lobby else '',
            c.assigned_cli.full_name if c.assigned_cli else '',
            c.traction_type or 'BOTH',
            c.safety_grading or '',
            dob,
            pme_due,
            "ACTIVE" if c.is_active else "INACTIVE"
        ])
    buf.seek(0)
    return buf
'''

with open(helper_path, 'w', encoding='utf-8') as f:
    f.write(new_helper_code)
print("reporting_helper.py updated successfully.")
