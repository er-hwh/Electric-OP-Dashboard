import os

dash_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\admin\dashboard.html"

with open(dash_file, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add CMS dropdown to header
old_header_btns = """            <a href="{{ url_for('admin.important_tools') }}" class="btn btn-danger fw-bold shadow-sm">
                <i class="fa-solid fa-screwdriver-wrench me-1"></i> Important Tools
            </a>"""

new_header_btns = """            <div class="dropdown d-inline-block">
                <button class="btn btn-warning dropdown-toggle fw-bold text-dark shadow-sm" type="button" data-bs-toggle="dropdown">
                    <i class="fa-solid fa-file-pen me-1"></i> Content &amp; CMS Options
                </button>
                <ul class="dropdown-menu shadow">
                    <li><a class="dropdown-item fw-bold text-danger" href="{{ url_for('admin.cms_bulletins') }}"><i class="fa-solid fa-bullhorn me-2 text-danger"></i>Latest Bulletins Upload (PDF)</a></li>
                    <li><a class="dropdown-item fw-bold text-warning" href="{{ url_for('admin.cms_carousel') }}"><i class="fa-solid fa-images me-2 text-warning"></i>Carousel Banner Photos</a></li>
                    <li><a class="dropdown-item fw-bold text-info" href="{{ url_for('admin.cms_pages') }}"><i class="fa-solid fa-file-pen me-2 text-info"></i>Page Content Management (CMS)</a></li>
                    <li><a class="dropdown-item fw-bold text-success" href="{{ url_for('admin.cms_rules') }}"><i class="fa-solid fa-book-bookmark me-2 text-success"></i>Rules &amp; Regulations PDF Upload</a></li>
                    <li><a class="dropdown-item fw-bold text-primary" href="{{ url_for('admin.cms_learning') }}"><i class="fa-solid fa-graduation-cap me-2 text-primary"></i>Learning Materials Content &amp; PDF</a></li>
                </ul>
            </div>
            <a href="{{ url_for('admin.important_tools') }}" class="btn btn-danger fw-bold shadow-sm">
                <i class="fa-solid fa-screwdriver-wrench me-1"></i> Important Tools
            </a>"""

html = html.replace(old_header_btns, new_header_btns)

# 2. Add CMS Options row before Quick Actions
cms_section = """    <!-- CMS & CONTENT MANAGEMENT CARDS -->
    <div class="card border-0 shadow-sm p-3 mb-4 bg-light">
        <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap">
            <div>
                <h5 class="fw-bold text-dark mb-0">
                    <i class="fa-solid fa-cubes text-primary me-2"></i> Content Management System (CMS) &amp; Public Portal Uploads
                </h5>
                <small class="text-muted">Manage homepage banners, latest safety bulletins, rules &amp; regulations PDFs, and technical learning content.</small>
            </div>
            <span class="badge bg-danger">Exclusive Admin Management</span>
        </div>
        <div class="row g-3">
            <!-- 1. Bulletins -->
            <div class="col-lg col-md-4 col-sm-6">
                <div class="card h-100 shadow-sm border-0 border-top border-4 border-danger p-3">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <i class="fa-solid fa-bullhorn text-danger fs-4"></i>
                        <h6 class="fw-bold text-dark mb-0">Latest Bulletins</h6>
                    </div>
                    <p class="small text-muted mb-3 flex-grow-1">Publish safety directives, circulars, and orders with PDF file attachments.</p>
                    <a href="{{ url_for('admin.cms_bulletins') }}" class="btn btn-outline-danger btn-sm fw-bold">
                        <i class="fa-solid fa-upload me-1"></i> Upload Bulletins
                    </a>
                </div>
            </div>
            <!-- 2. Carousel -->
            <div class="col-lg col-md-4 col-sm-6">
                <div class="card h-100 shadow-sm border-0 border-top border-4 border-warning p-3">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <i class="fa-solid fa-images text-warning fs-4"></i>
                        <h6 class="fw-bold text-dark mb-0">Carousel Photos</h6>
                    </div>
                    <p class="small text-muted mb-3 flex-grow-1">Upload high-res promotional &amp; operational banner photos for homepage slider.</p>
                    <a href="{{ url_for('admin.cms_carousel') }}" class="btn btn-outline-warning text-dark btn-sm fw-bold">
                        <i class="fa-solid fa-camera me-1"></i> Manage Photos
                    </a>
                </div>
            </div>
            <!-- 3. CMS Pages -->
            <div class="col-lg col-md-4 col-sm-6">
                <div class="card h-100 shadow-sm border-0 border-top border-4 border-info p-3">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <i class="fa-solid fa-file-pen text-info fs-4"></i>
                        <h6 class="fw-bold text-dark mb-0">Page CMS</h6>
                    </div>
                    <p class="small text-muted mb-3 flex-grow-1">Edit Mission, Vision, Safety Slogans, and Emergency Contact numbers.</p>
                    <a href="{{ url_for('admin.cms_pages') }}" class="btn btn-outline-info btn-sm fw-bold">
                        <i class="fa-solid fa-pen-to-square me-1"></i> Edit CMS Pages
                    </a>
                </div>
            </div>
            <!-- 4. Rules & Regs -->
            <div class="col-lg col-md-4 col-sm-6">
                <div class="card h-100 shadow-sm border-0 border-top border-4 border-success p-3">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <i class="fa-solid fa-book-bookmark text-success fs-4"></i>
                        <h6 class="fw-bold text-dark mb-0">Rules &amp; Regulations</h6>
                    </div>
                    <p class="small text-muted mb-3 flex-grow-1">Upload GR, SR, SWR, and Accident Manuals with direct PDF attachments.</p>
                    <a href="{{ url_for('admin.cms_rules') }}" class="btn btn-outline-success btn-sm fw-bold">
                        <i class="fa-solid fa-file-pdf me-1"></i> Upload Rulebooks
                    </a>
                </div>
            </div>
            <!-- 5. Learning Materials -->
            <div class="col-lg col-md-4 col-sm-6">
                <div class="card h-100 shadow-sm border-0 border-top border-4 border-primary p-3">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <i class="fa-solid fa-graduation-cap text-primary fs-4"></i>
                        <h6 class="fw-bold text-dark mb-0">Learning Materials</h6>
                    </div>
                    <p class="small text-muted mb-3 flex-grow-1">Create loco study guides, rich notes, attach PDFs, and link e-learning tools.</p>
                    <a href="{{ url_for('admin.cms_learning') }}" class="btn btn-outline-primary btn-sm fw-bold">
                        <i class="fa-solid fa-book-open-reader me-1"></i> Manage Learning
                    </a>
                </div>
            </div>
        </div>
    </div>
"""

target_quick_actions = '    <!-- QUICK ACTIONS & RECENT USERS -->'
if "Content Management System (CMS)" not in html:
    html = html.replace(target_quick_actions, cms_section + "\n" + target_quick_actions)

with open(dash_file, 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated templates/admin/dashboard.html successfully.")
