import os

base_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\base.html"

with open(base_file, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update Admin Dropdown with CMS items
old_admin_menu = """                                    <li><a class="dropdown-item fw-bold text-danger" href="{{ url_for('admin.dashboard') }}"><i class="fa-solid fa-gauge-high me-2 text-danger"></i>Admin Console (System Edit)</a></li>
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('admin.crew_master') }}"><i class="fa-solid fa-users-gear me-2 text-primary"></i>Crew Master Database</a></li>"""

new_admin_menu = """                                    <li><a class="dropdown-item fw-bold text-danger" href="{{ url_for('admin.dashboard') }}"><i class="fa-solid fa-gauge-high me-2 text-danger"></i>Admin Console (System Edit)</a></li>
                                    <li><a class="dropdown-item fw-bold text-primary" href="{{ url_for('admin.cms_bulletins') }}"><i class="fa-solid fa-bullhorn me-2 text-danger"></i>Upload Latest Bulletins (PDF)</a></li>
                                    <li><a class="dropdown-item fw-bold text-primary" href="{{ url_for('admin.cms_carousel') }}"><i class="fa-solid fa-images me-2 text-warning"></i>Upload Carousel Banners</a></li>
                                    <li><a class="dropdown-item fw-bold text-primary" href="{{ url_for('admin.cms_pages') }}"><i class="fa-solid fa-file-pen me-2 text-info"></i>Page Content Management (CMS)</a></li>
                                    <li><a class="dropdown-item fw-bold text-primary" href="{{ url_for('admin.cms_rules') }}"><i class="fa-solid fa-book-bookmark me-2 text-success"></i>Upload Rules &amp; Regulations (PDF)</a></li>
                                    <li><a class="dropdown-item fw-bold text-primary" href="{{ url_for('admin.cms_learning') }}"><i class="fa-solid fa-graduation-cap me-2 text-primary"></i>Upload Learning Content &amp; PDF</a></li>
                                    <li><hr class="dropdown-divider"></li>
                                    <li><a class="dropdown-item fw-bold text-dark" href="{{ url_for('admin.crew_master') }}"><i class="fa-solid fa-users-gear me-2 text-primary"></i>Crew Master Database</a></li>"""

html = html.replace(old_admin_menu, new_admin_menu)

# 2. Update Navbar: E-Learning Link in Learning Materials dropdown & Add Important Links dropdown
old_learning_dropdown = """                            <li><a class="dropdown-item" href="{{ url_for('public.instructions') }}"><i class="fa-solid fa-shield-halved me-2 text-info"></i>Safety Instructions & Circulars</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.forms_manual') }}"><i class="fa-solid fa-file-lines me-2 text-secondary"></i>Technical Manuals & Operating Forms</a></li>
                        </ul>"""

new_learning_dropdown = """                            <li><a class="dropdown-item" href="{{ url_for('public.instructions') }}"><i class="fa-solid fa-shield-halved me-2 text-info"></i>Safety Instructions & Circulars</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.forms_manual') }}"><i class="fa-solid fa-file-lines me-2 text-secondary"></i>Technical Manuals & Operating Forms</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item fw-bold text-success" href="https://elearninghwh.in/home_page.html" target="_blank"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>E-Learning Portal (elearninghwh.in) <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                        </ul>"""

html = html.replace(old_learning_dropdown, new_learning_dropdown)

# Add Important Links Dropdown into navbar before the end of ul.navbar-nav
old_nav_end = """                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.notices' %}active{% endif %}" href="{{ url_for('public.notices') }}">
                            <i class="fa-solid fa-bell me-1 text-warning"></i> Notices & Results
                        </a>
                    </li>
                </ul>"""

new_nav_end = """                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.rules' %}active{% endif %}" href="{{ url_for('public.rules') }}">
                            <i class="fa-solid fa-book-bookmark me-1 text-success"></i> Rules &amp; Regulations
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.bulletins' or request.endpoint == 'public.notices' %}active{% endif %}" href="{{ url_for('public.bulletins') }}">
                            <i class="fa-solid fa-bullhorn me-1 text-warning"></i> Latest Bulletins
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle text-warning fw-bold" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-link me-1"></i> Important Links
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end shadow">
                            <li><h6 class="dropdown-header text-primary fw-bold"><i class="fa-solid fa-tower-broadcast me-1"></i>Operational Portals</h6></li>
                            <li><a class="dropdown-item fw-bold" href="https://www.fois.indianrail.gov.in/" target="_blank"><i class="fa-solid fa-train-track me-2 text-primary"></i>FOIS (Freight Operations) <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                            <li><a class="dropdown-item fw-bold" href="https://cois.indianrail.gov.in/" target="_blank"><i class="fa-solid fa-train-subway me-2 text-success"></i>COIS (Coaching Operations) <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                            <li><a class="dropdown-item fw-bold" href="https://rtis.cris.org.in/" target="_blank"><i class="fa-solid fa-satellite-dish me-2 text-danger"></i>RTIS (Real-Time Tracking) <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                            <li><a class="dropdown-item fw-bold" href="https://fois.indianrail.gov.in/SSTS" target="_blank"><i class="fa-solid fa-clock-rotate-left me-2 text-warning"></i>SSTS (Short Stay Tracking) <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="https://cms.indianrail.gov.in" target="_blank"><i class="fa-solid fa-users-gear me-2 text-info"></i>CMS Indian Railways <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                            <li><a class="dropdown-item" href="https://hrms.indianrail.gov.in" target="_blank"><i class="fa-solid fa-id-badge me-2 text-secondary"></i>HRMS Indian Railways <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                            <li><a class="dropdown-item fw-bold text-success" href="https://elearninghwh.in/home_page.html" target="_blank"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>E-Learning Howrah Division <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                        </ul>
                    </li>
                </ul>"""

html = html.replace(old_nav_end, new_nav_end)

# 3. Update Footer with all requested operational & e-learning links
old_footer = """                    <h5 class="footer-heading">Emergency & Portals</h5>
                    <ul class="list-unstyled small text-light mb-0">
                        <li class="mb-1"><i class="fa-solid fa-phone me-2 text-danger"></i><strong>Traction Loco Control (TLC):</strong> 22328</li>
                        <li class="mb-1"><i class="fa-solid fa-phone me-2 text-danger"></i><strong>Power Control (PCNL):</strong> 22666 / 22667</li>
                        <li class="mb-1"><i class="fa-solid fa-link me-2 text-warning"></i><a href="https://cms.indianrail.gov.in" target="_blank" class="text-info text-decoration-none">CMS (Crew Management System)</a></li>
                        <li class="mb-1"><i class="fa-solid fa-link me-2 text-warning"></i><a href="https://hrms.indianrail.gov.in" target="_blank" class="text-info text-decoration-none">HRMS Indian Railways</a></li>
                        <li class="mb-1"><i class="fa-solid fa-link me-2 text-warning"></i><a href="https://fois.indianrail.gov.in" target="_blank" class="text-info text-decoration-none">FOIS (Freight Operating Information System)</a></li>
                    </ul>"""

new_footer = """                    <h5 class="footer-heading">Operational Links &amp; Emergency</h5>
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <a href="https://www.fois.indianrail.gov.in/" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-1" style="font-size:0.78rem;">
                                <i class="fa-solid fa-train-track me-1 text-warning"></i> FOIS
                            </a>
                        </div>
                        <div class="col-6">
                            <a href="https://cois.indianrail.gov.in/" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-1" style="font-size:0.78rem;">
                                <i class="fa-solid fa-train-subway me-1 text-success"></i> COIS
                            </a>
                        </div>
                        <div class="col-6">
                            <a href="https://rtis.cris.org.in/" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-1" style="font-size:0.78rem;">
                                <i class="fa-solid fa-satellite-dish me-1 text-danger"></i> RTIS
                            </a>
                        </div>
                        <div class="col-6">
                            <a href="https://fois.indianrail.gov.in/SSTS" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-1" style="font-size:0.78rem;">
                                <i class="fa-solid fa-clock-rotate-left me-1 text-info"></i> SSTS
                            </a>
                        </div>
                    </div>
                    <ul class="list-unstyled small text-light mb-0">
                        <li class="mb-1"><i class="fa-solid fa-graduation-cap me-2 text-success"></i><a href="https://elearninghwh.in/home_page.html" target="_blank" class="text-warning text-decoration-none fw-bold">E-Learning Portal (elearninghwh.in)</a></li>
                        <li class="mb-1"><i class="fa-solid fa-phone me-2 text-danger"></i><strong>TLC:</strong> 22328 &bull; <strong>PCNL:</strong> 22666 / 22667</li>
                        <li class="mb-0"><i class="fa-solid fa-link me-2 text-warning"></i><a href="https://cms.indianrail.gov.in" target="_blank" class="text-info text-decoration-none me-2">CMS</a> | <a href="https://hrms.indianrail.gov.in" target="_blank" class="text-info text-decoration-none">HRMS</a></li>
                    </ul>"""

html = html.replace(old_footer, new_footer)

with open(base_file, 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated templates/base.html successfully.")
