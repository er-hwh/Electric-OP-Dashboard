with open(r'templates\control\tools\gradient.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = """                <!-- Admin-only Upload Button -->
                <button id="btnToggleUpload" class="btn btn-outline-primary btn-sm fw-bold admin-only" style="display: none;">
                    <i class="bi bi-cloud-arrow-up-fill me-1"></i> Import Excel
                </button>"""

repl = """                <a href="{{ url_for('public.haulage_capacity') }}" class="btn btn-warning btn-sm fw-bold shadow-sm" target="_blank">
                    <i class="bi bi-speedometer2 me-1"></i> Hauling Capacity Calculator
                </a>
                <!-- Admin-only Upload Button -->
                <button id="btnToggleUpload" class="btn btn-outline-primary btn-sm fw-bold admin-only" style="display: none;">
                    <i class="bi bi-cloud-arrow-up-fill me-1"></i> Import Excel
                </button>"""

assert target in html, "target not found in gradient.html"
html = html.replace(target, repl, 1)

with open(r'templates\control\tools\gradient.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("[OK] templates/control/tools/gradient.html updated successfully!")
