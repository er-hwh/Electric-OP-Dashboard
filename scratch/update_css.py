with open(r'static\css\custom.css', 'r', encoding='utf-8') as f:
    css = f.read()

target = """.main-navbar .nav-link {
  color: var(--ir-blue-dark) !important;
  font-weight: 600;
  padding: 14px 16px !important;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
}"""

replacement = """.main-navbar .nav-link {
  color: var(--ir-blue-dark) !important;
  font-weight: 600;
  padding: 12px 14px !important;
  white-space: nowrap !important;
  transition: all 0.2s ease;
  border-bottom: 3px solid transparent;
  font-size: 0.94rem;
}

@media (min-width: 1200px) and (max-width: 1420px) {
  .main-navbar .nav-link {
    padding: 12px 9px !important;
    font-size: 0.88rem;
  }
  .btn-dashboard-nav {
    padding: 5px 12px !important;
    font-size: 0.84rem;
  }
}"""

if target in css:
    css = css.replace(target, replacement, 1)
    with open(r'static\css\custom.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("[OK] static/css/custom.css updated!")
else:
    print("[FAIL] target not found in static/css/custom.css")
