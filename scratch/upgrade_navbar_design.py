import os

base_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\base.html"
css_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\static\css\custom.css"

with open(base_file, 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the entire <nav class="navbar ..."> block
old_nav_start = '    <!-- MAIN NAVIGATION MENU -->'
old_nav_end = '    <!-- MANDATORY DEFAULT PASSWORD ALERT BANNER -->'

new_nav_block = """    <!-- MAIN NAVIGATION MENU -->
    <nav class="navbar navbar-expand-xl main-navbar sticky-top">
        <div class="container-fluid px-3 px-xl-4">
            <button class="navbar-toggler my-2 border-primary" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbarMenu" aria-controls="mainNavbarMenu" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="mainNavbarMenu">
                <ul class="navbar-nav me-auto mb-2 mb-xl-0 align-items-xl-center">
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.index' %}active{% endif %}" href="{{ url_for('public.index') }}">
                            <i class="fa-solid fa-house-chimney me-1 text-primary"></i> Home
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle {% if 'learning' in request.endpoint or 'trouble' in request.endpoint or 'quiz' in request.endpoint %}active{% endif %}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-book-open-reader me-1 text-info"></i> Learning Hub
                        </a>
                        <ul class="dropdown-menu shadow border-0">
                            <li><a class="dropdown-item fw-bold" href="{{ url_for('public.learning_materials') }}"><i class="fa-solid fa-layer-group me-2 text-primary"></i>All Learning Materials</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.learning_materials') }}#electric"><i class="fa-solid fa-bolt me-2 text-warning"></i>Electric Traction Handbook</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.learning_materials') }}#diesel"><i class="fa-solid fa-gas-pump me-2 text-danger"></i>Diesel Traction Handbook</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.troubleshooting') }}"><i class="fa-solid fa-screwdriver-wrench me-2 text-danger"></i>Trouble Shooting Guide</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.forms_manual') }}"><i class="fa-solid fa-file-lines me-2 text-secondary"></i>Operating Forms &amp; Authority</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.quiz') }}"><i class="fa-solid fa-award me-2 text-warning"></i>Safety Quiz &amp; Assessment</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item fw-bold text-success" href="https://elearninghwh.in/home_page.html" target="_blank"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>E-Learning Portal (elearninghwh.in) <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                        </ul>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.rules' or request.endpoint == 'elearning.index' %}active{% endif %}" href="{{ url_for('public.rules') }}">
                            <i class="fa-solid fa-book-bookmark me-1 text-success"></i> Rules &amp; Regulations
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.loco_info' %}active{% endif %}" href="{{ url_for('public.loco_info') }}">
                            <i class="fa-solid fa-train me-1 text-primary"></i> Loco Info
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle {% if 'bulletin' in request.endpoint or 'notice' in request.endpoint %}active{% endif %}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-bullhorn me-1 text-warning"></i> Bulletins &amp; Notices
                        </a>
                        <ul class="dropdown-menu shadow border-0">
                            <li><a class="dropdown-item fw-bold" href="{{ url_for('public.bulletins') }}"><i class="fa-solid fa-file-pdf me-2 text-danger"></i>Latest Safety Bulletins</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.notices') }}"><i class="fa-solid fa-bell me-2 text-warning"></i>Divisional Notices &amp; Results</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.instructions') }}"><i class="fa-solid fa-shield-halved me-2 text-info"></i>Safety Instructions &amp; Circulars</a></li>
                        </ul>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.gallery' %}active{% endif %}" href="{{ url_for('public.gallery') }}">
                            <i class="fa-solid fa-camera-retro me-1 text-secondary"></i> Gallery
                        </a>
                    </li>
                </ul>

                {% if current_user %}
                    <div class="d-flex align-items-center gap-2 mt-2 mt-xl-0 flex-nowrap">
                        {% if current_user.is_admin() %}
                            <a href="{{ url_for('admin.dashboard') }}" class="btn btn-danger btn-sm fw-bold shadow-sm py-1 px-3 text-nowrap">
                                <i class="fa-solid fa-gauge-high me-1"></i> Admin Portal
                            </a>
                            <a href="{{ url_for('control.dashboard') }}" class="btn btn-warning btn-sm text-dark fw-bold shadow-sm py-1 px-3 text-nowrap">
                                <i class="fa-solid fa-headset me-1"></i> Control Desk
                            </a>
                        {% elif current_user.is_control() %}
                            <a href="{{ url_for('control.dashboard') }}" class="btn btn-warning btn-sm text-dark fw-bold shadow-sm py-1 px-3 text-nowrap">
                                <i class="fa-solid fa-headset me-1"></i> Control Desk
                            </a>
                            <a href="{{ url_for('control.notice_compliance') }}" class="btn btn-outline-danger btn-sm fw-bold shadow-sm py-1 px-2 text-nowrap">
                                <i class="fa-solid fa-bullhorn me-1"></i> Notices
                            </a>
                        {% elif current_user.is_officer() %}
                            <a href="{{ url_for('officer.dashboard') }}" class="btn btn-primary btn-sm fw-bold shadow-sm py-1 px-3 text-nowrap">
                                <i class="fa-solid fa-shield-halved me-1"></i> Officer Desk
                            </a>
                        {% elif current_user.is_supervisor() %}
                            <a href="{{ url_for('supervisor.dashboard') }}" class="btn btn-info btn-sm text-dark fw-bold shadow-sm py-1 px-3 text-nowrap">
                                <i class="fa-solid fa-clipboard-check me-1"></i> Supervisor Console
                            </a>
                        {% elif current_user.is_crew() %}
                            <a href="{{ url_for('crew.dashboard') }}" class="btn btn-success btn-sm fw-bold shadow-sm py-1 px-3 text-nowrap">
                                <i class="fa-solid fa-id-card me-1"></i> Crew Desk
                            </a>
                        {% endif %}
                    </div>
                {% endif %}
            </div>
        </div>
    </nav>
"""

start_pos = html.find(old_nav_start)
end_pos = html.find(old_nav_end)

if start_pos != -1 and end_pos != -1:
    html = html[:start_pos] + new_nav_block + "\n" + html[end_pos:]
    with open(base_file, 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated templates/base.html navbar.")
else:
    print(f"Could not find boundaries: start_pos={start_pos}, end_pos={end_pos}")

# Now update static/css/custom.css
with open(css_file, 'r', encoding='utf-8') as f:
    css = f.read()

old_nav_css = """.main-navbar {
  background-color: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 0;
}

.main-navbar .nav-link {
  color: var(--ir-blue-dark) !important;
  font-weight: 600;
  padding: 14px 16px !important;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
}

.main-navbar .nav-link:hover,
.main-navbar .nav-link.active {
  color: var(--ir-gold-hover) !important;
  border-bottom-color: var(--ir-gold);
  background-color: rgba(197, 155, 39, 0.05);
}"""

new_nav_css = """.main-navbar {
  background-color: #ffffff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  padding: 0;
  min-height: 52px;
}

.main-navbar .nav-link {
  color: var(--ir-blue-dark) !important;
  font-weight: 600;
  font-size: 0.90rem;
  padding: 14px 12px !important;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
  white-space: nowrap !important;
  display: inline-flex;
  align-items: center;
}

.main-navbar .nav-link:hover,
.main-navbar .nav-link.active {
  color: #0b2545 !important;
  border-bottom-color: var(--ir-gold);
  background-color: rgba(243, 156, 18, 0.08);
}

@media (max-width: 1400px) {
  .main-navbar .nav-link {
    font-size: 0.84rem;
    padding: 14px 8px !important;
  }
}

@media (max-width: 1250px) {
  .main-navbar .nav-link {
    font-size: 0.80rem;
    padding: 14px 6px !important;
  }
}"""

if old_nav_css in css:
    css = css.replace(old_nav_css, new_nav_css)
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(css)
    print("Updated static/css/custom.css navbar rules.")
else:
    print("old_nav_css not exact match, let's append media query rules.")
    # Append fallback
    css += """\n
/* Responsive Navbar Overrides */
.main-navbar .nav-link {
  white-space: nowrap !important;
  font-size: 0.88rem;
  padding: 12px 10px !important;
}
@media (max-width: 1400px) {
  .main-navbar .nav-link {
    font-size: 0.83rem;
    padding: 12px 7px !important;
  }
}
"""
    with open(css_file, 'w', encoding='utf-8') as f:
        f.write(css)
    print("Appended responsive overrides to custom.css.")
