import os

base_file = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\base.html'
with open(base_file, 'r', encoding='utf-8') as f:
    c = f.read()

# Add to Admin
admin_target = '<li><a class="dropdown-item fw-bold text-dark" href="{{ url_for(\'admin.training_medical\') }}"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>Training & PME Management</a></li>'
admin_replacement = admin_target + '''
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('admin.sheets') }}"><i class="fa-solid fa-table-cells me-2 text-success"></i>Google Sheets Hub (Phase 6)</a></li>
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('admin.incidents') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Unusual Incident Tracker (Phase 6)</a></li>'''

# Add to Officer
officer_target = '<li><a class="dropdown-item" href="{{ url_for(\'officer.training_monitor\') }}"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>Training & PME Compliance</a></li>'
officer_replacement = officer_target + '''
                                    <li><a class="dropdown-item" href="{{ url_for('officer.sheets') }}"><i class="fa-solid fa-table-cells me-2 text-success"></i>Google Sheets Hub</a></li>
                                    <li><a class="dropdown-item" href="{{ url_for('officer.incidents') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Unusual Incident Surveillance</a></li>'''

# Add to Control
control_target = '<li><a class="dropdown-item" href="{{ url_for(\'control.training_monitor\') }}"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>Training & PME Compliance</a></li>'
control_replacement = control_target + '''
                                    <li><a class="dropdown-item" href="{{ url_for('control.sheets') }}"><i class="fa-solid fa-table-cells me-2 text-success"></i>Operational Google Sheets</a></li>
                                    <li><a class="dropdown-item" href="{{ url_for('control.incidents') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Shift Unusual Incidents</a></li>'''

# Add to Supervisor
sup_target = '<li><a class="dropdown-item" href="{{ url_for(\'supervisor.training_medical\') }}"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>Squad Training & PME</a></li>'
sup_replacement = sup_target + '''
                                    <li><a class="dropdown-item" href="{{ url_for('supervisor.sheets') }}"><i class="fa-solid fa-table-cells me-2 text-success"></i>CLI Google Sheets</a></li>
                                    <li><a class="dropdown-item" href="{{ url_for('supervisor.incidents') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Squad Unusual Incidents</a></li>'''

# Add to Crew
crew_target = '<li><a class="dropdown-item" href="{{ url_for(\'crew.export_my_pdf\') }}" target="_blank"><i class="fa-solid fa-file-pdf me-2 text-danger"></i>My Bio-Data PDF</a></li>'
crew_replacement = crew_target + '''
                                    <li><a class="dropdown-item" href="{{ url_for('crew.sheets') }}"><i class="fa-solid fa-table-cells me-2 text-success"></i>Running Rosters & Sheets</a></li>
                                    <li><a class="dropdown-item" href="{{ url_for('crew.unusual_reports') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Safety Case Studies & Alerts</a></li>'''

if 'admin.sheets' not in c:
    c = c.replace(admin_target, admin_replacement)
    c = c.replace(officer_target, officer_replacement)
    c = c.replace(control_target, control_replacement)
    c = c.replace(sup_target, sup_replacement)
    c = c.replace(crew_target, crew_replacement)

    with open(base_file, 'w', encoding='utf-8') as f:
        f.write(c)

    print('base.html updated successfully with Phase 6 navigation links!')
else:
    print('base.html already updated with Phase 6 navigation links.')
