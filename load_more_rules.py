from app import create_app
from database import db
from models import ELearningRule, Notice, User

app = create_app()

def load_more_rules():
    with app.app_context():
        officer = User.query.filter_by(username='Sr. DEE(OP)/HWH').first()
        
        new_rules = [
            {
                'chapter_no': 'Railway Board Safety',
                'chapter_title': 'Drunkenness on Duty & Breathalyzer Procedure',
                'rule_no': 'Rly Bd 2009/Safety(DM)/6/12 (12.11.2018)',
                'rule_title': 'Rejection of Second Breath Analyser Test - Absolute Finality of First Test',
                'general_rule': (
                    "In response to representations seeking second breath analyser test if an employee fails the first test, "
                    "Railway Board has reiterated that:\n"
                    "1. Under GR 2.09(1): No Railway servant shall be in a state of intoxication or where capacity to perform duties is impaired.\n"
                    "2. Under GR 2.09(2): No Railway servant directly connected with train working shall consume alcohol within EIGHT HOURS before commencement of duty or while on duty.\n"
                    "3. Decision: There are NO SUFFICIENT REASONS to modify instructions. NO SECOND BREATH ANALYSER TEST is permitted if an employee fails the initial test. "
                    "The first test result is conclusive and immediate D&AR / off-duty action must follow."
                ),
                'subsidiary_rule': "Lobby CCC and breathalyzer operators must strictly abide by the single-test protocol. Refusal or failure results in immediate replacement of crew.",
                'category': 'Safety Policy & D&AR',
                'key_points': "NO SECOND TEST permitted if crew fails first breathalyzer test. First test is final."
            },
            {
                'chapter_no': 'Running Allowance Rules',
                'chapter_title': 'Minimum Guaranteed Kilometreage (MGK)',
                'rule_no': 'Rly Bd E(P&A)II-85/FE-4/3 (1985)',
                'rule_title': 'Grant of Minimum Guaranteed Kilometreage (120 KM) & Spare Travel Calculation',
                'general_rule': (
                    "1. Running staff working on identified short sections where extended run/round trips within duty hours are not feasible "
                    "shall be granted Minimum Guaranteed Kilometreage (MGK) of 120 Kms.\n"
                    "2. Staff unable to complete run on identified section due to operational reasons or relieved enroute are also eligible for 120 Kms.\n"
                    "3. Travelling as Passenger on Duty (Spare) before/after working: Running staff working on identified sections shall be granted "
                    "120 Kms for working the section, PLUS HALF (50%) of the kilometreage covered while travelling as passenger on duty (spare)."
                ),
                'subsidiary_rule': "Lobby CCC and CLIs must verify trip sheets to ensure correct calculation of 120 KM MGK + 50% spare travel allowance.",
                'category': 'Allowances & Running Rules',
                'key_points': "120 KM Minimum Guaranteed Kilometreage + 50% of spare passenger travel distance."
            },
            {
                'chapter_no': 'Hours of Employment (HOER)',
                'chapter_title': 'Spare Running on Duty & Overtime',
                'rule_no': 'Rly Bd E(LL)79/HER(RLT)/23 (1985)',
                'rule_title': 'Running Staff Travelling Spare on Duty Without Crew Rest Van - Full Overtime Credit',
                'general_rule': (
                    "1. In case of running staff travelling spare on double-manned trains without the facility of a Crew Rest Van, "
                    "FULL CREDIT should be given to both sets of crew for payment of overtime (OT).\n"
                    "2. In future, double set of crew should NOT be provided on a train without the provision of a crew rest van. "
                    "If inescapable in train working interest, permitted only with personal approval of GM in consultation with FA&CAO for max 2 months."
                ),
                'subsidiary_rule': "Ensure proper rest van attachment when double crew is rostered; else grant full OT credit to both sets.",
                'category': 'Allowances & Running Rules',
                'key_points': "Full overtime credit to both crew sets if travelling spare without Crew Rest Van."
            },
            {
                'chapter_no': 'Railway Board Medical & Safety',
                'chapter_title': 'Periodical Medical Examination (PME)',
                'rule_no': 'Rly Bd 2016/M(L)/467/1 (2020)',
                'rule_title': 'Strict Compliance & Exception Monitoring for PME and Safety Courses in CMS',
                'general_rule': (
                    "All running staff must undergo Periodic Medical Examination (PME) strictly as per medical classification (A-1 for LP/ALP). "
                    "Crew booking for PME-overdue staff is strictly prohibited in CMS except under explicit Railway Board policy dispensations. "
                    "Exception reports must be monitored by Sr. DEE(OP) and Divisional Safety Officers."
                ),
                'subsidiary_rule': "CCC and Lobby supervisors must spare running staff for PME well before the expiry of their medical fitness certificate.",
                'category': 'Training & Competency',
                'key_points': "Mandatory PME adherence for A-1 medical category; CMS exception report tracking."
            }
        ]

        for r in new_rules:
            existing = ELearningRule.query.filter_by(rule_no=r['rule_no']).first()
            if not existing:
                db.session.add(ELearningRule(**r))
                print(f"Added rule: {r['rule_no']}")
            else:
                existing.general_rule = r['general_rule']
                existing.subsidiary_rule = r['subsidiary_rule']
                existing.category = r['category']
                existing.key_points = r['key_points']
                print(f"Updated rule: {r['rule_no']}")

        if officer:
            n1 = {
                'title': 'Reiteration: Conclusive Nature of Breathalyzer Test - No Second Test Permitted (Rly Bd 2018)',
                'category': 'Sr. DEE(OP) Instruction',
                'content': 'All Lobby In-charges (CCC), Chief Loco Inspectors (CLI), and Running Staff are reminded that under Railway Board Letter No. 2009/Safety(DM)/6/12/Committee dt 12.11.2018, NO SECOND BREATH ANALYSER TEST is permitted if an employee fails the initial test. Extant rules under GR 2.09(1) & (2) must be strictly enforced with immediate off-duty action.',
                'target_audience': 'ALL',
                'published_by_id': officer.id,
                'is_urgent': True
            }
            if not Notice.query.filter_by(title=n1['title']).first():
                db.session.add(Notice(**n1))
                print("Added Notice on Conclusive Breathalyzer Test")

            n2 = {
                'title': 'Adherence to Minimum Guaranteed Kilometreage (MGK) and Spare Travel Rules (1985 Order)',
                'category': 'Circular',
                'content': 'Attention of all CCCs and CLIs is drawn to Board letter No. E(P&A)II-85/FE-4/3. On identified short sections, running staff are entitled to 120 KM MGK plus 50% kilometreage for travelling spare on duty before or after working. Ensure accurate TA/KMA journal verification.',
                'target_audience': 'ALL',
                'published_by_id': officer.id,
                'is_urgent': False
            }
            if not Notice.query.filter_by(title=n2['title']).first():
                db.session.add(Notice(**n2))
                print("Added Notice on MGK")

        db.session.commit()
        print("All additional running rules and instructions loaded successfully!")

if __name__ == '__main__':
    load_more_rules()
