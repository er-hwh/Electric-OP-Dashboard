import os
import sys

base_dir = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard'
sys.path.insert(0, base_dir)

# ---------------------------------------------------------------------------
# 1. Update blueprints/officer.py
# ---------------------------------------------------------------------------
officer_path = os.path.join(base_dir, 'blueprints', 'officer.py')
with open(officer_path, 'r', encoding='utf-8') as f:
    officer_code = f.read()

# Check imports in officer.py
if 'from flask import' in officer_code and 'send_file' not in officer_code:
    officer_code = officer_code.replace('from flask import ', 'from flask import send_file, Response, ')

if 'from blueprints.reporting_helper import' not in officer_code:
    officer_code = '''from blueprints.reporting_helper import (
    get_crew_overview_stats, get_cli_crew_matrix, get_lobby_crew_matrix,
    filter_crews_query, export_crews_to_excel, export_crews_to_csv
)\n''' + officer_code

phase7_officer_code = '''

# ---------------------------------------------------------------------------
# PHASE 7: OFFICER ADVANCED REPORTING SUITE & EXPORT ANALYTICS
# ---------------------------------------------------------------------------

@officer_bp.route('/reports', methods=['GET'])
def reports():
    """Advanced Multi-Parameter Filtered Reports & Analytics Suite."""
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

    # Query filtered crews
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
        export_base_url=url_for('officer.reports'),
        is_officer_view=True
    )


@officer_bp.route('/reports/export/excel', methods=['GET'])
def export_reports_excel():
    """Download filtered crew records as styled Excel (.xlsx)."""
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
        download_name=f"HWH_Crew_Master_Report_{ts}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@officer_bp.route('/reports/export/csv', methods=['GET'])
def export_reports_csv():
    """Download filtered crew records as standard CSV."""
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
        headers={"Content-Disposition": f"attachment; filename=HWH_Crew_Report_{ts}.csv"}
    )


@officer_bp.route('/crew/<int:crew_id>/remark', methods=['POST'])
def add_crew_remark(crew_id):
    """Add supervisory / performance remark on a running crew."""
    crew = User.query.get_or_404(crew_id)
    remark = request.form.get('officer_remark', '').strip()
    grading = request.form.get('safety_grading', '').strip()
    officer = User.query.get(session.get('user_id'))
    officer_name = officer.full_name if officer else "Officer"

    if grading in ('A', 'B', 'C'):
        crew.safety_grading = grading

    if remark:
        existing = crew.remarks or ''
        ts_str = datetime.now().strftime('%d-%m-%Y %H:%M')
        crew.remarks = f"{existing}\\n[{ts_str} - {officer_name}]: {remark}".strip()

    db.session.commit()
    flash(f'Observation recorded for {crew.full_name}.', 'success')
    return redirect(url_for('officer.reports', tab='filter'))
'''

if 'def reports():' not in officer_code:
    officer_code = officer_code + phase7_officer_code
    with open(officer_path, 'w', encoding='utf-8') as f:
        f.write(officer_code)
    print("blueprints/officer.py updated with Phase 7.")
else:
    print("blueprints/officer.py already has reports routes.")


# ---------------------------------------------------------------------------
# 2. Update blueprints/control.py
# ---------------------------------------------------------------------------
control_path = os.path.join(base_dir, 'blueprints', 'control.py')
with open(control_path, 'r', encoding='utf-8') as f:
    control_code = f.read()

if 'from blueprints.reporting_helper import' not in control_code:
    control_code = '''from blueprints.reporting_helper import (
    get_crew_overview_stats, get_cli_crew_matrix, get_lobby_crew_matrix,
    filter_crews_query, export_crews_to_excel, export_crews_to_csv
)\n''' + control_code

phase7_control_code = '''

# ---------------------------------------------------------------------------
# PHASE 7: CONTROL (TLC / PCNL) IMPORTANT TOOLS & OPERATIONAL REPORTS
# ---------------------------------------------------------------------------

@control_bp.route('/important-tools')
@control_login_required
def important_tools():
    """TLC / PCNL Control Operational Tools Suite."""
    return render_template('control/important_tools.html')


@control_bp.route('/reports', methods=['GET'])
@control_login_required
def reports():
    """Operational Reports Desk with Full Sr. DEE(OP) Parity."""
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
        export_base_url=url_for('control.reports'),
        is_control_view=True
    )


@control_bp.route('/reports/export/excel', methods=['GET'])
@control_login_required
def export_reports_excel():
    """Download filtered crew records as styled Excel (.xlsx) by Control."""
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
    ts = dt.now().strftime('%Y%m%d_%H%M%S')
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"Control_Crew_Report_{ts}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@control_bp.route('/reports/export/csv', methods=['GET'])
@control_login_required
def export_reports_csv():
    """Download filtered crew records as standard CSV by Control."""
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
    ts = dt.now().strftime('%Y%m%d_%H%M%S')
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Control_Crew_Report_{ts}.csv"}
    )


@control_bp.route('/crew/<int:crew_id>/remark', methods=['POST'])
@control_login_required
def add_crew_remark(crew_id):
    """Add shift controller remark on running crew."""
    crew = User.query.get_or_404(crew_id)
    remark = request.form.get('officer_remark', '').strip()
    user = User.query.get(session.get('user_id'))
    role_str = "TLC" if user and user.is_tlc() else ("PCNL" if user and user.is_pcnl() else "Control")

    if remark:
        existing = crew.remarks or ''
        ts_str = dt.now().strftime('%d-%m-%Y %H:%M')
        crew.remarks = f"{existing}\\n[{ts_str} - {role_str} Shift Note]: {remark}".strip()
        db.session.commit()
        flash(f'Shift observation logged for {crew.full_name}.', 'success')

    return redirect(url_for('control.reports', tab='filter'))
'''

if 'def important_tools():' not in control_code:
    control_code = control_code + phase7_control_code
    with open(control_path, 'w', encoding='utf-8') as f:
        f.write(control_code)
    print("blueprints/control.py updated with Phase 7.")
else:
    print("blueprints/control.py already has important_tools.")


# ---------------------------------------------------------------------------
# 3. Update blueprints/admin.py
# ---------------------------------------------------------------------------
admin_path = os.path.join(base_dir, 'blueprints', 'admin.py')
with open(admin_path, 'r', encoding='utf-8') as f:
    admin_code = f.read()

if 'from blueprints.reporting_helper import' not in admin_code:
    admin_code = '''from blueprints.reporting_helper import (
    get_crew_overview_stats, get_cli_crew_matrix, get_lobby_crew_matrix,
    filter_crews_query, export_crews_to_excel, export_crews_to_csv
)\n''' + admin_code

phase7_admin_code = '''

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
        crew.remarks = f"{existing}\\n[{ts_str} - Admin Note]: {remark}".strip()

    db.session.commit()
    flash(f'Observation recorded for {crew.full_name}.', 'success')
    return redirect(url_for('admin.reports', tab='filter'))
'''

if 'def reports():' not in admin_code:
    admin_code = admin_code + phase7_admin_code
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(admin_code)
    print("blueprints/admin.py updated with Phase 7.")
else:
    print("blueprints/admin.py already has reports.")

print("All Phase 7 backend updates applied!")
