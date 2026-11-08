import os

base_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\base.html"

with open(base_file, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Remove Important Links dropdown from top menu
old_top_links = """                    <li class="nav-item dropdown">
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
                    </li>"""

html = html.replace(old_top_links, "")

# 2. Add global Important Links bar below main content right before footer
links_strip = """    <!-- IMPORTANT OPERATIONAL LINKS BAR (BELOW MAIN CONTENT) -->
    <section class="bg-dark text-white py-3 border-top border-warning border-3">
        <div class="container-fluid px-4">
            <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap">
                <div>
                    <h6 class="fw-bold text-warning mb-0">
                        <i class="fa-solid fa-tower-broadcast me-2"></i> IMPORTANT OPERATIONAL LINKS &amp; RAILWAY PORTALS
                    </h6>
                    <small class="text-secondary">Quick access to essential Indian Railways operations, tracking, and learning systems</small>
                </div>
            </div>
            <div class="row g-2">
                <div class="col-xl-2 col-md-4 col-6">
                    <a href="https://www.fois.indianrail.gov.in/" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-2 d-flex align-items-center justify-content-between">
                        <span><i class="fa-solid fa-train-track me-2 text-warning"></i><strong>FOIS</strong></span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-secondary small"></i>
                    </a>
                </div>
                <div class="col-xl-2 col-md-4 col-6">
                    <a href="https://cois.indianrail.gov.in/" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-2 d-flex align-items-center justify-content-between">
                        <span><i class="fa-solid fa-train-subway me-2 text-success"></i><strong>COIS</strong></span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-secondary small"></i>
                    </a>
                </div>
                <div class="col-xl-2 col-md-4 col-6">
                    <a href="https://rtis.cris.org.in/" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-2 d-flex align-items-center justify-content-between">
                        <span><i class="fa-solid fa-satellite-dish me-2 text-danger"></i><strong>RTIS</strong></span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-secondary small"></i>
                    </a>
                </div>
                <div class="col-xl-2 col-md-4 col-6">
                    <a href="https://fois.indianrail.gov.in/SSTS" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-2 d-flex align-items-center justify-content-between">
                        <span><i class="fa-solid fa-clock-rotate-left me-2 text-info"></i><strong>SSTS</strong></span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-secondary small"></i>
                    </a>
                </div>
                <div class="col-xl-2 col-md-4 col-6">
                    <a href="https://elearninghwh.in/home_page.html" target="_blank" class="btn btn-warning text-dark btn-sm w-100 text-start py-2 d-flex align-items-center justify-content-between fw-bold">
                        <span><i class="fa-solid fa-graduation-cap me-2 text-dark"></i><strong>E-Learning</strong></span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-dark small"></i>
                    </a>
                </div>
                <div class="col-xl-2 col-md-4 col-6">
                    <a href="https://cms.indianrail.gov.in" target="_blank" class="btn btn-outline-light btn-sm w-100 text-start py-2 d-flex align-items-center justify-content-between">
                        <span><i class="fa-solid fa-users-gear me-2 text-primary"></i><strong>CMS</strong></span>
                        <i class="fa-solid fa-arrow-up-right-from-square text-secondary small"></i>
                    </a>
                </div>
            </div>
        </div>
    </section>
"""

target_footer = '    <!-- OFFICIAL RAILWAY FOOTER -->'
if "IMPORTANT OPERATIONAL LINKS BAR (BELOW MAIN CONTENT)" not in html:
    html = html.replace(target_footer, links_strip + "\n" + target_footer)

with open(base_file, 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated templates/base.html: removed Important Links from top menu and positioned all links below.")
