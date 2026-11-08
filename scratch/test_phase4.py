import os
import sys
import unittest
from datetime import date, datetime, timedelta
from io import BytesIO

# Set paths
REPO_DIR = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard"
VENV_PKGS = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages"
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
if VENV_PKGS not in sys.path:
    sys.path.insert(1, VENV_PKGS)

from app import create_app
from database import db
from models import User, Lobby, TrainingRecord, MedicalRecord
from blueprints.excel_helper import (
    generate_training_medical_template,
    parse_training_medical_excel,
    parse_excel_date
)
import openpyxl

class Phase4ComprehensiveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()

        with cls.app.app_context():
            # Ensure lobby HWH exists
            lobby = Lobby.query.filter_by(code='HWH').first()
            if not lobby:
                lobby = Lobby(code='HWH', name='Howrah', division='HWH', lobby_type='MAIN')
                db.session.add(lobby)
                db.session.commit()

            # Ensure CLI supervisor exists
            cli = User.query.filter_by(username='TEST_CLI_P4').first()
            if not cli:
                cli = User(
                    username='TEST_CLI_P4',
                    full_name='Test CLI Phase 4',
                    role='supervisor',
                    sub_role='CLI',
                    lobby_id=lobby.id,
                    mobile='9876543210'
                )
                cli.set_password('12345')
                db.session.add(cli)
                db.session.commit()

            # Ensure crew exists under CLI
            crew = User.query.filter_by(username='TEST_CREW_P4').first()
            if not crew:
                crew = User(
                    username='TEST_CREW_P4',
                    full_name='Test Running Crew Phase 4',
                    role='crew',
                    sub_role='LPP',
                    pf_number='P4CREW001',
                    lobby_id=lobby.id,
                    cli_id=cli.id,
                    mobile='9876543211',
                    date_of_birth=date(1985, 5, 20),
                    pme_fitness_status='Fit (A-One)'
                )
                crew.set_password('12345')
                db.session.add(crew)
                db.session.commit()

    def test_01_pme_age_frequency_tiers(self):
        """Test Railway running staff PME frequency age rules: <=45: 4y, 46-55: 2y, >55: 1y"""
        u = User(username='age_test', full_name='Age Test', role='crew')
        today = date.today()
        
        # Age 35 (<= 45) -> 4 years
        u.date_of_birth = date(today.year - 35, today.month, today.day)
        self.assertEqual(u.get_age(), 35)
        self.assertEqual(u.compute_pme_frequency_years(), 4)
        next_due_35 = u.calculate_next_pme_due(date(2023, 1, 15))
        self.assertEqual(next_due_35, date(2027, 1, 15))

        # Age 50 (46-55) -> 2 years
        u.date_of_birth = date(today.year - 50, today.month, today.day)
        self.assertEqual(u.get_age(), 50)
        self.assertEqual(u.compute_pme_frequency_years(), 2)
        next_due_50 = u.calculate_next_pme_due(date(2023, 1, 15))
        self.assertEqual(next_due_50, date(2025, 1, 15))

        # Age 58 (> 55) -> 1 year
        u.date_of_birth = date(today.year - 58, today.month, today.day)
        self.assertEqual(u.get_age(), 58)
        self.assertEqual(u.compute_pme_frequency_years(), 1)
        next_due_58 = u.calculate_next_pme_due(date(today.year, 1, 15))
        self.assertEqual(next_due_58, date(today.year + 1, 1, 15))

    def test_02_pme_status_info_badges(self):
        """Test PME status info logic (OK, Due Soon, Overdue)"""
        today = date.today()
        u = User(username='status_test', full_name='Status Test', role='crew')
        
        # Overdue
        u.pme_due_date = today - timedelta(days=10)
        info = u.pme_status_info
        self.assertEqual(info['status'].upper(), 'OVERDUE')
        self.assertEqual(info['class'], 'danger')
        self.assertLess(info['days_left'], 0)

        # Due Soon (<= 30 days)
        u.pme_due_date = today + timedelta(days=15)
        info = u.pme_status_info
        self.assertEqual(info['status'].upper(), 'DUE_SOON')
        self.assertEqual(info['class'], 'warning')
        self.assertEqual(info['days_left'], 15)

        # Compliant / Valid (> 30 days)
        u.pme_due_date = today + timedelta(days=90)
        info = u.pme_status_info
        self.assertEqual(info['status'].upper(), 'VALID')
        self.assertEqual(info['class'], 'success')
        self.assertEqual(info['days_left'], 90)

    def test_03_training_validity_calculation(self):
        """Test Railway training cycle default durations"""
        comp_date = date(2024, 1, 1)

        # Refresher ELEC / DSL / GR & SR: 36 Months
        due_ref = TrainingRecord.calculate_due_date(comp_date, 'Refresher ELEC')
        self.assertEqual(due_ref, date(2027, 1, 1))

        # Automatic Block System (ABS): 6 Months (180 days)
        due_abs = TrainingRecord.calculate_due_date(comp_date, 'Automatic Block System (ABS)')
        self.assertEqual(due_abs, date(2024, 7, 1))

        # Safety Camp: 12 Months
        due_sc = TrainingRecord.calculate_due_date(comp_date, 'Safety Camp')
        self.assertEqual(due_sc, date(2025, 1, 1))

    def test_04_excel_template_generation_and_parsing(self):
        """Test dynamic Excel template generation and round-trip parser"""
        wb_buf = generate_training_medical_template()
        self.assertIsNotNone(wb_buf)
        data_bytes = wb_buf.getvalue()
        self.assertGreater(len(data_bytes), 1000)

        # Parse generated template using openpyxl
        wb = openpyxl.load_workbook(BytesIO(data_bytes))
        sheet = wb.active
        self.assertEqual(sheet.title, "Training & PME Update")
        
        # Verify sample row content
        rows = list(sheet.iter_rows(values_only=True))
        self.assertGreaterEqual(len(rows), 3)
        headers = rows[2]
        self.assertIn("Employee PF / Mobile *", headers)
        self.assertIn("Record Type *", headers)
        self.assertIn("Course / Exam Name *", headers)

        # Test parse_training_medical_excel on the generated template
        with self.app.app_context():
            parsed_rows = parse_training_medical_excel(BytesIO(data_bytes))
            self.assertGreaterEqual(len(parsed_rows), 1)
            self.assertIn('record_type', parsed_rows[0])

    def test_05_admin_training_medical_portal_and_add(self):
        """Test Admin Training & Medical Management endpoints"""
        with self.app.app_context():
            admin = User.query.filter_by(username='admin').first()
            crew = User.query.filter_by(username='TEST_CREW_P4').first()

        # Login as Admin
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['role'] = 'admin'

        # 1. Access main training-medical management view
        resp = self.client.get('/admin/training-medical')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(b"Training & Medical (PME) Management" in resp.data or b"Training &amp; Medical" in resp.data)

        # 2. Download template
        resp_tpl = self.client.get('/admin/training-medical/template')
        self.assertEqual(resp_tpl.status_code, 200)
        self.assertEqual(resp_tpl.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # 3. Manually add a training record
        resp_add = self.client.post('/admin/training-medical/add', data={
            'crew_id': crew.id,
            'record_type': 'TRAINING',
            'course_name': 'Refresher ELEC',
            'training_category': 'Refresher',
            'completion_date': '2024-03-01',
            'institute': 'ZRTI Bhuli',
            'remarks': 'Class 1 division test'
        }, follow_redirects=True)
        self.assertEqual(resp_add.status_code, 200)

        with self.app.app_context():
            tr = TrainingRecord.query.filter_by(crew_id=crew.id, training_type='Refresher ELEC').first()
            self.assertIsNotNone(tr)
            self.assertEqual(tr.institute, 'ZRTI Bhuli')
            self.assertEqual(tr.due_date, date(2027, 3, 1))

        # 4. Manually add an ABS training record
        resp_add_abs = self.client.post('/admin/training-medical/add', data={
            'crew_id': crew.id,
            'record_type': 'TRAINING',
            'course_name': 'Automatic Block System (ABS)',
            'training_category': 'Technical',
            'completion_date': '2024-04-10',
            'institute': 'Divisional Safety Center',
            'remarks': '6-month ABS competency'
        }, follow_redirects=True)
        self.assertEqual(resp_add_abs.status_code, 200)

        with self.app.app_context():
            abs_tr = TrainingRecord.query.filter_by(crew_id=crew.id, training_type='Automatic Block System (ABS)').first()
            self.assertIsNotNone(abs_tr)
            self.assertEqual(abs_tr.due_date, date(2024, 10, 10))

        # 5. Manually record PME
        resp_add_pme = self.client.post('/admin/training-medical/add', data={
            'crew_id': crew.id,
            'record_type': 'PME',
            'completion_date': '2023-06-15',
            'pme_status': 'Fit (A-One)',
            'hospital': 'BRSH Sealdah',
            'fit_memo_no': 'MED/HWH/2023/987',
            'remarks': 'Vision 6/6 without glasses'
        }, follow_redirects=True)
        self.assertEqual(resp_add_pme.status_code, 200)

        with self.app.app_context():
            refreshed_crew = User.query.get(crew.id)
            self.assertEqual(refreshed_crew.pme_last_done_date, date(2023, 6, 15))
            self.assertEqual(refreshed_crew.pme_fitness_status, 'Fit (A-One)')
            self.assertIsNotNone(refreshed_crew.pme_due_date)

    def test_06_officer_and_control_training_monitor(self):
        """Test Officer and TLC/PCNL Control Training & Medical monitoring views"""
        with self.app.app_context():
            officer = User.query.filter_by(username='SR_DEEOP_HWH').first()
            if not officer:
                officer = User(username='SR_DEEOP_HWH', full_name='Sr. DEE (OP) Howrah', role='officer', sub_role='SR_DEE_OP')
                officer.set_password('12345')
                db.session.add(officer)
                db.session.commit()

            control_user = User.query.filter_by(username='TLC').first()
            if not control_user:
                control_user = User(username='TLC', full_name='Traction Loco Controller', role='control', sub_role='TLC')
                control_user.set_password('12345')
                db.session.add(control_user)
                db.session.commit()

        # 1. Officer training monitor
        with self.client.session_transaction() as sess:
            sess['user_id'] = officer.id
            sess['role'] = 'officer'

        resp_off = self.client.get('/officer/training-monitor')
        self.assertEqual(resp_off.status_code, 200)
        self.assertIn(b"Training & Medical (PME) Monitor", resp_off.data)
        self.assertIn(b"Periodical Medical Exam", resp_off.data)

        # 2. Control access via /control/training-monitor redirect
        with self.client.session_transaction() as sess:
            sess['user_id'] = control_user.id
            sess['role'] = 'control'

        resp_ctl = self.client.get('/control/training-monitor')
        self.assertEqual(resp_ctl.status_code, 302)
        self.assertIn('/officer/training-monitor', resp_ctl.location)

        # Follow redirect as control
        resp_ctl_fwd = self.client.get('/officer/training-monitor')
        self.assertEqual(resp_ctl_fwd.status_code, 200)
        self.assertIn(b"Training & Medical (PME) Monitor", resp_ctl_fwd.data)

    def test_07_supervisor_squad_training_and_recording(self):
        """Test CLI supervisory view and recording for assigned crew"""
        with self.app.app_context():
            cli = User.query.filter_by(username='TEST_CLI_P4').first()
            crew = User.query.filter_by(username='TEST_CREW_P4').first()

        with self.client.session_transaction() as sess:
            sess['user_id'] = cli.id
            sess['role'] = 'supervisor'

        # View squad training-medical
        resp_cli = self.client.get('/supervisor/training-medical')
        self.assertEqual(resp_cli.status_code, 200)
        self.assertIn(b"Squad Training & Medical", resp_cli.data)
        self.assertTrue(b"Test Running Crew Phase 4" in resp_cli.data or b"P4CREW001" in resp_cli.data)

        # CLI logs a training course for squad crew
        resp_log = self.client.post('/supervisor/training-medical/record', data={
            'crew_id': crew.id,
            'record_type': 'TRAINING',
            'course_name': 'Safety Camp',
            'completion_date': '2024-05-01',
            'institute': 'Divisional Safety Center',
            'remarks': 'Annual safety camp attended'
        }, follow_redirects=True)
        self.assertEqual(resp_log.status_code, 200)

        with self.app.app_context():
            sc = TrainingRecord.query.filter_by(crew_id=crew.id, training_type='Safety Camp').first()
            self.assertIsNotNone(sc)
            self.assertEqual(sc.due_date, date(2025, 5, 1))

    def test_08_crew_dashboard_compliance_display(self):
        """Test Running Crew portal renders PME and Training section seamlessly"""
        with self.app.app_context():
            crew = User.query.filter_by(username='TEST_CREW_P4').first()

        with self.client.session_transaction() as sess:
            sess['user_id'] = crew.id
            sess['role'] = 'crew'

        resp = self.client.get('/crew/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(b"Mandatory Training & Periodic Medical Examination (PME) Register" in resp.data or b"Mandatory Training" in resp.data)
        self.assertIn(b"Refresher ELEC", resp.data)
        self.assertIn(b"Automatic Block System (ABS)", resp.data)
        self.assertIn(b"BRSH Sealdah", resp.data)

if __name__ == '__main__':
    unittest.main()
