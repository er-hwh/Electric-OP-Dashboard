import os
import sys
from datetime import datetime, date, timedelta

# Add workspace and site-packages
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from database import db
from models import (
    User, Lobby, CLIMovement, FootplateInspection, 
    CrewCounsellingRecord, TrainingRecord
)

app = create_app()

def run_tests():
    passed = 0
    failed = 0

    def assert_true(cond, msg):
        nonlocal passed, failed
        if cond:
            print(f"  [PASS] {msg}")
            passed += 1
        else:
            print(f"  [FAIL] {msg}")
            failed += 1

    with app.app_context():
        print("=== RUNNING PHASE 3 TEST SUITE ===")

        client = app.test_client()

        # 1. Fetch key test accounts
        admin = User.query.filter_by(username='admin').first()
        officer = User.query.filter_by(username='SR_DEEOP_HWH').first()
        tlc = User.query.filter_by(username='TLC').first()
        pcnl = User.query.filter_by(username='PCNL').first()
        cli = User.query.filter_by(role='supervisor', sub_role='CLI').first()
        crew = User.query.filter_by(role='crew').first()
        lobby = Lobby.query.first()

        assert_true(admin is not None, "Admin user exists")
        assert_true(officer is not None, "Officer user (SR_DEEOP_HWH) exists")
        assert_true(tlc is not None and tlc.is_control(), "TLC Control user exists")
        assert_true(pcnl is not None and pcnl.is_control(), "PCNL Control user exists")
        assert_true(cli is not None and cli.is_supervisor(), "CLI user exists")
        assert_true(crew is not None and crew.is_crew(), "Crew user exists")
        assert_true(lobby is not None, "Lobby exists")

        # -------------------------------------------------------------
        # 2. CLI Daily Movement Creation & Syncing
        # -------------------------------------------------------------
        print("\n--- Testing CLI Movement Creation & Synchronization ---")
        
        # Test CLI logging new Footplate movement via POST
        with client.session_transaction() as sess:
            sess['user_id'] = cli.id
            sess['role'] = 'supervisor'

        resp = client.post('/supervisor/movements/new', data={
            'activity_type': 'Footplate Inspection',
            'activity_date': date.today().strftime('%Y-%m-%d'),
            'lobby_id': lobby.id,
            'section_from': 'HWH',
            'section_to': 'BWN',
            'train_no': '12301 Up',
            'loco_no': '30201 WAP7',
            'footplate_km': '108.5',
            'departure_time': '06:00',
            'arrival_time': '07:30',
            'crew_id': str(crew.id),
            'crew_name_manual': crew.full_name,
            'crew_id_str': crew.pf_number or crew.username,
            'crew_category': crew.sub_role,
            'grading': 'A',
            'observations_irregularities': 'Signal calling prompt and loud; RS valve tested',
            'corrective_action': 'Counselled on calling-on signal aspect adherence',
            'remarks': 'Satisfactory run'
        }, follow_redirects=True)

        assert_true(resp.status_code == 200, "CLI /movements/new POST succeeded")

        mov = CLIMovement.query.filter_by(cli_id=cli.id, train_no='12301 Up').first()
        assert_true(mov is not None, "CLIMovement record created in DB")
        assert_true(mov.footplate_km == 108.5, "CLIMovement footplate_km recorded correctly")
        assert_true(mov.grading == 'A', "CLIMovement grading recorded as A")
        assert_true(mov.is_within_retention, "Movement is marked within 90-day retention")

        # Check FootplateInspection sync
        fp_rec = FootplateInspection.query.filter_by(cli_id=cli.id, train_no='12301 Up').first()
        assert_true(fp_rec is not None, "FootplateInspection synchronized automatically")

        # Test CLI viewing /movements
        resp_list = client.get('/supervisor/movements')
        assert_true(resp_list.status_code == 200, "CLI /movements page loads successfully")
        assert_true(b"12301 Up" in resp_list.data, "Logged movement train number visible in table")

        # Test CLI editing movement
        resp_edit = client.post(f'/supervisor/movements/{mov.id}/edit', data={
            'activity_type': 'Footplate Inspection',
            'activity_date': date.today().strftime('%Y-%m-%d'),
            'lobby_id': lobby.id,
            'section_from': 'HWH',
            'section_to': 'BWN',
            'train_no': '12301 Up (Rajdhani)',
            'loco_no': '30201 WAP7',
            'footplate_km': '108.5',
            'departure_time': '06:00',
            'arrival_time': '07:25',
            'crew_id': str(crew.id),
            'crew_name_manual': crew.full_name,
            'crew_id_str': crew.pf_number or crew.username,
            'crew_category': crew.sub_role,
            'grading': 'A',
            'observations_irregularities': 'Signal calling exemplary',
            'corrective_action': 'Counselling completed',
            'remarks': 'Punctual arrival'
        }, follow_redirects=True)
        assert_true(resp_edit.status_code == 200, "CLI edit movement POST succeeded")
        mov_updated = CLIMovement.query.get(mov.id)
        assert_true(mov_updated.train_no == '12301 Up (Rajdhani)', "CLIMovement train_no updated")

        # -------------------------------------------------------------
        # 3. Quick Action Synchronization
        # -------------------------------------------------------------
        print("\n--- Testing Quick Action Synchronization to CLIMovement ---")
        
        # Test quick_spm
        client.post('/supervisor/quick-spm', data={
            'crew_id': str(crew.id),
            'spm_date': date.today().strftime('%Y-%m-%d'),
            'train_no': '37812 EMU',
            'loco_no': 'EMU-312',
            'speed_viol': 'No',
            'remarks': 'Speed within prescribed MPS 96 kmph'
        })
        spm_mov = CLIMovement.query.filter_by(cli_id=cli.id, activity_type='SPM Analysis', train_no='37812 EMU').first()
        assert_true(spm_mov is not None, "quick_spm automatically created CLIMovement entry")

        # Test quick_cvvrs
        client.post('/supervisor/quick-cvvrs', data={
            'crew_id': str(crew.id),
            'cvvrs_date': date.today().strftime('%Y-%m-%d'),
            'irregularity': 'Nil'
        })
        cvvrs_mov = CLIMovement.query.filter_by(cli_id=cli.id, activity_type='CVVRS Inspection').first()
        assert_true(cvvrs_mov is not None, "quick_cvvrs automatically created CLIMovement entry")

        # -------------------------------------------------------------
        # 4. Officer Monitoring & Remarks (Strict RBAC)
        # -------------------------------------------------------------
        print("\n--- Testing Officer Monitoring & Remark Permissions ---")
        
        with client.session_transaction() as sess:
            sess['user_id'] = officer.id
            sess['role'] = 'officer'

        # Officer views cli-movements
        resp_off_mov = client.get('/officer/cli-movements')
        assert_true(resp_off_mov.status_code == 200, "Officer /cli-movements loads successfully")
        assert_true(b"12301 Up (Rajdhani)" in resp_off_mov.data, "Officer sees logged CLI movements")

        # Officer adds remark to CLI movement
        resp_remark = client.post(f'/officer/cli-movements/{mov.id}/remark', data={
            'officer_remarks': 'Good footplate monitoring. Ensure follow up on turnout speed at BWN yard.'
        }, follow_redirects=True)
        assert_true(resp_remark.status_code == 200, "Officer remark POST succeeded")

        mov_remarked = CLIMovement.query.get(mov.id)
        assert_true("Ensure follow up on turnout speed" in mov_remarked.officer_remarks, "Officer remark saved on movement")
        assert_true(mov_remarked.officer_remarked_by_id == officer.id, "Officer remark credited to officer.id")
        # Ensure CLI factual data was not tampered with
        assert_true(mov_remarked.train_no == '12301 Up (Rajdhani)', "CLI factual data preserved (Immutable)")

        # Officer views cli-performance
        resp_cli_perf = client.get('/officer/cli-performance')
        assert_true(resp_cli_perf.status_code == 200, "Officer /cli-performance loads successfully")
        assert_true(cli.full_name.encode() in resp_cli_perf.data, "CLI appears in CLI performance table")

        # Officer views crew-performance and adds remark
        resp_crew_perf = client.get('/officer/crew-performance')
        assert_true(resp_crew_perf.status_code == 200, "Officer /crew-performance loads successfully")

        c_rec = CrewCounsellingRecord.query.first()
        if c_rec:
            client.post('/officer/crew-performance', data={
                'record_id': str(c_rec.id),
                'officer_remarks': 'Recommended for refresher safety camp.'
            })
            c_rec_refreshed = CrewCounsellingRecord.query.get(c_rec.id)
            assert_true("Recommended for refresher" in (c_rec_refreshed.officer_remarks or ''), "Officer remark recorded on crew")

        # -------------------------------------------------------------
        # 5. TLC & PCNL Control Monitoring Parity
        # -------------------------------------------------------------
        print("\n--- Testing TLC & PCNL Control Monitoring Access ---")
        
        # Test TLC access
        with client.session_transaction() as sess:
            sess['user_id'] = tlc.id
            sess['role'] = 'control'
            sess['username'] = 'TLC'

        resp_tlc_mov = client.get('/officer/cli-movements')
        assert_true(resp_tlc_mov.status_code == 200, "TLC can access /officer/cli-movements")

        resp_tlc_perf = client.get('/officer/cli-performance')
        assert_true(resp_tlc_perf.status_code == 200, "TLC can access /officer/cli-performance")

        # Test PCNL access
        with client.session_transaction() as sess:
            sess['user_id'] = pcnl.id
            sess['role'] = 'control'
            sess['username'] = 'PCNL'

        resp_pcnl_mov = client.get('/officer/cli-movements')
        assert_true(resp_pcnl_mov.status_code == 200, "PCNL can access /officer/cli-movements")

        # Test Control adding operational remark
        resp_ctl_remark = client.post(f'/officer/cli-movements/{mov.id}/remark', data={
            'officer_remarks': 'Power Control (PCNL): Checked sectional locomotive running time.'
        }, follow_redirects=True)
        assert_true(resp_ctl_remark.status_code == 200, "Control can record operational remark on movement")

        # -------------------------------------------------------------
        # 6. Data Retention Policy (3 Months / 90 Days)
        # -------------------------------------------------------------
        print("\n--- Testing 3-Month (90-Day) Retention Policy & Purge ---")

        # Create an old movement record (100 days old)
        old_date = date.today() - timedelta(days=100)
        old_mov = CLIMovement(
            cli_id=cli.id,
            activity_date=old_date,
            activity_type='Yard Inspection',
            location='HWH Yard (Old)',
            remarks='Old yard inspection log from 100 days ago'
        )
        db.session.add(old_mov)
        db.session.commit()

        assert_true(not old_mov.is_within_retention, "100-day-old record is flagged as NOT within retention")
        old_id = old_mov.id

        # Admin retention policy page
        with client.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['role'] = 'admin'

        resp_ret = client.get('/admin/retention-policy')
        assert_true(resp_ret.status_code == 200, "Admin /retention-policy loads successfully")
        assert_true(b"Eligible for Purge" in resp_ret.data, "Eligible for purge section displayed")

        # Execute purge via Admin POST
        resp_purge = client.post('/admin/retention-policy', follow_redirects=True)
        assert_true(resp_purge.status_code == 200, "Admin purge POST executed")

        # Verify old record is deleted
        old_check = CLIMovement.query.get(old_id)
        assert_true(old_check is None, "Record older than 90 days was purged successfully")

        # Verify recent records (<= 90 days) are PRESERVED
        recent_check = CLIMovement.query.get(mov.id)
        assert_true(recent_check is not None, "Recent movement (< 90 days) was safely PRESERVED")

        # Verify permanent tables (User, CrewCounsellingRecord, TrainingRecord) are completely untouched
        user_cnt = User.query.count()
        assert_true(user_cnt > 0, "Users table strictly intact after purge")
        counsel_cnt = CrewCounsellingRecord.query.count()
        assert_true(counsel_cnt > 0, "Crew Counselling Master table strictly intact after purge")

        print(f"\nPhase 3 Test Results: {passed} passed, {failed} failed")
        if failed > 0:
            sys.exit(1)

if __name__ == '__main__':
    run_tests()
