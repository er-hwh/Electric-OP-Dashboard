import os
import sys
import io
import json

workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

venv_pkg = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages"
if os.path.exists(venv_pkg) and venv_pkg not in sys.path:
    sys.path.insert(0, venv_pkg)

import openpyxl
from app import create_app
from database import db
from models import User, Lobby, CustomField

app = create_app()

def test_phase2():
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

    print("\n================== PHASE 2 VERIFICATION ==================\n")

    # Authenticate client as admin
    with app.app_context():
        User.query.filter(User.mobile.in_(['9831999001', '9831999002', '9831999003'])).delete()
        db.session.commit()

    with app.test_client() as c:
        c.post('/auth/login', data={'username': 'admin', 'password': '12345'}, follow_redirects=True)

        # 1. Test Lobby Management
        r = c.get('/admin/lobbies')
        check("Admin accesses /admin/lobbies", r.status_code == 200 and b'DIVISIONAL LOBBY MANAGEMENT' in r.data)
        check("All 12 Lobbies listed in /admin/lobbies", b'RPH' in r.data and b'KURV' in r.data and b'NHT' in r.data)

        # Update a lobby in-charge and jurisdiction
        with app.app_context():
            hwh_lobby = Lobby.query.filter_by(code='HWH').first()
            cli_hwh = User.query.filter_by(username='CLI_HWH_01').first()
            lid = hwh_lobby.id
            cid = cli_hwh.id

        r = c.post(f'/admin/lobbies/{lid}/update', data={
            'in_charge_cli_id': str(cid),
            'ccc_name': 'Sri Prasanta Panja (CCC/HWH)',
            'phone': '033-2660-1234',
            'operational_jurisdiction': 'HWH-BWN Main & Chord EMU/Freight routes',
            'description': 'HQ Primary Running Lobby'
        }, follow_redirects=True)
        check("Lobby in-charge and jurisdiction updated", r.status_code == 200 and b'updated successfully' in r.data)

        with app.app_context():
            updated_lobby = Lobby.query.get(lid)
            check("Lobby DB updated with in-charge CLI", updated_lobby.in_charge_cli_id == cid)
            check("Lobby DB updated with operational jurisdiction", 'HWH-BWN Main' in (updated_lobby.operational_jurisdiction or ''))

        # 2. Test Dynamic Custom Fields Management
        r = c.get('/admin/custom-fields')
        check("Admin accesses /admin/custom-fields", r.status_code == 200 and b'DYNAMIC CUSTOM FIELDS' in r.data)

        # Add a custom field
        r = c.post('/admin/custom-fields/add', data={
            'field_label': 'Safety Grading',
            'field_name': 'safety_grading',
            'field_type': 'select',
            'options': 'A, B, C, D',
            'is_required': 'on'
        }, follow_redirects=True)
        check("Custom field added successfully", r.status_code == 200)

        with app.app_context():
            cf = CustomField.query.filter_by(field_name='safety_grading').first()
            check("CustomField created in DB", cf is not None and cf.field_label == 'Safety Grading')
            check("CustomField options stored correctly", cf is not None and 'A' in cf.get_options())
            cf_id = cf.id

        # Toggle status
        r = c.post(f'/admin/custom-fields/{cf_id}/toggle', follow_redirects=True)
        check("CustomField toggle active status", r.status_code == 200 and b'marked as' in r.data)
        # Toggle back to active
        c.post(f'/admin/custom-fields/{cf_id}/toggle', follow_redirects=True)

        # 3. Test Crew Master Database & Export
        r = c.get('/admin/crew-master')
        check("Admin accesses /admin/crew-master", r.status_code == 200 and b'CREW MASTER DATABASE' in r.data)
        check("Custom field column present in table", b'Safety Grading' in r.data)

        # Export Excel
        r = c.get('/admin/crew-master/export')
        check("Export crew master to Excel", r.status_code == 200 and 'spreadsheetml' in r.headers.get('Content-Type', ''))

        # Quick update a crew
        with app.app_context():
            sample_crew = User.query.filter_by(role='crew').first()
            crew_id = sample_crew.id

        r = c.post(f'/admin/crew-master/{crew_id}/quick-update', data={
            'full_name': sample_crew.full_name,
            'mobile': sample_crew.mobile,
            'pf_number': sample_crew.pf_number or 'PF123456',
            'sub_role': 'LPM',
            'lobby_id': str(sample_crew.lobby_id or 1),
            'cli_id': str(sample_crew.cli_id or 1),
            'safety_grading': 'A'
        }, follow_redirects=True)
        check("Quick update crew record", r.status_code == 200)

        with app.app_context():
            updated_crew = User.query.get(crew_id)
            check("Custom field value persisted in crew JSON", updated_crew.get_custom_fields().get('safety_grading') == 'A')

        # 4. Test Excel Upload & Preview Workflow (Section 8)
        # Create an in-memory sample Excel file using openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Master Crew"
        # Header
        ws.append(["CLI ID", "CLI Name", "Crew Name", "Employee ID", "Mobile", "Category", "Lobby", "Safety Grading"])
        # Row 1 (Valid)
        ws.append(["CLI_TEST_01", "Sri Test Inspector", "Ramesh Kumar Sharma", "5020999001", "9831999001", "LPM", "HWH", "A"])
        # Row 2 (Valid)
        ws.append(["CLI_TEST_01", "Sri Test Inspector", "Anoop Singh", "5020999002", "9831999002", "LPG", "BWN", "B"])
        # Row 3 (Intentionally duplicate mobile of Row 2)
        ws.append(["CLI_TEST_02", "Sri Inspector Two", "Deepak Das", "5020999003", "9831999002", "ALP", "RPH", "C"])

        excel_stream = io.BytesIO()
        wb.save(excel_stream)
        excel_stream.seek(0)

        # Upload preview
        r = c.post('/admin/crew-master/upload-preview', data={
            'file': (excel_stream, 'test_crew_master.xlsx')
        }, content_type='multipart/form-data')
        check("Upload-preview endpoint returns 200", r.status_code == 200)

        preview_data = json.loads(r.data.decode('utf-8'))
        check("Preview parsed 3 rows", preview_data.get('total_rows') == 3, f"Got: {preview_data.get('total_rows')}")
        check("Duplicate detected in preview", preview_data.get('duplicates_count') >= 1, f"Found {preview_data.get('duplicates_count')}")

        # Correct Row 3 duplicate before batch save
        valid_rows = preview_data['rows']
        valid_rows[2]['mobile'] = "9831999003"  # Corrected mobile

        # Batch save to master database
        r = c.post('/admin/crew-master/save-batch', 
                   data=json.dumps({'rows': valid_rows}),
                   content_type='application/json')
        check("Save-batch endpoint returns 200", r.status_code == 200)

        save_res = json.loads(r.data.decode('utf-8'))
        check("Batch save succeeded", save_res.get('success') is True)
        check("New crew records created", save_res.get('created', 0) >= 2, f"Created: {save_res.get('created')}")

        with app.app_context():
            ramesh = User.query.filter_by(mobile='9831999001').first()
            check("Uploaded crew Ramesh exists in DB", ramesh is not None)
            if ramesh:
                check("Ramesh has role 'crew'", ramesh.role == 'crew')
                check("Ramesh has category 'LPM'", ramesh.sub_role == 'LPM')
                check("Ramesh default password is '12345'", ramesh.check_password('12345'))
                check("Ramesh nominated CLI is CLI_TEST_01", ramesh.nominated_cli is not None and ramesh.nominated_cli.username == 'CLI_TEST_01')
                check("Ramesh custom field 'safety_grading' is 'A'", ramesh.get_custom_fields().get('safety_grading') == 'A')

    print(f"\n================== RESULTS: {passed} PASSED, {failed} FAILED ==================\n")
    return failed == 0

if __name__ == '__main__':
    success = test_phase2()
    sys.exit(0 if success else 1)
