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
from models import User, Lobby
from blueprints.reporting_helper import (
    get_crew_overview_stats, get_cli_crew_matrix, get_lobby_crew_matrix,
    filter_crews_query, export_crews_to_excel, export_crews_to_csv
)

class Phase7TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            db.create_all()

    def test_01_reporting_helper_functions(self):
        """Test reporting_helper metrics, aggregation, and export builders."""
        with self.app.app_context():
            # 1. Overview stats
            stats = get_crew_overview_stats()
            self.assertIn('total_count', stats)
            self.assertIn('active_count', stats)
            self.assertIn('category_counts', stats)
            self.assertIn('LPM', stats['category_counts'])
            self.assertIn('ALP', stats['category_counts'])
            self.assertIn('traction_counts', stats)
            self.assertIn('grading_counts', stats)

            # 2. CLI matrix
            cli_mat = get_cli_crew_matrix()
            self.assertIn('matrix', cli_mat)
            self.assertIsInstance(cli_mat['matrix'], list)
            if cli_mat['matrix']:
                first_row = cli_mat['matrix'][0]
                self.assertIn('cli', first_row)
                self.assertIn('total_crews', first_row)
                self.assertIn('cat_dist', first_row)

            # 3. Lobby matrix
            lobby_mat = get_lobby_crew_matrix()
            self.assertIn('matrix', lobby_mat)
            self.assertGreaterEqual(len(lobby_mat['matrix']), 1)
            # Check 12 lobbies logic
            lobby_codes = {row['lobby'].code for row in lobby_mat['matrix']}
            self.assertTrue(any(c in lobby_codes for c in ['RPH', 'BWN', 'HWH', 'DKAE']))

            # 4. Filter query
            q = filter_crews_query(category='LPG')
            self.assertIsNotNone(q)

            # 5. Export to Excel and CSV
            sample_crews = User.query.filter_by(role='crew').limit(5).all()
            excel_buf = export_crews_to_excel(sample_crews)
            self.assertGreater(excel_buf.getbuffer().nbytes, 1000)

            csv_buf = export_crews_to_csv(sample_crews)
            self.assertIn('Crew ID (Mobile)', csv_buf.getvalue())

            print(" [PASS] test_01_reporting_helper_functions")

    def test_02_admin_important_tools_and_reports(self):
        """Test Admin access to Important Tools suite and Reporting Hub."""
        with self.client as c:
            with c.session_transaction() as sess:
                with self.app.app_context():
                    admin = User.query.filter_by(role='admin').first()
                    sess['user_id'] = admin.id
                    sess['username'] = admin.username
                    sess['role'] = 'admin'

            # 1. Important Tools Hub
            res = c.get('/admin/important-tools')
            self.assertEqual(res.status_code, 200)

            # 2. Bulk Analysis Tool
            res = c.get('/admin/important-tools/bulk-analysis')
            self.assertEqual(res.status_code, 200)

            # 3. PF Entry Speed Checker
            res = c.get('/admin/important-tools/pf-entry-speed')
            self.assertEqual(res.status_code, 200)

            # 4. Reports Desk
            res = c.get('/admin/reports')
            self.assertEqual(res.status_code, 200)

            # 5. Export Excel
            res = c.get('/admin/reports/export/excel')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

            # 6. Export CSV
            res = c.get('/admin/reports/export/csv')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'text/csv')

            print(" [PASS] test_02_admin_important_tools_and_reports")

    def test_03_officer_reports_suite_and_remark(self):
        """Test Officer multi-parameter reports, export, and supervisory remarks."""
        with self.app.app_context():
            officer = User.query.filter_by(role='officer').first()
            if not officer:
                officer = User(username='SR_DEEOP_HWH', role='officer', sub_role='SR_DEE_OP', full_name='Sr. DEE(OP) HWH')
                db.session.add(officer)
                db.session.commit()
            officer_id = officer.id
            officer_user = officer.username

            crew = User.query.filter_by(role='crew').first()
            crew_id = crew.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = officer_id
                sess['username'] = officer_user
                sess['role'] = 'officer'

            # 1. Main Reports page
            res = c.get('/officer/reports')
            self.assertEqual(res.status_code, 200)

            # 2. Filtered Tab
            res = c.get('/officer/reports?tab=filter&category=LPG')
            self.assertEqual(res.status_code, 200)

            # 3. Export Excel
            res = c.get('/officer/reports/export/excel?category=LPG')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

            # 4. Export CSV
            res = c.get('/officer/reports/export/csv?category=LPG')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'text/csv')

            # 5. Add Officer Remark on Crew
            res = c.post(f'/officer/crew/{crew_id}/remark', data={
                'officer_remark': 'Officer inspected crew driving log; recommended for Grade A upgrade.',
                'safety_grading': 'A'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            with self.app.app_context():
                updated_crew = db.session.get(User, crew_id)
                self.assertEqual(updated_crew.safety_grading, 'A')
                self.assertIn('recommended for Grade A upgrade', updated_crew.remarks)

            print(" [PASS] test_03_officer_reports_suite_and_remark")

    def test_04_control_parity_tools_and_reports(self):
        """Test TLC & PCNL Control full operational parity (Important Tools & Reports)."""
        with self.app.app_context():
            control_user = User.query.filter_by(role='control').first()
            if not control_user:
                control_user = User(username='TLC', role='control', sub_role='TLC', full_name='Traction Loco Controller')
                db.session.add(control_user)
                db.session.commit()
            ctrl_id = control_user.id
            ctrl_name = control_user.username

        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = ctrl_id
                sess['username'] = ctrl_name
                sess['role'] = 'control'

            # 1. Control Important Tools Launchpad
            res = c.get('/control/important-tools')
            self.assertEqual(res.status_code, 200)

            # 2. Operational Tools
            res = c.get('/control/tools/bulk-analysis')
            self.assertEqual(res.status_code, 200)

            res = c.get('/control/tools/pf-entry-speed')
            self.assertEqual(res.status_code, 200)

            res = c.get('/control/tools/duty-hours-count')
            self.assertEqual(res.status_code, 200)

            res = c.get('/control/tools/memo-generator')
            self.assertEqual(res.status_code, 200)

            res = c.get('/control/tools/availability-management')
            self.assertEqual(res.status_code, 200)

            res = c.get('/control/tools/gradient')
            self.assertEqual(res.status_code, 200)

            # 3. Control Reports Desk (Parity with Sr. DEE(OP))
            res = c.get('/control/reports')
            self.assertEqual(res.status_code, 200)

            # 4. Control Excel & CSV Export
            res = c.get('/control/reports/export/excel')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

            res = c.get('/control/reports/export/csv')
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.mimetype, 'text/csv')

            print(" [PASS] test_04_control_parity_tools_and_reports")

if __name__ == '__main__':
    unittest.main()
