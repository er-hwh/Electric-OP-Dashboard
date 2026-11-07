from app import create_app
from database import db
from models import ELearningRule, Notice, User

app = create_app()

def load_comprehensive():
    with app.app_context():
        officer = User.query.filter_by(username='Sr. DEE(OP)/HWH').first()

        rules = [
            # 1. HPC 2016 on Duty Hours
            {
                'chapter_no': 'Duty Hours & HOER',
                'chapter_title': 'High Power Committee (HPC) on Running Staff Duty Hours',
                'rule_no': 'RBE No. 143/2016 (HPC Decision)',
                'rule_title': 'Maximum Duty Hours, Running Duty & Rest Norms for Running Staff',
                'general_rule': (
                    "Recommendations of High Power Committee (HPC) approved by Railway Board:\n"
                    "(i) Total duty at a stretch (from 'sign on' to 'sign off') shall NOT exceed 11 hours.\n"
                    "(ii) Running duty at a stretch should not ordinarily exceed 9 hours. Extension beyond 9 hrs permitted provided at least 2 hours advance notice is given to the crew, with total duty not exceeding 11 hours.\n"
                    "(iii) If train does not reach destination/crew changing point within 11 hours and such point is approximately 1 hour journey away, crew is required to work to that point provided maximum duty does not exceed 12 hours.\n"
                    "(iv) For Loco Pilots of Mail/Express trains, running duty (for link preparation) shall not exceed 8 hours (P&C time excluded).\n"
                    "(v) Headquarter Rest: Minimum 16 hours irrespective of the duration of incoming trip."
                ),
                'subsidiary_rule': "CCC and TLC must closely monitor running duty on section. Prompt relief must be arranged before reaching 9 hours running or 11 hours total duty.",
                'category': 'HOER & Duty Hours',
                'key_points': "Max 11 hrs total duty; Max 9 hrs running duty; 16 hrs HQ rest; Max 8 hrs running duty for Mail/Express links."
            },

            # 2. Periodical Rest 2023 Order
            {
                'chapter_no': 'Duty Hours & HOER',
                'chapter_title': 'Periodical Rest in CMS',
                'rule_no': 'Rly Bd 2023/Elect.(TRS)/225/6 (11.09.2023)',
                'rule_title': 'Periodical Rest of 30 Hours as Default in CMS & 22 Hours Exigency Option',
                'general_rule': (
                    "1. In accordance with High Level Committee recommendations, preference must be given to 4 periodic rests of 30 hours every month (including a full night in bed 22:00 to 06:00).\n"
                    "2. CRIS is advised to modify CMS software to set 30 HOURS REST AS DEFAULT.\n"
                    "3. The authority to grant 22 hours rest in case of operational exigencies is vested exclusively with the Chief Crew Controller (CCC) of the crew lobby."
                ),
                'subsidiary_rule': "Lobbies must not routinely reduce periodic rest to 22 hours. 30 hours rest must be ensured as the primary standard in Howrah Division.",
                'category': 'HOER & Duty Hours',
                'key_points': "30 hrs default periodic rest in CMS; 22 hrs rest only by CCC personal approval in operational exigency."
            },

            # 3. Footplate Periodicity & Safety Grading (CRIS/Board 2023)
            {
                'chapter_no': 'Footplate & Monitoring',
                'chapter_title': 'CLI Monitoring Periodicity & Crew Grading',
                'rule_no': 'Rly Bd 2012/Safety(DM)/7/25 & CRIS 2023',
                'rule_title': 'Periodicity of Footplate Inspection & Safety Grading (A, B, C) by CLIs',
                'general_rule': (
                    "Mandatory Footplate Inspection Periodicity by Nominated CLI (CMS Type-II):\n"
                    "• 'A' Category Loco Pilots: Monitored at least ONCE IN 3 MONTHS (90 Days).\n"
                    "• 'B' Category Loco Pilots: Monitored at least ONCE IN 2 MONTHS (60 Days).\n"
                    "• 'C' Category Loco Pilots: Monitored at least ONCE IN A MONTH (30 Days).\n\n"
                    "Periodicity of Review / Revising Gradation (CMS Type-VI):\n"
                    "• 'A' Category: 3 Years\n• 'B' Category: 2 Years\n• 'C' Category: 1 Year\n\n"
                    "UPGRADATION RULE: Whenever a Loco Pilot is upgraded in safety grading by CLI, it must be done ONLY WITH THE PERSONAL APPROVAL OF POWER OFFICERS (Sr. DEE(OP))."
                ),
                'subsidiary_rule': "CLI must download event recorder data and inspect continuity test, brake feel/power test, whistling at W/L boards, and VCD functioning.",
                'category': 'Footplate & CLI Duties',
                'key_points': "A Grade: 90 days; B Grade: 60 days; C Grade: 30 days. Upgradation requires Sr. DEE(OP) personal approval."
            },

            # 4. SPAD Analysis & Advisory
            {
                'chapter_no': 'Safety & SPAD Prevention',
                'chapter_title': 'Analysis of Signal Passing at Danger (SPAD)',
                'rule_no': 'Rly Bd 2015/Safety(DM)/SPAD/1',
                'rule_title': 'SPAD Statistical Findings & Preventive Footplate Action Points',
                'general_rule': (
                    "Safety Directorate analysis of SPAD cases highlights critical vigilance areas:\n"
                    "1. 60% of SPAD cases occur in passenger trains.\n"
                    "2. Departmentally promoted crew involved 2.4 times more than RRB direct recruits.\n"
                    "3. 63% of SPAD cases occur after availing complete Headquarters rest.\n"
                    "4. 70% of SPAD cases occur within the first 6 hours of duty.\n"
                    "5. Peak time period of SPAD: 06:00 to 10:00 hrs & 10:00 to 12:00 hrs.\n"
                    "6. 74% attributed to lack of alertness and negligence; 18% to delayed brake application.\n"
                    "7. Mandatory reporting of all SPAD in SIMS; strict punishment norms under D&AR."
                ),
                'subsidiary_rule': "Rigorous compliance of calling signal aspects aloud between LP and ALP (SR 3.83). Strict observance of restricted speed at Calling-on and Automatic signals.",
                'category': 'Safety Policy & D&AR',
                'key_points': "70% SPAD within first 6 hrs; 60% in passenger trains; calling aspects aloud and timely braking are essential."
            },

            # 5. Unified Road Learning SR 3.78(6)
            {
                'chapter_no': 'Road Learning',
                'chapter_title': 'Unified Road Learning Rules',
                'rule_no': 'Rly Bd 2017/Safety(DM)/7/25/Pt./4 (2018/2019)',
                'rule_title': 'Unified Road Learning under GR 3.78(6) & Lapsing Schedule',
                'general_rule': (
                    "1. Initial Road Learning: 3 trips (Up and Down separately), of which at least ONE trip must be by NIGHT.\n"
                    "2. Ghat Section & Automatic Block Territories: Minimum SIX TRIPS in both directions. If multiple lines, at least 1 trip in each line.\n"
                    "3. Road Learning Lapsing Schedule:\n"
                    "   • 3 to 6 months absence: 1 trip in plains / 3 trips in Ghat & Automatic.\n"
                    "   • 6 months to 2 years absence: 2 trips in plains / 3 trips in Ghat & Automatic.\n"
                    "   • Over 2 years absence: 3 trips in plains / 6 trips in Ghat & Automatic.\n"
                    "4. Crew Booking Alert: Crew must record in register 15 days in advance that road learning is lapsing.\n"
                    "5. New IBS Commissioning: Road learning trip not required; issue Caution Order for 90 days."
                ),
                'subsidiary_rule': "Crew booking supervisor (CCC) is personally held responsible for booking any crew without valid road learning.",
                'category': 'Running Rules & Deployment',
                'key_points': "3 trips initial (1 night); 6 trips for Automatic/Ghat; 90 days caution order for new IBS."
            },

            # 6. 7th CPC Running Allowance & KMA Rates
            {
                'chapter_no': 'Running Allowances',
                'chapter_title': '7th CPC Running Allowance & KMA Rates',
                'rule_no': 'RBE No. 85/2019 & RBE No. 85/2017',
                'rule_title': 'Kilometreage Allowance (KMA), ALK & Additional Allowance Rates',
                'general_rule': (
                    "1. Pay Element: 30% of basic pay for specified benefits; 55% for retirement benefits (30% for CLIs pensionary benefits).\n"
                    "2. Revised Rates of KMA per 100 KMs (7th CPC):\n"
                    "   • Loco Pilot (Mail/Express): ₹530 / 100 km (ALK 160 kms: ₹848)\n"
                    "   • Loco Pilot (Passenger) / Sr. Motorman: ₹525 / 100 km (ALK: ₹840)\n"
                    "   • Loco Pilot (Goods): ₹520 / 100 km (ALK: ₹832)\n"
                    "   • Loco Pilot (Shunting) Gr. I: ₹403 / 100 km (ALK: ₹645)\n"
                    "   • Loco Pilot (Shunting) Gr. II: ₹391 / 100 km (ALK: ₹626)\n"
                    "   • Sr. Assistant Loco Pilot: ₹391 / 100 km (Shunting: ₹251, ALK: ₹626)\n"
                    "   • Assistant Loco Pilot: ₹376 / 100 km (Shunting: ₹242, ALK: ₹602)\n"
                    "3. Additional Allowance (RBE 85/2017):\n"
                    "   • LP (Mail/Express): ₹2,250 / month\n"
                    "   • LP (Passenger) / Motorman: ₹1,125 / month\n"
                    "   • LP (Goods): ₹750 / month\n"
                    "4. Trip Allowance for High Speed Trains (> 110 kmph): LP: ₹75, Co-LP: ₹56, ALP: ₹37."
                ),
                'subsidiary_rule': "Running allowance bills must be verified against CMS electronic trip journals.",
                'category': 'Allowances & Running Rules',
                'key_points': "KMA: ₹530 LPM, ₹525 LPP/MMAN, ₹520 LPG, ₹376 ALP. Addl Allowance: ₹2250 LPM, ₹1125 LPP, ₹750 LPG."
            },

            # 7. Officiating in Higher Running Post (ACS 262 to IREM)
            {
                'chapter_no': 'Establishment & Promotion',
                'chapter_title': 'Officiating Allowance in Higher Running Post',
                'rule_no': 'RBE No. 29/2019 (ACS No. 262 to IREM-I)',
                'rule_title': 'Running Allowance Enhancement by 15% for Officiating in Higher Running Grade',
                'general_rule': (
                    "Advance Correction Slip No. 262 to IREM Vol-I Rule 913:\n"
                    "\"When running staff are put to officiate in a running post for 30 days or less, they shall be entitled to pay as admissible in the lower grade PLUS Running Allowance at the rates and on the condition applicable to the higher grade in which they officiate, ENHANCED BY 15% of the kilometreage actually performed for every such higher grade.\""
                ),
                'subsidiary_rule': "CCC and Bill Clerks must compute 15% enhanced KMA for running staff officiating as LP Goods or LP Passenger.",
                'category': 'Allowances & Running Rules',
                'key_points': "Pay in lower grade + Higher grade KMA enhanced by 15% for officiating &le; 30 days."
            },

            # 8. Promotional Stage-wise Training & Exemption (RBE 39/2003)
            {
                'chapter_no': 'Training & Competency',
                'chapter_title': 'Refresher vs Promotional Course Alignment',
                'rule_no': 'RBE No. 39/2003 (E(MPP)98/3/8)',
                'rule_title': 'Exemption from Refresher Course when Empanelled for Promotional Course',
                'general_rule': (
                    "If running staff due for Refresher Course gets empanelled/scheduled for Promotional Course, "
                    "they may be EXEMPTED from Refresher Course and sent to Promotional Course directly, provided:\n"
                    "• The gap between the scheduled date of Refresher Course and Promotional Course is NOT MORE THAN 3 MONTHS.\n"
                    "• If the gap is more than 3 months, employee must undergo BOTH courses.\n"
                    "• In all cases, staff overdue for Refresher Course must be taken off duty as per RSRC 1998 until completion."
                ),
                'subsidiary_rule': "Coordinated by Divisional Training Cell with Principal ZRTI Bhuli.",
                'category': 'Training & Competency',
                'key_points': "Exemption from Refresher if Promotional course is within 3 months; else attend both."
            },

            # 9. Psychological / Aptitude Test in Selections (RB 2007)
            {
                'chapter_no': 'Selection & Aptitude',
                'chapter_title': 'Psychological Screening Rules',
                'rule_no': 'RB/Estt. No. 44/2007 & RB No. 57/2005',
                'rule_title': 'Hands-on Practice Session and Multiple Cut-Off Scoring in Aptitude Tests',
                'general_rule': (
                    "1. Candidates appearing in Aptitude Test (Psychological Screening) for safety category selections (ALP, Motorman, ASM) "
                    "shall be called A DAY PRIOR to the test for hands-on practice sessions to familiarize with the test batteries.\n"
                    "2. Qualifying Standard: System of MULTIPLE CUT-OFF is strictly followed. Candidates must score at or above the minimum qualifying cut-off in EACH sub-test of the test battery.\n"
                    "3. Candidates failing in the Aptitude Test can appear again in subsequent selections."
                ),
                'subsidiary_rule': "Aptitude tests are administered by RDSO certified Psycho-technical testing officers.",
                'category': 'Selection & Aptitude',
                'key_points': "Practice session 1 day prior; Must pass minimum cut-off in EACH sub-test battery."
            }
        ]

        for r in rules:
            existing = ELearningRule.query.filter_by(rule_no=r['rule_no']).first()
            if not existing:
                db.session.add(ELearningRule(**r))
                print(f"Added comprehensive rule: {r['rule_no']}")
            else:
                existing.general_rule = r['general_rule']
                existing.subsidiary_rule = r['subsidiary_rule']
                existing.category = r['category']
                existing.key_points = r['key_points']
                print(f"Updated comprehensive rule: {r['rule_no']}")

        # Add High Power Committee (HPC) Notice
        if officer:
            n_hpc = {
                'title': 'Strict Compliance: HPC 2016 Norms on Running Staff Duty Hours & 16 Hours HQ Rest',
                'category': 'Sr. DEE(OP) Instruction',
                'content': 'All CCCs, CLIs, and Running Staff of Howrah Division must adhere strictly to RBE 143/2016: Total duty from sign-on to sign-off shall not exceed 11 hours. Running duty shall not exceed 9 hours without 2 hours advance notice. Full 16 hours headquarter rest is mandatory for all running staff irrespective of incoming trip duration.',
                'target_audience': 'ALL',
                'published_by_id': officer.id,
                'is_urgent': True
            }
            if not Notice.query.filter_by(title=n_hpc['title']).first():
                db.session.add(Notice(**n_hpc))
                print("Added Notice on HPC Duty Hours")

        db.session.commit()
        print("Comprehensive running rules loaded successfully into database!")

if __name__ == '__main__':
    load_comprehensive()
