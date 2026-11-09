with open(r'templates\public\learning_materials.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = """                    <a href="{{ url_for('elearning.troubleshooting') }}" class="btn btn-outline-warning text-dark w-100 fw-bold btn-sm">
                        <i class="fa-solid fa-screwdriver-wrench me-1"></i> Electric Loco Troubleshooting
                    </a>"""

repl = """                    <a href="{{ url_for('public.haulage_capacity') }}" class="btn btn-primary w-100 fw-bold btn-sm mb-2 shadow-sm">
                        <i class="fa-solid fa-calculator me-1"></i> Hauling Capacity &amp; Load Calculator (RDSO)
                    </a>
                    <a href="{{ url_for('elearning.troubleshooting') }}" class="btn btn-outline-warning text-dark w-100 fw-bold btn-sm">
                        <i class="fa-solid fa-screwdriver-wrench me-1"></i> Electric Loco Troubleshooting
                    </a>"""

assert target in html, "target not found in learning_materials.html"
html = html.replace(target, repl, 1)

with open(r'templates\public\learning_materials.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("[OK] templates/public/learning_materials.html updated successfully!")
