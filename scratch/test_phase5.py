import os
import sys
import unittest
from datetime import datetime, date, timedelta

# Set up paths
project_dir = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard"
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import create_app
from database import db
from models import (
    User, Lobby, Notice, NoticeAcknowledgement, CounsellingTopic,
    CounsellingAcknowledgement, CrewCounsellingLog, CrewCounsellingRecord,
    CLIMovement
)

class TestPhase5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.app.config['WTF_CSRF_ENABLED'] = False

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_01_notice_creation_and_stats(self):
        """Test notice creation with traction types and compliance stats."""
        # Clean up any previous test circular
        old_notices = Notice.query.filter_by(notice_number="HWH/TEST/CIRCULAR/01").all()
        for on in old_notices:
            NoticeAcknowledgement.query.filter_by(notice_id=on.id).delete()
            db.session.delete(on)
        db.session.commit()

        # Find or create admin user
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(username='test_admin_p5', full_name='Test Admin', role='admin')
            admin.set_password('12345')
            db.session.add(admin)
            db.session.commit()

        # Create Notice
        notice = Notice(
            title="Test Safety Circular Monsoon Precautions",
            content="Maintain strict vigilance during thunderstorm. Test brake feel.",
            notice_number="HWH/TEST/CIRCULAR/01",
            category="SAFETY",
            traction_type="ELECTRIC",
            is_mandatory=True,
            is_urgent=True,
            posted_by_id=admin.id
        )
        db.session.add(notice)
        db.session.commit()

        self.assertIsNotNone(notice.id)
        self.assertEqual(notice.traction_type, "ELECTRIC")
        self.assertTrue(notice.is_mandatory)

        # Check compliance stats
        stats = notice.get_compliance_stats()
        self.assertIn('total_crews', stats)
        self.assertIn('acked_count', stats)
        self.assertIn('unacked_count', stats)
        self.assertIn('percentage', stats)
        self.assertEqual(stats['acked_count'], 0)

    def test_02_officer_endorsement(self):
        """Test officer digital endorsement on a circular."""
        officer = User.query.filter_by(role='officer').first()
        if not officer:
            officer = User(username='test_officer_p5', full_name='Sr. DEE(OP)/HWH', role='officer', sub_role='Sr. DEE(OP)')
            officer.set_password('12345')
            db.session.add(officer)
            db.session.commit()

        notice = Notice.query.filter_by(notice_number="HWH/TEST/CIRCULAR/01").first()
        self.assertIsNotNone(notice)

        notice.approved_by_id = officer.id
        notice.approval_date = datetime.utcnow()
        notice.officer_remarks = "Approved for division-wide running staff enforcement."
        db.session.commit()

        # Re-fetch
        n_updated = Notice.query.get(notice.id)
        self.assertEqual(n_updated.approved_by_id, officer.id)
        self.assertIsNotNone(n_updated.approval_date)
        self.assertEqual(n_updated.officer_remarks, "Approved for division-wide running staff enforcement.")

    def test_03_crew_notice_acknowledgement(self):
        """Test crew mandatory notice acknowledgement with IP and audit recording."""
        crew = User.query.filter_by(role='crew').first()
        if not crew:
            lobby = Lobby.query.first()
            crew = User(username='test_crew_p5', full_name='Test ALP Crew', role='crew', sub_role='ALP', mobile='9876543210', lobby_id=lobby.id if lobby else None)
            crew.set_password('12345')
            db.session.add(crew)
            db.session.commit()

        notice = Notice.query.filter_by(notice_number="HWH/TEST/CIRCULAR/01").first()
        self.assertFalse(notice.is_acknowledged_by(crew.id))

        # Record acknowledgement
        ack = NoticeAcknowledgement(
            notice_id=notice.id,
            user_id=crew.id,
            acknowledged_at=datetime.utcnow(),
            remarks="Read and completely understood.",
            ip_address="192.168.1.100",
            device_info="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            is_confirmed=True
        )
        db.session.add(ack)
        db.session.commit()

        self.assertTrue(notice.is_acknowledged_by(crew.id))
        self.assertEqual(notice.get_ack_count(), 1)
        stats = notice.get_compliance_stats()
        self.assertGreaterEqual(stats['acked_count'], 1)

    def test_04_cli_counselling_log_and_synchronization(self):
        """Test CLI recording one-to-one counselling session and syncing with CrewCounsellingRecord & Movement diary."""
        cli = User.query.filter(User.role.in_(['supervisor', 'admin'])).first()
        crew = User.query.filter_by(role='crew').first()

        c_date = date.today()
        topic_title = "SPAD Prevention & Speed Restriction Adherence"

        log = CrewCounsellingLog(
            cli_id=cli.id,
            crew_id=crew.id,
            counselling_date=c_date,
            counselling_type='MONTHLY_SAFETY',
            topic=topic_title,
            location='HWH Lobby',
            counselling_mode='One-to-One',
            crew_response='Understood precautions and rules.',
            cli_remarks='Good comprehension demonstrated.',
            crew_acknowledged=False
        )
        db.session.add(log)

        # Synchronize with CrewCounsellingRecord
        formatted_date = c_date.strftime('%d-%m-%Y')
        rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == crew.id) |
            (CrewCounsellingRecord.crew_id_str == crew.username)
        ).first()

        if not rec:
            rec = CrewCounsellingRecord(
                crew_user_id=crew.id,
                crew_id_str=crew.username,
                crew_name=crew.full_name,
                cug=crew.mobile,
                designation=crew.sub_role,
                grade='A'
            )
            db.session.add(rec)

        rec.safety_counselling = formatted_date
        rec.counselling_verified_by = cli.full_name

        # Synchronize with CLIMovement diary
        mov = CLIMovement(
            cli_id=cli.id,
            activity_date=c_date,
            activity_type='Crew Counselling',
            lobby_id=crew.lobby_id or cli.lobby_id or 1,
            location='HWH Lobby',
            crew_id=crew.id,
            crew_name_manual=crew.full_name,
            crew_id_str=crew.username,
            crew_category=crew.sub_role,
            grading='A',
            observations_irregularities=f"Topic: {topic_title}",
            corrective_action='Imparted instructions on signal perception.'
        )
        db.session.add(mov)
        db.session.commit()

        self.assertIsNotNone(log.id)
        self.assertIsNotNone(mov.id)
        self.assertEqual(rec.safety_counselling, formatted_date)

    def test_05_counselling_status_and_30_day_surveillance(self):
        """Test User.counselling_status property and 30-day overdue detection."""
        crew = User.query.filter_by(role='crew').first()
        status = crew.counselling_status

        self.assertIn('status', status)
        self.assertIn('days_elapsed', status)
        self.assertIn('last_date', status)
        self.assertIn('is_overdue', status)

        # Since we just counselled today, it should be COMPLIANT / OK
        self.assertEqual(status['status'], 'OK')
        self.assertFalse(status['is_overdue'])
        self.assertEqual(status['days_elapsed'], 0)

        # Test simulated overdue crew (>30 days)
        # Create a crew with past counselling date 45 days ago
        old_date = date.today() - timedelta(days=45)
        cli = User.query.filter(User.role.in_(['supervisor', 'admin'])).first()
        old_crew = User.query.filter_by(username='test_old_crew_p5').first()
        if not old_crew:
            old_crew = User(username='test_old_crew_p5', full_name='Overdue Crew Member', role='crew', sub_role='LPG', mobile='9111222333')
            old_crew.set_password('12345')
            db.session.add(old_crew)
            db.session.commit()

        old_rec = CrewCounsellingRecord.query.filter_by(crew_user_id=old_crew.id).first()
        if not old_rec:
            old_rec = CrewCounsellingRecord(
                crew_user_id=old_crew.id,
                crew_id_str=old_crew.username,
                crew_name=old_crew.full_name,
                safety_counselling=old_date.strftime('%d-%m-%Y')
            )
            db.session.add(old_rec)
        else:
            old_rec.safety_counselling = old_date.strftime('%d-%m-%Y')
        db.session.commit()

        old_status = old_crew.counselling_status
        self.assertEqual(old_status['status'], 'OVERDUE')
        self.assertTrue(old_status['is_overdue'])
        self.assertGreater(old_status['days_elapsed'], 30)

    def test_06_crew_acknowledges_counselling_log(self):
        """Test crew digitally acknowledging one-to-one counselling session."""
        log = CrewCounsellingLog.query.order_by(CrewCounsellingLog.id.desc()).first()
        self.assertIsNotNone(log)
        self.assertFalse(log.crew_acknowledged)

        log.crew_acknowledged = True
        log.crew_ack_date = datetime.utcnow()
        log.crew_response = "Confirmed having received counselling and clarified all doubts."
        db.session.commit()

        updated_log = CrewCounsellingLog.query.get(log.id)
        self.assertTrue(updated_log.crew_acknowledged)
        self.assertIsNotNone(updated_log.crew_ack_date)

    def test_07_officer_adds_remark_to_counselling_log(self):
        """Test officer adding observation/directive to a counselling session."""
        log = CrewCounsellingLog.query.order_by(CrewCounsellingLog.id.desc()).first()
        self.assertIsNotNone(log)

        log.officer_remarks = "CLI instructed to conduct follow-up inspection on footplate next trip."
        db.session.commit()

        updated_log = CrewCounsellingLog.query.get(log.id)
        self.assertIn("follow-up inspection", updated_log.officer_remarks)

    def test_08_http_endpoints_and_role_views(self):
        """Test HTTP GET/POST endpoints across Admin, Officer, Control, Supervisor, and Crew."""
        # 1. Admin notices & counselling views
        admin = User.query.filter_by(role='admin').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['role'] = 'admin'
        
        r = self.client.get('/admin/notices')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Departmental Notices", r.data)

        r = self.client.get('/admin/counselling')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Safety Counselling Topics", r.data)

        # 2. Officer notice compliance & counselling surveillance views
        officer = User.query.filter_by(role='officer').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = officer.id
            sess['role'] = 'officer'

        r = self.client.get('/officer/notice-compliance')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Circular Compliance Desk", r.data)

        r = self.client.get('/officer/counselling-monitor')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Safety Counselling Monitor", r.data)

        # 3. Control views
        ctrl = User.query.filter_by(role='control').first()
        if not ctrl:
            ctrl = User(username='test_tlc_p5', full_name='TLC Howrah', role='control', sub_role='TLC')
            ctrl.set_password('12345')
            db.session.add(ctrl)
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = ctrl.id
            sess['role'] = 'control'

        r = self.client.get('/control/notice-compliance', follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/control/counselling-monitor', follow_redirects=True)
        self.assertEqual(r.status_code, 200)

        # 4. Supervisor squad views
        cli = User.query.filter_by(role='supervisor').first()
        if not cli:
            cli = User(username='test_cli_p5', full_name='CLI Test User', role='supervisor', sub_role='CLI')
            cli.set_password('12345')
            db.session.add(cli)
            db.session.commit()

        with self.client.session_transaction() as sess:
            sess['user_id'] = cli.id
            sess['role'] = 'supervisor'

        r = self.client.get('/supervisor/notices-status')
        self.assertEqual(r.status_code, 200)

        r = self.client.get('/supervisor/counselling-logs')
        self.assertEqual(r.status_code, 200)

        # 5. Crew Running Desk
        crew = User.query.filter_by(role='crew').first()
        with self.client.session_transaction() as sess:
            sess['user_id'] = crew.id
            sess['role'] = 'crew'

        r = self.client.get('/crew/')
        self.assertEqual(r.status_code, 200)

if __name__ == '__main__':
    unittest.main()
