import os
import sys

site_packages = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages'
base_dir = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard'

if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import unittest
from datetime import datetime, date
from app import create_app
from database import db
from models import User, Lobby, GoogleSheetLink, UnusualIncident

class Phase6TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()

    def test_01_google_sheet_link_model_and_permissions(self):
        """Test GoogleSheetLink model, embed URL generation, and RBAC permissions."""
        with self.app.app_context():
            # Create a test sheet
            sheet = GoogleSheetLink(
                title='Test Safety Monitoring Master',
                sheet_url='https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0',
                category='SAFETY_MONITORING',
                description='Automated test sheet for safety drives',
                allowed_roles='admin,officer,supervisor',
                traction_type='ELECTRIC',
                is_active=True
            )
            db.session.add(sheet)
            db.session.commit()

            self.assertIsNotNone(sheet.id)
            self.assertIn('/preview?rm=minimal', sheet.get_embed_url())

            # Test permission check
            admin_user = User.query.filter_by(role='admin').first()
            if not admin_user:
                admin_user = User(username='test_adm', role='admin', full_name='Admin Test')
                db.session.add(admin_user)
                db.session.commit()
            self.assertTrue(sheet.is_accessible_by(admin_user))

            # Role string check
            self.assertTrue(sheet.is_accessible_by('officer'))
            self.assertTrue(sheet.is_accessible_by('supervisor'))
            self.assertFalse(sheet.is_accessible_by('crew')) # Crew not in allowed_roles

            print(" [PASS] test_01_google_sheet_link_model_and_permissions")

    def test_02_unusual_incident_model_and_number_gen(self):
        """Test UnusualIncident model, sequential number generation, and badge attributes."""
        with self.app.app_context():
            inc_num = UnusualIncident.generate_incident_number()
            self.assertTrue(inc_num.startswith('INC/HWH/'))

            incident = UnusualIncident(
                incident_number=inc_num,
                incident_date=date.today(),
                incident_time='11:15',
                section='HWH-BWN',
                station_location='BWN Yard, Km 95/4',
                train_no='12301 Up',
                loco_no='WAP-7 30201',
                traction_type='ELECTRIC',
                incident_category='SPAD',
                brief_description='Signal passing test event description for testing suite.',
                status='REPORTED',
                reported_by_role='ADMIN'
            )
            db.session.add(incident)
            db.session.commit()

            self.assertIsNotNone(incident.id)
            self.assertEqual(incident.incident_category, 'SPAD')
            self.assertEqual(incident.category_label, 'Signal Passing At Danger (SPAD)')
            badge_cls, icon, text = incident.status_badge
            self.assertEqual(text, 'Reported')

            print(" [PASS] test_02_unusual_incident_model_and_number_gen")

    def test_03_admin_sheets_and_incidents_endpoints(self):
        """Test Admin Google Sheets and Unusual Incident endpoints."""
        with self.client as c:
            with c.session_transaction() as sess:
                with self.app.app_context():
                    admin = User.query.filter_by(role='admin').first()
                    sess['user_id'] = admin.id
                    sess['username'] = admin.username
                    sess['role'] = 'admin'

            # 1. GET sheets list
            res = c.get('/admin/sheets')
            self.assertEqual(res.status_code, 200)

            # 2. POST create new sheet
            res = c.post('/admin/sheets/new', data={
                'title': 'CLI Performance Google Sheet',
                'sheet_url': 'https://docs.google.com/spreadsheets/d/test1234/edit',
                'category': 'CLI_PERFORMANCE',
                'description': 'CLI targets and compliance',
                'allowed_roles': ['admin', 'officer', 'control', 'supervisor'],
                'traction_type': 'BOTH',
                'display_order': '1',
                'is_active': '1'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            # 3. GET incidents list
            res = c.get('/admin/incidents')
            self.assertEqual(res.status_code, 200)

            # 4. POST create new incident
            res = c.post('/admin/incidents/new', data={
                'incident_date': '2026-11-08',
                'incident_time': '16:00',
                'section': 'BWN-RPH',
                'station_location': 'BHP Km 152/1',
                'train_no': '13010 Down',
                'loco_no': 'WAG-9 31100',
                'traction_type': 'ELECTRIC',
                'incident_category': 'LOCO_FAILURE',
                'brief_description': 'Pantograph damaged due to external bird hit.',
                'primary_cause': 'Bird hit on DJ assembly',
                'immediate_action': 'Rear pantograph raised after checking',
                'delay_minutes': '25',
                'status': 'REPORTED'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            print(" [PASS] test_03_admin_sheets_and_incidents_endpoints")

    def test_04_officer_surveillance_and_remark(self):
        """Test Officer Sheets and Incident Surveillance & Directive endorsement."""
        with self.app.app_context():
            officer = User.query.filter_by(role='officer').first()
            if not officer:
                officer = User(username='SR_DEEOP_HWH', role='officer', sub_role='SR_DEE_OP', full_name='Sr. DEE(OP) HWH')
                db.session.add(officer)
                db.session.commit()

            incident = UnusualIncident.query.order_by(UnusualIncident.id.desc()).first()
            officer_id = officer.id
            officer_username = officer.username

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = officer_id
                sess['username'] = officer_username
                sess['role'] = 'officer'

            # 1. View officer sheets
            res = c.get('/officer/sheets')
            self.assertEqual(res.status_code, 200)

            # 2. View officer incidents surveillance
            res = c.get('/officer/incidents')
            self.assertEqual(res.status_code, 200)

            # 3. View dossier
            res = c.get(f'/officer/incidents/{incident.id}')
            self.assertEqual(res.status_code, 200)

            # 4. Endorse executive remark
            res = c.post(f'/officer/incidents/{incident.id}/remark', data={
                'officer_remarks': 'Nominated CLI to conduct joint inspection with Shed staff and submit report within 48 hours.',
                'status': 'UNDER_INVESTIGATION'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            with self.app.app_context():
                reloaded = db.session.get(UnusualIncident, incident.id)
                self.assertIn('Nominated CLI to conduct joint inspection', reloaded.officer_remarks)
                self.assertEqual(reloaded.status, 'UNDER_INVESTIGATION')

            print(" [PASS] test_04_officer_surveillance_and_remark")

    def test_05_control_operational_log(self):
        """Test Control (TLC / PCNL) Shift Incidents and Action Logging."""
        with self.app.app_context():
            control_user = User.query.filter_by(role='control').first()
            if not control_user:
                control_user = User(username='TLC', role='control', sub_role='TLC', full_name='Traction Loco Controller')
                db.session.add(control_user)
                db.session.commit()
            ctrl_id = control_user.id
            ctrl_user = control_user.username

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = ctrl_id
                sess['username'] = ctrl_user
                sess['role'] = 'control'

            # 1. View control sheets
            res = c.get('/control/sheets')
            self.assertEqual(res.status_code, 200)

            # 2. View shift incidents
            res = c.get('/control/incidents')
            self.assertEqual(res.status_code, 200)

            # 3. Fast log new incident
            res = c.post('/control/incidents/new', data={
                'incident_date': '2026-11-08',
                'incident_time': '16:20',
                'section': 'HWH-DKAE',
                'station_location': 'DKAE Km 14/8',
                'train_no': '37815 Down',
                'loco_no': '30055',
                'traction_type': 'ELECTRIC',
                'incident_category': 'UNUSUAL_SOUND',
                'crew_name_manual': 'P. K. Ghosh',
                'brief_description': 'LP reported unusual jerk while passing over point 102.',
                'immediate_action': 'Section advised to caution following trains at 20 kmph.',
                'delay_minutes': '10'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            print(" [PASS] test_05_control_operational_log")

    def test_06_supervisor_and_crew_views(self):
        """Test Supervisor Squad Incident action and Crew Safety Case Studies."""
        with self.app.app_context():
            supervisor = User.query.filter_by(role='supervisor').first()
            if not supervisor:
                supervisor = User(username='CLI_TEST', role='supervisor', full_name='CLI Test Supervisor')
                db.session.add(supervisor)
                db.session.commit()

            crew_user = User.query.filter_by(role='crew').first()
            if not crew_user:
                crew_user = User(username='9876543210', role='crew', full_name='ALP Test Crew')
                db.session.add(crew_user)
                db.session.commit()

            incident = UnusualIncident.query.order_by(UnusualIncident.id.desc()).first()
            sup_id = supervisor.id
            sup_name = supervisor.username
            crew_id = crew_user.id
            crew_name = crew_user.username
            inc_id = incident.id

        # Test Supervisor
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = sup_id
                sess['username'] = sup_name
                sess['role'] = 'supervisor'

            res = c.get('/supervisor/sheets')
            self.assertEqual(res.status_code, 200)

            res = c.get('/supervisor/incidents')
            self.assertEqual(res.status_code, 200)

            res = c.post(f'/supervisor/incidents/{inc_id}/action', data={
                'primary_cause': 'Track gauge variation at tongue rail',
                'findings': 'Point checked jointly with P-Way supervisor; packing done.',
                'status': 'ACTION_COMPLETED'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        # Test Crew
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = crew_id
                sess['username'] = crew_name
                sess['role'] = 'crew'

            res = c.get('/crew/sheets')
            self.assertEqual(res.status_code, 200)

            res = c.get('/crew/unusual-reports')
            self.assertEqual(res.status_code, 200)

            print(" [PASS] test_06_supervisor_and_crew_views")

if __name__ == '__main__':
    unittest.main()
