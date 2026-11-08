import os

index_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\templates\public\index.html"

with open(index_file, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update ticker to show bulletins or notices
old_ticker = """        <div class="ticker-content">
            <marquee behavior="scroll" direction="left" onmouseover="this.stop();" onmouseout="this.start();">
                {% for n in notices %}
                    <span class="me-4">
                        <span class="badge bg-danger me-1">NEW</span>
                        <a href="{{ url_for('public.notices') }}" class="text-dark fw-bold text-decoration-none">
                            [{{ n.category }}] {{ n.title }} ({{ n.created_at.strftime('%d-%b-%Y') }})
                        </a>
                        &bull;
                    </span>
                {% endfor %}
            </marquee>
        </div>"""

new_ticker = """        <div class="ticker-content">
            <marquee behavior="scroll" direction="left" onmouseover="this.stop();" onmouseout="this.start();">
                {% if bulletins %}
                    {% for b in bulletins %}
                        <span class="me-4">
                            <span class="badge bg-danger me-1">BULLETIN</span>
                            <a href="{{ url_for('public.bulletins') }}" class="text-dark fw-bold text-decoration-none">
                                {{ b.title }} ({{ b.bulletin_date.strftime('%d-%b-%Y') if b.bulletin_date else '' }})
                            </a>
                            {% if b.attachment_path %}
                                <a href="{{ url_for('static', filename=b.attachment_path) }}" target="_blank" class="badge bg-danger text-white ms-1 text-decoration-none"><i class="fa-solid fa-file-pdf"></i> PDF</a>
                            {% endif %}
                            &bull;
                        </span>
                    {% endfor %}
                {% endif %}
                {% for n in notices %}
                    <span class="me-4">
                        <span class="badge bg-primary me-1">NOTICE</span>
                        <a href="{{ url_for('public.notices') }}" class="text-dark fw-bold text-decoration-none">
                            [{{ n.category }}] {{ n.title }} ({{ n.created_at.strftime('%d-%b-%Y') }})
                        </a>
                        &bull;
                    </span>
                {% endfor %}
            </marquee>
        </div>"""

html = html.replace(old_ticker, new_ticker)

# 2. Update Carousel to render dynamic slides if available
old_carousel = """            <div id="deptHeroCarousel" class="carousel slide hero-slider" data-bs-ride="carousel">
                <div class="carousel-indicators">
                    <button type="button" data-bs-target="#deptHeroCarousel" data-bs-slide-to="0" class="active" aria-current="true" aria-label="Slide 1"></button>
                    <button type="button" data-bs-target="#deptHeroCarousel" data-bs-slide-to="1" aria-label="Slide 2"></button>
                    <button type="button" data-bs-target="#deptHeroCarousel" data-bs-slide-to="2" aria-label="Slide 3"></button>
                </div>
                <div class="carousel-inner">
                    <div class="carousel-item active">
                        <svg class="bd-placeholder-img w-100 h-100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice" focusable="false">
                            <rect width="100%" height="100%" fill="#002244"></rect>
                            <circle cx="50%" cy="40%" r="90" fill="#003366"></circle>
                            <text x="50%" y="42%" fill="#ffde59" font-family="'Segoe UI', sans-serif" font-weight="bold" font-size="28" text-anchor="middle">⚡ ELECTRIC OPERATION DEPARTMENT ⚡</text>
                            <text x="50%" y="54%" fill="#ffffff" font-family="'Segoe UI', sans-serif" font-size="18" text-anchor="middle">Howrah Division &bull; Eastern Railway</text>
                        </svg>
                        <div class="carousel-caption-custom">
                            <h4 class="text-warning fw-bold mb-1">Committed to Zero SPAD & Maximum Safety</h4>
                            <p class="text-white small mb-0">Empowering Running Crews, Chief Loco Inspectors, and Lobbies across Howrah Division with real-time safety directives and digital records.</p>
                        </div>
                    </div>
                    <div class="carousel-item">
                        <svg class="bd-placeholder-img w-100 h-100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice" focusable="false">
                            <rect width="100%" height="100%" fill="#082c4d"></rect>
                            <circle cx="50%" cy="40%" r="90" fill="#0b487e"></circle>
                            <text x="50%" y="42%" fill="#58d68d" font-family="'Segoe UI', sans-serif" font-weight="bold" font-size="28" text-anchor="middle">🚆 12 RUNNING LOBBIES & OUTPOSTS 🚆</text>
                            <text x="50%" y="54%" fill="#ffffff" font-family="'Segoe UI', sans-serif" font-size="16" text-anchor="middle">HWH &bull; BWN &bull; RPH &bull; PKR &bull; AZ &bull; KWAE &bull; NHT &bull; BHP &bull; TAK &bull; KURV &bull; DKAE &bull; SNT</text>
                        </svg>
                        <div class="carousel-caption-custom">
                            <h4 class="text-warning fw-bold mb-1">Seamless Crew Management & Footplate Inspection</h4>
                            <p class="text-white small mb-0">Direct CLI to Running Staff monitoring, daily safety counselling, and automated competency tracking.</p>
                        </div>
                    </div>
                    <div class="carousel-item">
                        <svg class="bd-placeholder-img w-100 h-100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice" focusable="false">
                            <rect width="100%" height="100%" fill="#1a1c23"></rect>
                            <circle cx="50%" cy="40%" r="90" fill="#2d3748"></circle>
                            <text x="50%" y="42%" fill="#f39c12" font-family="'Segoe UI', sans-serif" font-weight="bold" font-size="28" text-anchor="middle">📖 DIGITAL GR & SR REPOSITORY 📖</text>
                            <text x="50%" y="54%" fill="#ffffff" font-family="'Segoe UI', sans-serif" font-size="18" text-anchor="middle">General & Subsidiary Rules &bull; Eastern Railway Book of Rules</text>
                        </svg>
                        <div class="carousel-caption-custom">
                            <h4 class="text-warning fw-bold mb-1">Knowledge, Competency & Continuous E-Learning</h4>
                            <p class="text-white small mb-0">Complete reference on caution order forms (T/409, T/A 409, T/B 409), whistle codes, OHE safety, and train protection.</p>
                        </div>
                    </div>
                </div>
                <button class="carousel-control-prev" type="button" data-bs-target="#deptHeroCarousel" data-bs-slide="prev">
                    <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Previous</span>
                </button>
                <button class="carousel-control-next" type="button" data-bs-target="#deptHeroCarousel" data-bs-slide="next">
                    <span class="carousel-control-next-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Next</span>
                </button>
            </div>"""

new_carousel = """            {% if slides %}
            <div id="deptHeroCarousel" class="carousel slide hero-slider shadow-sm" data-bs-ride="carousel">
                <div class="carousel-indicators">
                    {% for s in slides %}
                        <button type="button" data-bs-target="#deptHeroCarousel" data-bs-slide-to="{{ loop.index0 }}" class="{% if loop.first %}active{% endif %}" aria-current="{% if loop.first %}true{% else %}false{% endif %}" aria-label="Slide {{ loop.index }}"></button>
                    {% endfor %}
                </div>
                <div class="carousel-inner" style="border-radius: 8px; overflow: hidden; height: 380px;">
                    {% for s in slides %}
                        <div class="carousel-item {% if loop.first %}active{% endif %} h-100 position-relative">
                            <img src="{{ url_for('static', filename=s.image_path) }}" class="d-block w-100 h-100 object-fit-cover" alt="{{ s.title }}">
                            <div class="carousel-caption-custom" style="background: linear-gradient(0deg, rgba(0, 18, 51, 0.85) 0%, rgba(0, 18, 51, 0.4) 70%, transparent 100%); bottom: 0; left: 0; right: 0; padding: 25px;">
                                <h3 class="text-warning fw-bold mb-1">{{ s.title }}</h3>
                                {% if s.subtitle %}
                                    <p class="text-white small mb-2" style="max-width: 680px;">{{ s.subtitle }}</p>
                                {% endif %}
                                {% if s.button_text and s.button_url %}
                                    <a href="{{ s.button_url }}" class="btn btn-warning btn-sm text-dark fw-bold px-3">
                                        {{ s.button_text }} &rarr;
                                    </a>
                                {% endif %}
                            </div>
                        </div>
                    {% endfor %}
                </div>
                <button class="carousel-control-prev" type="button" data-bs-target="#deptHeroCarousel" data-bs-slide="prev">
                    <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Previous</span>
                </button>
                <button class="carousel-control-next" type="button" data-bs-target="#deptHeroCarousel" data-bs-slide="next">
                    <span class="carousel-control-next-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Next</span>
                </button>
            </div>
            {% else %}
            <div id="deptHeroCarousel" class="carousel slide hero-slider" data-bs-ride="carousel">
                <div class="carousel-indicators">
                    <button type="button" data-bs-target="#deptHeroCarousel" data-bs-slide-to="0" class="active" aria-current="true" aria-label="Slide 1"></button>
                    <button type="button" data-bs-target="#deptHeroCarousel" data-bs-slide-to="1" aria-label="Slide 2"></button>
                    <button type="button" data-bs-target="#deptHeroCarousel" data-bs-slide-to="2" aria-label="Slide 3"></button>
                </div>
                <div class="carousel-inner">
                    <div class="carousel-item active">
                        <svg class="bd-placeholder-img w-100 h-100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice" focusable="false">
                            <rect width="100%" height="100%" fill="#002244"></rect>
                            <circle cx="50%" cy="40%" r="90" fill="#003366"></circle>
                            <text x="50%" y="42%" fill="#ffde59" font-family="'Segoe UI', sans-serif" font-weight="bold" font-size="28" text-anchor="middle">⚡ ELECTRIC OPERATION DEPARTMENT ⚡</text>
                            <text x="50%" y="54%" fill="#ffffff" font-family="'Segoe UI', sans-serif" font-size="18" text-anchor="middle">Howrah Division &bull; Eastern Railway</text>
                        </svg>
                        <div class="carousel-caption-custom">
                            <h4 class="text-warning fw-bold mb-1">Committed to Zero SPAD & Maximum Safety</h4>
                            <p class="text-white small mb-0">Empowering Running Crews, Chief Loco Inspectors, and Lobbies across Howrah Division with real-time safety directives and digital records.</p>
                        </div>
                    </div>
                    <div class="carousel-item">
                        <svg class="bd-placeholder-img w-100 h-100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice" focusable="false">
                            <rect width="100%" height="100%" fill="#082c4d"></rect>
                            <circle cx="50%" cy="40%" r="90" fill="#0b487e"></circle>
                            <text x="50%" y="42%" fill="#58d68d" font-family="'Segoe UI', sans-serif" font-weight="bold" font-size="28" text-anchor="middle">🚆 12 RUNNING LOBBIES & OUTPOSTS 🚆</text>
                            <text x="50%" y="54%" fill="#ffffff" font-family="'Segoe UI', sans-serif" font-size="16" text-anchor="middle">HWH &bull; BWN &bull; RPH &bull; PKR &bull; AZ &bull; KWAE &bull; NHT &bull; BHP &bull; TAK &bull; KURV &bull; DKAE &bull; SNT</text>
                        </svg>
                        <div class="carousel-caption-custom">
                            <h4 class="text-warning fw-bold mb-1">Seamless Crew Management & Footplate Inspection</h4>
                            <p class="text-white small mb-0">Direct CLI to Running Staff monitoring, daily safety counselling, and automated competency tracking.</p>
                        </div>
                    </div>
                    <div class="carousel-item">
                        <svg class="bd-placeholder-img w-100 h-100" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice" focusable="false">
                            <rect width="100%" height="100%" fill="#1a1c23"></rect>
                            <circle cx="50%" cy="40%" r="90" fill="#2d3748"></circle>
                            <text x="50%" y="42%" fill="#f39c12" font-family="'Segoe UI', sans-serif" font-weight="bold" font-size="28" text-anchor="middle">📖 DIGITAL GR & SR REPOSITORY 📖</text>
                            <text x="50%" y="54%" fill="#ffffff" font-family="'Segoe UI', sans-serif" font-size="18" text-anchor="middle">General & Subsidiary Rules &bull; Eastern Railway Book of Rules</text>
                        </svg>
                        <div class="carousel-caption-custom">
                            <h4 class="text-warning fw-bold mb-1">Knowledge, Competency & Continuous E-Learning</h4>
                            <p class="text-white small mb-0">Complete reference on caution order forms (T/409, T/A 409, T/B 409), whistle codes, OHE safety, and train protection.</p>
                        </div>
                    </div>
                </div>
                <button class="carousel-control-prev" type="button" data-bs-target="#deptHeroCarousel" data-bs-slide="prev">
                    <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Previous</span>
                </button>
                <button class="carousel-control-next" type="button" data-bs-target="#deptHeroCarousel" data-bs-slide="next">
                    <span class="carousel-control-next-icon" aria-hidden="true"></span>
                    <span class="visually-hidden">Next</span>
                </button>
            </div>
            {% endif %}"""

html = html.replace(old_carousel, new_carousel)

# 3. Add Important Operational Links quick portal row right below Hero Carousel
portal_cards = """    <!-- IMPORTANT OPERATIONAL PORTALS (FOIS, COIS, RTIS, SSTS, E-LEARNING) -->
    <div class="row g-3 mb-4">
        <div class="col-12">
            <div class="card border-0 shadow-sm p-3 bg-light">
                <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap">
                    <h5 class="fw-bold text-dark mb-0">
                        <i class="fa-solid fa-tower-broadcast text-danger me-2"></i> IMPORTANT OPERATIONAL PORTALS &amp; E-LEARNING
                    </h5>
                    <span class="badge bg-primary">Quick Access Portals</span>
                </div>
                <div class="row g-2">
                    <div class="col-lg-2 col-md-4 col-6">
                        <a href="https://www.fois.indianrail.gov.in/" target="_blank" class="btn btn-outline-primary w-100 text-start p-2 h-100 shadow-sm">
                            <div class="fw-bold text-primary"><i class="fa-solid fa-train-track me-1"></i> FOIS</div>
                            <small class="text-muted d-block" style="font-size:0.75rem;">Freight Operations System</small>
                        </a>
                    </div>
                    <div class="col-lg-2 col-md-4 col-6">
                        <a href="https://cois.indianrail.gov.in/" target="_blank" class="btn btn-outline-success w-100 text-start p-2 h-100 shadow-sm">
                            <div class="fw-bold text-success"><i class="fa-solid fa-train-subway me-1"></i> COIS</div>
                            <small class="text-muted d-block" style="font-size:0.75rem;">Coaching Operations System</small>
                        </a>
                    </div>
                    <div class="col-lg-2 col-md-4 col-6">
                        <a href="https://rtis.cris.org.in/" target="_blank" class="btn btn-outline-danger w-100 text-start p-2 h-100 shadow-sm">
                            <div class="fw-bold text-danger"><i class="fa-solid fa-satellite-dish me-1"></i> RTIS</div>
                            <small class="text-muted d-block" style="font-size:0.75rem;">Real-Time Train Tracking</small>
                        </a>
                    </div>
                    <div class="col-lg-2 col-md-4 col-6">
                        <a href="https://fois.indianrail.gov.in/SSTS" target="_blank" class="btn btn-outline-warning text-dark w-100 text-start p-2 h-100 shadow-sm">
                            <div class="fw-bold text-dark"><i class="fa-solid fa-clock-rotate-left me-1 text-warning"></i> SSTS</div>
                            <small class="text-muted d-block" style="font-size:0.75rem;">Short Stay Crew Tracking</small>
                        </a>
                    </div>
                    <div class="col-lg-2 col-md-4 col-6">
                        <a href="https://elearninghwh.in/home_page.html" target="_blank" class="btn btn-warning text-dark w-100 text-start p-2 h-100 shadow-sm fw-bold border-dark">
                            <div><i class="fa-solid fa-graduation-cap me-1"></i> E-Learning</div>
                            <small class="text-dark d-block" style="font-size:0.75rem;">elearninghwh.in Portal</small>
                        </a>
                    </div>
                    <div class="col-lg-2 col-md-4 col-6">
                        <a href="{{ url_for('public.rules') }}" class="btn btn-outline-secondary w-100 text-start p-2 h-100 shadow-sm">
                            <div class="fw-bold text-dark"><i class="fa-solid fa-book-bookmark me-1 text-success"></i> Rules (GR/SR)</div>
                            <small class="text-muted d-block" style="font-size:0.75rem;">Rulebooks &amp; SWRs</small>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
"""

# Insert right after row of carousel (around line 140)
target_after_carousel = '    <!-- OFFICER\'S SAY ("OFFICERS DESK") -->'
if "IMPORTANT OPERATIONAL PORTALS" not in html:
    html = html.replace(target_after_carousel, portal_cards + "\n" + target_after_carousel)

with open(index_file, 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated templates/public/index.html successfully.")
