with open(r'templates\base.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = """    <!-- MAIN NAVIGATION MENU -->
    <nav class="navbar navbar-expand-lg main-navbar sticky-top">
        <div class="container-fluid px-4">
            <button class="navbar-toggler my-2" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbarMenu" aria-controls="mainNavbarMenu" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="mainNavbarMenu">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.index' %}active{% endif %}" href="{{ url_for('public.index') }}">
                            <i class="fa-solid fa-house-chimney me-1 text-primary"></i> Home
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle {% if 'learning' in request.endpoint %}active{% endif %}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-book-open-reader me-1 text-info"></i> Learning Materials
                        </a>
                        <ul class="dropdown-menu shadow">
                            <li><a class="dropdown-item fw-bold" href="{{ url_for('public.learning_materials') }}"><i class="fa-solid fa-layer-group me-2 text-primary"></i>All Learning Materials</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.learning_materials') }}#electric"><i class="fa-solid fa-bolt me-2 text-warning"></i>Electric Traction</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.learning_materials') }}#diesel"><i class="fa-solid fa-gas-pump me-2 text-danger"></i>Diesel Traction</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.index') }}"><i class="fa-solid fa-scale-balanced me-2 text-success"></i>Railway Transportation Rules (GR & SR)</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.instructions') }}"><i class="fa-solid fa-shield-halved me-2 text-info"></i>Safety Instructions & Circulars</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.forms_manual') }}"><i class="fa-solid fa-file-lines me-2 text-secondary"></i>Technical Manuals & Operating Forms</a></li>
                        </ul>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'elearning.quiz' %}active{% endif %}" href="{{ url_for('elearning.quiz') }}">
                            <i class="fa-solid fa-award me-1 text-warning"></i> Quiz & Assessment
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.loco_info' %}active{% endif %}" href="{{ url_for('public.loco_info') }}">
                            <i class="fa-solid fa-train me-1 text-primary"></i> Loco Information
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'elearning.index' %}active{% endif %}" href="{{ url_for('elearning.index') }}">
                            <i class="fa-solid fa-scale-balanced me-1 text-success"></i> Rules & Regulations
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'elearning.troubleshooting' %}active{% endif %}" href="{{ url_for('elearning.troubleshooting') }}">
                            <i class="fa-solid fa-wrench me-1 text-danger"></i> Trouble Shooting Guide
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.gallery' %}active{% endif %}" href="{{ url_for('public.gallery') }}">
                            <i class="fa-solid fa-camera-retro me-1 text-secondary"></i> Photo Gallery
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.notices' %}active{% endif %}" href="{{ url_for('public.notices') }}">
                            <i class="fa-solid fa-bell me-1 text-warning"></i> Notices & Results
                        </a>
                    </li>
                </ul>"""

replacement = """    <!-- MAIN NAVIGATION MENU -->
    <nav class="navbar navbar-expand-xl main-navbar sticky-top">
        <div class="container-fluid px-4">
            <button class="navbar-toggler my-2" type="button" data-bs-toggle="collapse" data-bs-target="#mainNavbarMenu" aria-controls="mainNavbarMenu" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="mainNavbarMenu">
                <ul class="navbar-nav me-auto mb-2 mb-xl-0">
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.index' %}active{% endif %}" href="{{ url_for('public.index') }}">
                            <i class="fa-solid fa-house-chimney me-1 text-primary"></i> Home
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle {% if 'learning' in request.endpoint or 'instructions' in request.endpoint %}active{% endif %}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-book-open-reader me-1 text-info"></i> Learning Materials
                        </a>
                        <ul class="dropdown-menu shadow">
                            <li><a class="dropdown-item fw-bold" href="{{ url_for('public.learning_materials') }}"><i class="fa-solid fa-layer-group me-2 text-primary"></i>All Learning Materials</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.learning_materials') }}#electric"><i class="fa-solid fa-bolt me-2 text-warning"></i>Electric Traction (3-Phase &amp; Conventional)</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.learning_materials') }}#diesel"><i class="fa-solid fa-gas-pump me-2 text-danger"></i>Diesel Traction (EMD HHP &amp; ALCO)</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.instructions') }}"><i class="fa-solid fa-shield-halved me-2 text-info"></i>Safety Instructions &amp; Circulars</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.forms_manual') }}"><i class="fa-solid fa-file-lines me-2 text-secondary"></i>Technical Manuals &amp; Operating Forms</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item fw-bold text-success" href="https://elearninghwh.in/home_page.html" target="_blank"><i class="fa-solid fa-graduation-cap me-2 text-success"></i>Official Division E-Learning Portal <i class="fa-solid fa-arrow-up-right-from-square ms-1 small"></i></a></li>
                        </ul>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle {% if 'loco' in request.endpoint or 'haulage' in request.endpoint %}active{% endif %}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-train me-1 text-primary"></i> Loco Info &amp; Haulage
                        </a>
                        <ul class="dropdown-menu shadow">
                            <li><a class="dropdown-item fw-bold" href="{{ url_for('public.loco_info') }}"><i class="fa-solid fa-circle-info me-2 text-primary"></i>Locomotive Specifications &amp; Technical Directory</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item fw-bold text-primary" href="{{ url_for('public.haulage_capacity') }}"><i class="fa-solid fa-gauge-high me-2 text-danger"></i>⚡ Electric Hauling Capacity Calculator (RDSO 2016)</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.haulage_capacity') }}#tab-wag12"><i class="fa-solid fa-train-subway me-2 text-warning"></i>WAG-12B (12000 HP) Heavy Haul &amp; Momentum Tables</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.loco_info') }}#electric-locos"><i class="fa-solid fa-bolt me-2 text-warning"></i>Electric Locos (WAG-12B, WAG-9, WAP-7, WAG-7)</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.loco_info') }}#diesel-locos"><i class="fa-solid fa-gas-pump me-2 text-danger"></i>Diesel Locos (WDP-4D, WDG-4, WDM-3D)</a></li>
                        </ul>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'elearning.index' %}active{% endif %}" href="{{ url_for('elearning.index') }}">
                            <i class="fa-solid fa-scale-balanced me-1 text-success"></i> Rules &amp; Regulations
                        </a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle {% if 'trouble' in request.endpoint or 'quiz' in request.endpoint or 'gallery' in request.endpoint %}active{% endif %}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-toolbox me-1 text-warning"></i> Operations &amp; Safety
                        </a>
                        <ul class="dropdown-menu shadow">
                            <li><a class="dropdown-item fw-bold" href="{{ url_for('elearning.troubleshooting') }}"><i class="fa-solid fa-wrench me-2 text-danger"></i>Trouble Shooting Guide &amp; Fault Directory</a></li>
                            <li><a class="dropdown-item" href="{{ url_for('elearning.quiz') }}"><i class="fa-solid fa-award me-2 text-warning"></i>Safety Quiz &amp; Knowledge Assessment</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="{{ url_for('public.gallery') }}"><i class="fa-solid fa-camera-retro me-2 text-secondary"></i>Division Photo &amp; Event Gallery</a></li>
                        </ul>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.endpoint == 'public.notices' %}active{% endif %}" href="{{ url_for('public.notices') }}">
                            <i class="fa-solid fa-bell me-1 text-danger"></i> Notices &amp; Bulletins
                        </a>
                    </li>
                </ul>"""

assert target in html, "target navbar not found in base.html"
html = html.replace(target, replacement, 1)

with open(r'templates\base.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("[OK] templates/base.html navbar updated successfully!")
