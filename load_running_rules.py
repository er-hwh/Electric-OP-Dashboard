from app import create_app
from database import db
from models import ELearningRule, Notice, User

app = create_app()

def load_rules():
    with app.app_context():
        officer = User.query.filter_by(username='Sr. DEE(OP)/HWH').first()
        
        rules = [
            {
                'chapter_no': 'Railway Board Policy',
                'chapter_title': 'Crew Utilization in Emergency',
                'rule_no': 'Rly Bd 97/Safety-I/11/9 (2015)',
                'rule_title': 'Working of Mail/Express Trains by Loco Pilot (Goods) in Emergency',
                'general_rule': (
                    "1. Rajdhani/Shatabdi/Duronto Express should NOT be run by LP (Goods) under any circumstances. "
                    "If necessary, trains should be run by withdrawing regular Loco Pilots from scheduled links.\n"
                    "2. Generally Mail/Express and Diverted trains should be run by LP (Mail/Pass). If not available to work these trains, then:\n"
                    "   a) All divisions should prepare a panel of adequate number of LP (Goods) holding 'A'-Grade.\n"
                    "   b) Panel of such LP (Goods) should be drawn duly screening them by Traction and Safety Officers.\n"
                    "   c) These trains will be run by the empanelled LP (Goods) as per point (a) above.\n"
                    "   d) In case an empanelled LP (Goods) is not available, then a Chief Loco Inspector (CLI/LI) must accompany the Loco Pilot on the foot-plate.\n"
                    "3. In case competent Loco Pilot as specified above is not available for running a particular type of locomotive, then the power should be changed with another type for which competent crew is available.\n"
                    "4. Where Mail/Express posts are vacant, ensure a panel of 'A'-Grade LP (Goods) is drawn up."
                ),
                'subsidiary_rule': "Strict divisional monitoring by CCC/CLI before calling LP (Goods) for passenger/express links. Mandatory LI footplate escort if non-empanelled crew is deployed.",
                'category': 'Running Rules & Deployment',
                'key_points': "Prohibition on Rajdhani/Shatabdi/Duronto; Panel of 'A' Grade LP Goods; LI footplate accompaniment mandatory if non-empanelled."
            },
            {
                'chapter_no': 'Railway Board Safety',
                'chapter_title': 'Refresher Courses for Safety Categories',
                'rule_no': 'Rly Bd 2000/Safety(A&R)/19/40 (RSRC 1998)',
                'rule_title': 'Mandatory Refresher Courses - Taking Overdue Staff Off Duty',
                'general_rule': (
                    "Consequent to acceptance of Railway Safety Review Committee (RSRC) Report 1998 (Para 5.4):\n"
                    "\"When any staff belonging to safety category becomes overdue for Refresher Training should be taken off duty until such time as he completes the training.\"\n\n"
                    "Mandatory for staff belonging to:\n"
                    "(i) SM/ASM\n(ii) Switchman\n(iii) Cabinman\n(iv) Guards\n(v) Drivers/Assistant Drivers\n(vi) Section Controllers\n(vii) Yard Masters.\n\n"
                    "Periodicity & Medical Classification (Annexure-II):\n"
                    "- Drivers: Refresher course 3 Weeks, Periodicity: 3 Years, Medical: A-1\n"
                    "- Assistant Drivers: Refresher course 3 Weeks, Periodicity: 3 Years, Medical: A-1\n"
                    "- Traction Power Controller / TLC / TDI: 3 Years\n"
                    "- Guards: 12 working days, 3 Years, Medical: A-2"
                ),
                'subsidiary_rule': "Crew booking kiosks (CMS) and CCC must not book any crew member whose refresher training or PME is overdue. Staff must be spared for training prior to expiry.",
                'category': 'Training & Competency',
                'key_points': "Overdue staff MUST be taken OFF DUTY immediately. 3 Weeks duration every 3 Years for Drivers/ALPs."
            },
            {
                'chapter_no': 'Railway Board Safety',
                'chapter_title': 'Operating Safety Training',
                'rule_no': 'Rly Bd 2001/SAFETY-I/13/8 (2002)',
                'rule_title': 'Combined Safety Camp & Refresher Course for Operating Staff',
                'general_rule': (
                    "In addition to mandatory refresher courses, safety categories are required to undergo 3 days of Safety Camp, "
                    "where recent accident cases and practical field problems are discussed.\n"
                    "To pull up arrears of overdue Safety Camp and avoid sparing of staff twice, the 3 days of Safety Camp is combined "
                    "in continuation with two weeks of Refresher Course for a total duration of 2½ weeks at training institutes (ZTC/ZRTI)."
                ),
                'subsidiary_rule': "Applicable to train operating and running categories to enhance safety awareness and case-based incident prevention.",
                'category': 'Training & Competency',
                'key_points': "3 days Safety Camp combined with 2 weeks Refresher = 2½ weeks combined training course."
            },
            {
                'chapter_no': 'Railway Board Safety',
                'chapter_title': 'Psychological Aptitude Screening',
                'rule_no': 'Rly Bd 2007/Safety-I/28/3 (2007)',
                'rule_title': 'Psychological Screening of High Speed Train Drivers (> 110 kmph)',
                'general_rule': (
                    "Board's directives prescribe psychological test (aptitude screening) at the stage of deployment of Drivers on high speed trains running ABOVE 110 KMPH.\n"
                    "While the Aptitude test need not be given to Drivers of Rajdhani/Shatabdi Express trains running at lower speeds, "
                    "the Drivers for deployment on non-Shatabdi/Rajdhani trains also running over 110 KMPH should be subjected to the Psycho (Aptitude) Test.\n"
                    "Divisions must maintain an active pool of psycho-tested running staff."
                ),
                'subsidiary_rule': "Only Loco Pilots who have cleared the Psycho screening and hold valid road learning shall be booked for high-speed sections (>110 kmph).",
                'category': 'Running Rules & Deployment',
                'key_points': "Mandatory Psycho Aptitude Test for deploying drivers on all trains running above 110 KMPH."
            },
            {
                'chapter_no': 'Railway Board Policy',
                'chapter_title': 'Safety Discipline & Vigilance',
                'rule_no': 'Rly Bd 2009/Safety(DM)/6/12 (Revised 2012)',
                'rule_title': 'Policy on Drunkenness on Duty - Breathalyzer & D&AR Removal Norms',
                'general_rule': (
                    "1. Preventive Strategy: Running staff (Loco Pilots, Assistant Loco Pilots, Motormen, Guards) SHALL undergo breathalyzer test BOTH at the time of Signing-ON and Signing-OFF as per Railway Board instructions.\n"
                    "2. All crew lobbies must be provided with State-of-the-art breathalyzers with memory & printout capability.\n"
                    "3. Supervisors / CLIs must carry portable breathalyzers for surprise checks on line.\n"
                    "4. No running staff allowed to sign on without undergoing breathalyzer test. Refusal treated as positive test.\n"
                    "5. PUNISHMENT NORMS FOR CATEGORY 1 (Running Staff):\n"
                    "   - Alcohol level between 1-20 mg / 100 ml of blood: Staff not allowed to perform duty, and endorsement made in service records.\n"
                    "   - Alcohol level > 21 mg / 100 ml of blood OR 2nd occasion of alcohol level between 1-20 mg: REMOVAL FROM SERVICE under D&AR.\n"
                    "6. Post-accident medical examination and blood/urine examination samples mandatory."
                ),
                'subsidiary_rule': "Zero tolerance to alcohol. Immediate relief of crew if detected positive. Random surprise checks en-route by CLIs and Officers.",
                'category': 'Safety Policy & D&AR',
                'key_points': "Mandatory Breathalyzer at Sign-ON & Sign-OFF. >21 mg/100ml alcohol or 2nd repeat = REMOVAL FROM SERVICE."
            }
        ]

        for r in rules:
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

        # Also publish high-priority notices for these policies
        if officer:
            notices_to_add = [
                {
                    'title': 'Strict Compliance: Mandatory Breathalyzer Test at Sign-ON & Sign-OFF and D&AR Action (Policy 2012)',
                    'category': 'Sr. DEE(OP) Instruction',
                    'content': 'All CCCs, CLIs, and Running Staff must strictly note: Under Railway Board Policy 2012, undergoing Breathalyzer testing is mandatory at BOTH Sign-ON and Sign-OFF. Any alcohol level > 21 mg/100ml or 2nd occasion entails REMOVAL FROM SERVICE. CLIs must conduct surprise checks with portable breathalyzers.',
                    'target_audience': 'ALL',
                    'published_by_id': officer.id,
                    'is_urgent': True
                },
                {
                    'title': 'RSRC 1998 Rule: Immediate Stoppage from Duty of Staff Overdue for Refresher Course',
                    'category': 'Sr. DEE(OP) Instruction',
                    'content': 'In terms of Railway Board letter No. 2000/Safety(A&R)/19/40, any running staff member overdue for Refresher training MUST be taken off duty immediately. CCCs must review CMS overdue lists daily and spare staff for ZRTI/DTC well in advance.',
                    'target_audience': 'ALL',
                    'published_by_id': officer.id,
                    'is_urgent': True
                },
                {
                    'title': 'SOP on Working Mail/Express Trains by LP (Goods) in Emergency (Rly Bd 2015)',
                    'category': 'Circular',
                    'content': 'Rajdhani/Shatabdi/Duronto Express shall NOT be run by LP (Goods) under any circumstances. For other Mail/Express trains in emergency, only \'A\' Grade empanelled LP (Goods) shall be utilized. If non-empanelled, an LI must accompany on the footplate without exception.',
                    'target_audience': 'ALL',
                    'published_by_id': officer.id,
                    'is_urgent': False
                }
            ]

            for nd in notices_to_add:
                if not Notice.query.filter_by(title=nd['title']).first():
                    db.session.add(Notice(**nd))
                    print(f"Added notice: {nd['title'][:40]}...")

        db.session.commit()
        print("All uploaded running rules and circulars seeded into database successfully!")

if __name__ == '__main__':
    load_rules()
