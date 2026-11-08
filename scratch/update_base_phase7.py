import os

base_file = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\base.html'
with open(base_file, 'r', encoding='utf-8') as f:
    c = f.read()

# Add to Admin
admin_target = '<li><a class="dropdown-item fw-bold text-dark" href="{{ url_for(\'admin.incidents\') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Unusual Incident Tracker (Phase 6)</a></li>'
admin_replacement = admin_target + '''
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('admin.reports') }}"><i class="fa-solid fa-chart-pie me-2 text-primary"></i>Division Reports & Analytics (Phase 7)</a></li>'''

# Add to Officer
officer_target = '<li><a class="dropdown-item" href="{{ url_for(\'officer.incidents\') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Unusual Incident Surveillance</a></li>'
officer_replacement = officer_target + '''
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('officer.reports') }}"><i class="fa-solid fa-chart-pie me-2 text-primary"></i>Division Reports & Analytics (Phase 7)</a></li>'''

# Add to Control
control_target = '<li><a class="dropdown-item" href="{{ url_for(\'control.incidents\') }}"><i class="fa-solid fa-triangle-exclamation me-2 text-danger"></i>Shift Unusual Incidents</a></li>'
control_replacement = control_target + '''
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('control.important_tools') }}"><i class="fa-solid fa-screwdriver-wrench me-2 text-warning"></i>Important Operational Tools</a></li>
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('control.reports') }}"><i class="fa-solid fa-chart-pie me-2 text-primary"></i>Operational Filtered Reports</a></li>'''

if 'admin.reports' not in c:
    c = c.replace(admin_target, admin_replacement)
    c = c.replace(officer_target, officer_replacement)
    c = c.replace(control_target, control_replacement)

    with open(base_file, 'w', encoding='utf-8') as f:
        f.write(c)
    print("templates/base.html updated with Phase 7 navigation links.")
else:
    print("templates/base.html already has Phase 7 navigation links.")
