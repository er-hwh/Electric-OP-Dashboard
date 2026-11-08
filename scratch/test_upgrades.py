import sys
import os
import io

sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages")
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard")

from app import create_app
from database import db
from models import (
    User, CarouselSlide, SafetyBulletin, RuleDocument, LearningMaterial, PageContent
)

def run_tests():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    client = app.test_client()

    with app.app_context():
        print("--- TEST 1: Verify Models & Seeding ---")
        pages = PageContent.query.all()
        assert len(pages) >= 5, f"Expected at least 5 default page contents, found {len(pages)}"
        mission = PageContent.get_val('home_mission')
        assert 'safe' in mission.lower(), f"Mission content mismatch: {mission}"
        print(f"PASS: PageContent seeded properly. Found {len(pages)} keys. Mission: {mission[:50]}...")

        print("\n--- TEST 2: Verify CLI Login (HWH0095) ---")
        cli_user = User.query.filter_by(username='HWH0095').first()
        assert cli_user is not None, "CLI User HWH0095 not found in DB!"
        assert cli_user.check_password('12345'), "CLI User HWH0095 password check failed!"
        print(f"PASS: CLI User HWH0095 exists: {cli_user.full_name}, role: {cli_user.role}, sub_role: {cli_user.sub_role}")

        # Test auth login via HTTP client
        resp = client.post('/auth/login', data={'username': 'HWH0095', 'password': '12345'}, follow_redirects=True)
        assert resp.status_code == 200
        assert b'Supervisor' in resp.data or b'CLI' in resp.data or b'Console' in resp.data
        print("PASS: HTTP Login for HWH0095 successful with redirect to Supervisor Console.")

        print("\n--- TEST 3: Admin CMS Bulletins Upload ---")
        # Login as admin
        admin_user = User.query.filter_by(username='admin').first()
        assert admin_user is not None, "Admin user not found"
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user.id

        # Upload a test bulletin
        pdf_data = (io.BytesIO(b"%PDF-1.4 test bulletin content"), "test_bulletin.pdf")
        resp = client.post('/admin/cms/bulletins', data={
            'title': 'Test Safety Bulletin 2026',
            'bulletin_no': 'SB/TEST/01',
            'bulletin_date': '2026-11-08',
            'category': 'Safety Bulletin',
            'description': 'Important testing directives for loco operations.',
            'is_active': '1',
            'attachment': pdf_data
        }, follow_redirects=True)
        assert resp.status_code == 200
        b_entry = SafetyBulletin.query.filter_by(bulletin_no='SB/TEST/01').first()
        assert b_entry is not None, "SafetyBulletin was not created!"
        assert b_entry.attachment_path is not None, "Attachment path missing!"
        print(f"PASS: SafetyBulletin created. ID={b_entry.id}, Title='{b_entry.title}', Path='{b_entry.attachment_path}'")

        print("\n--- TEST 4: Admin CMS Carousel Upload ---")
        img_data = (io.BytesIO(b"\xff\xd8\xff\xe0 test image content"), "test_slide.jpg")
        resp = client.post('/admin/cms/carousel', data={
            'title': 'Howrah Electric Loco Fleet',
            'subtitle': 'Zero SPAD & High Safety Operating Mission',
            'button_text': 'Explore Fleet',
            'button_url': '/loco-info',
            'display_order': '1',
            'is_active': '1',
            'image': img_data
        }, follow_redirects=True)
        assert resp.status_code == 200
        slide = CarouselSlide.query.filter_by(title='Howrah Electric Loco Fleet').first()
        assert slide is not None, "CarouselSlide was not created!"
        assert slide.image_path is not None, "Slide image path missing!"
        print(f"PASS: CarouselSlide created. ID={slide.id}, Title='{slide.title}', Path='{slide.image_path}'")

        print("\n--- TEST 5: Admin CMS Rules & Regulations Upload ---")
        rule_pdf = (io.BytesIO(b"%PDF-1.4 rule content"), "gr_sr_rules.pdf")
        resp = client.post('/admin/cms/rules', data={
            'title': 'General & Subsidiary Rules ER 2026',
            'category': 'General Rules (GR)',
            'rule_reference': 'GR 3.78',
            'description': 'Complete updated Eastern Railway GR & SR with latest amendment slips.',
            'display_order': '1',
            'is_active': '1',
            'pdf_file': rule_pdf
        }, follow_redirects=True)
        assert resp.status_code == 200
        rule_doc = RuleDocument.query.filter_by(title='General & Subsidiary Rules ER 2026').first()
        assert rule_doc is not None, "RuleDocument was not created!"
        print(f"PASS: RuleDocument created. ID={rule_doc.id}, Title='{rule_doc.title}', Path='{rule_doc.pdf_path}'")

        print("\n--- TEST 6: Admin CMS Learning Materials Upload ---")
        learn_pdf = (io.BytesIO(b"%PDF-1.4 learn material"), "wap7_troubleshoot.pdf")
        resp = client.post('/admin/cms/learning', data={
            'title': 'WAP-7 HOG Converter Troubleshooting Guide',
            'traction_type': 'ELECTRIC',
            'category': 'Troubleshooting Guide',
            'description': 'Step-by-step isolation and reset instructions for Hotel Load Converter.',
            'content': '<h3>WAP-7 HOG Procedure</h3><p>1. Check VCB status.<br>2. Inspect UIC coupler.</p>',
            'external_url': 'https://elearninghwh.in/home_page.html',
            'display_order': '1',
            'is_active': '1',
            'attachment': learn_pdf
        }, follow_redirects=True)
        assert resp.status_code == 200
        learn_mat = LearningMaterial.query.filter_by(title='WAP-7 HOG Converter Troubleshooting Guide').first()
        assert learn_mat is not None, "LearningMaterial was not created!"
        assert learn_mat.external_url == 'https://elearninghwh.in/home_page.html'
        print(f"PASS: LearningMaterial created. ID={learn_mat.id}, Title='{learn_mat.title}', Traction='{learn_mat.traction_type}'")

        print("\n--- TEST 7: Public Portal Views & External Links Verification ---")
        # Home page
        resp_home = client.get('/')
        assert resp_home.status_code == 200
        assert b'FOIS' in resp_home.data
        assert b'COIS' in resp_home.data
        assert b'RTIS' in resp_home.data
        assert b'SSTS' in resp_home.data
        assert b'https://elearninghwh.in/home_page.html' in resp_home.data
        assert b'Howrah Electric Loco Fleet' in resp_home.data  # Dynamic carousel slide
        assert b'Test Safety Bulletin 2026' in resp_home.data  # Dynamic bulletin in ticker
        print("PASS: Home page renders FOIS, COIS, RTIS, SSTS, E-Learning URL, dynamic Carousel & Bulletins.")

        # Learning materials page
        resp_learn = client.get('/learning-materials')
        assert resp_learn.status_code == 200
        assert b'https://elearninghwh.in/home_page.html' in resp_learn.data
        assert b'WAP-7 HOG Converter Troubleshooting Guide' in resp_learn.data
        assert b'WAP-7 HOG Procedure' in resp_learn.data
        print("PASS: Learning Materials page renders E-Learning banner and uploaded learning guides.")

        # Rules page
        resp_rules = client.get('/rules')
        assert resp_rules.status_code == 200
        assert b'General &amp; Subsidiary Rules ER 2026' in resp_rules.data or b'General & Subsidiary Rules ER 2026' in resp_rules.data
        assert b'GR 3.78' in resp_rules.data
        print("PASS: Rules page renders uploaded rulebooks and PDF links.")

        # Bulletins page
        resp_bull = client.get('/bulletins')
        assert resp_bull.status_code == 200
        assert b'Test Safety Bulletin 2026' in resp_bull.data
        assert b'SB/TEST/01' in resp_bull.data
        print("PASS: Bulletins page renders published safety bulletins and PDF links.")

        print("\n==========================================")
        print("ALL 7 UPGRADATION TESTS PASSED PERFECTLY!")
        print("==========================================")

if __name__ == '__main__':
    run_tests()
