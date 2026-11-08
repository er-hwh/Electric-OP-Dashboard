import os
import sys

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

# Add virtualenv site-packages to path
venv_pkg = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages"
if os.path.exists(venv_pkg) and venv_pkg not in sys.path:
    sys.path.insert(0, venv_pkg)

from app import create_app
from database import db
from models import User, Lobby

app = create_app()

def test_phase1():
    client = app.test_client()
    passed = 0
    failed = 0

    def check(name, condition, extra=""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f" [PASS] {name} {extra}")
        else:
            failed += 1
            print(f" [FAIL] {name} {extra}")

    print("\n================== PHASE 1 VERIFICATION ==================\n")

    # 1. Test Public Routes
    r = client.get('/')
    check("Public Home (/)", r.status_code == 200)

    r = client.get('/loco-info')
    check("Public Loco Info (/loco-info)", r.status_code == 200 and b'WAP-7' in r.data and b'WDP-4D' in r.data)

    r = client.get('/learning-materials')
    check("Public Learning Materials (/learning-materials)", r.status_code == 200 and b'Electric Traction' in r.data)

    r = client.get('/elearning/')
    check("Public Rules Explorer (/elearning/)", r.status_code == 200)

    r = client.get('/elearning/troubleshooting')
    check("Public Troubleshooting (/elearning/troubleshooting)", r.status_code == 200)

    r = client.get('/elearning/quiz')
    check("Public Quiz (/elearning/quiz)", r.status_code == 200)

    r = client.get('/notices')
    check("Public Notices (/notices)", r.status_code == 200)

    r = client.get('/gallery')
    check("Public Gallery (/gallery)", r.status_code == 200)

    # 2. Check Daily Safety Counselling is removed from public and redirects
    r = client.get('/counselling')
    check("Daily Counselling redirects to login", r.status_code in [302, 301] and '/auth/login' in r.headers.get('Location', ''))

    # 3. Check Lobbies (9 Main + 3 Sister)
    with app.app_context():
        main_lobbies = Lobby.query.filter_by(is_sister_lobby=False).all()
        sister_lobbies = Lobby.query.filter_by(is_sister_lobby=True).all()
        check("9 Main Lobbies present", len(main_lobbies) == 9, f"Found {len(main_lobbies)}")
        check("3 Sister Lobbies present (NHT, SNT, KURV)", len(sister_lobbies) == 3, f"Found {len(sister_lobbies)}")
        for l in main_lobbies:
            check(f"Lobby {l.code} has in-charge CLI", l.in_charge_cli_id is not None)

    # 4. Test Authentications with initial credentials (admin, SR_DEEOP_HWH, AEEOP_HWH, AMEP_HWH, TLC, PCNL, CLI, Crew)
    credentials_to_test = [
        ('admin', '12345', '/admin/'),
        ('SR_DEEOP_HWH', '12345', '/officer/'),
        ('AEEOP_HWH', '12345', '/officer/'),
        ('AMEP_HWH', '12345', '/officer/'),
        ('TLC', '12345', '/control/dashboard'),
        ('PCNL', '12345', '/control/dashboard'),
        ('CLI_HWH_01', '12345', '/supervisor/'),
        ('9876543210', '12345', '/crew/')
    ]

    for uname, pwd, expected_redirect in credentials_to_test:
        with app.test_client() as c:
            r = c.post('/auth/login', data={'username': uname, 'password': pwd}, follow_redirects=False)
            loc = r.headers.get('Location', '')
            check(f"Login for '{uname}' redirects to {expected_redirect}", expected_redirect in loc, f"Got: {loc}")

    # 5. Test Important Tools (Admin-only restricted access)
    with app.test_client() as c:
        # Without login -> redirected
        r = c.get('/admin/important-tools')
        check("Unauthenticated access to /admin/important-tools denied", r.status_code in [302, 401, 403])

        # Login as Admin
        c.post('/auth/login', data={'username': 'admin', 'password': '12345'}, follow_redirects=True)
        r = c.get('/admin/important-tools')
        check("Admin accesses /admin/important-tools", r.status_code == 200 and b'IMPORTANT TOOLS' in r.data)

        r = c.get('/admin/important-tools/bulk-analysis')
        check("Admin accesses Bulk Analysis tool", r.status_code == 200)

        r = c.get('/admin/important-tools/pf-entry-speed')
        check("Admin accesses PF Entry Speed tool", r.status_code == 200)

    # 6. Test TLC & PCNL Control Login tool access
    for ctrl_user in ['TLC', 'PCNL']:
        with app.test_client() as c:
            c.post('/auth/login', data={'username': ctrl_user, 'password': '12345'}, follow_redirects=True)
            r = c.get('/control/dashboard')
            check(f"{ctrl_user} accesses Control Dashboard", r.status_code == 200)

            r = c.get('/control/tools/bulk-analysis')
            check(f"{ctrl_user} accesses authorized Bulk Analysis tool", r.status_code == 200)

            r = c.get('/control/tools/pf-entry-speed')
            check(f"{ctrl_user} accesses authorized PF Entry Speed tool", r.status_code == 200)

    print(f"\n================== RESULTS: {passed} PASSED, {failed} FAILED ==================\n")
    return failed == 0

if __name__ == '__main__':
    success = test_phase1()
    sys.exit(0 if success else 1)
