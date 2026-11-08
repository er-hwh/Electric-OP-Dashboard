from datetime import datetime, date, timedelta
from app import create_app
from database import db
from models import (
    Lobby, User, Notice, CounsellingTopic, TrainingRecord, 
    OfficerSay, ELearningRule, PhotoGallery, CrewCounsellingRecord
)

app = create_app()

def seed():
    with app.app_context():
        # Create all tables in MySQL
        db.create_all()
        print("Database tables verified.")

        # 1. Seed Lobbies (9 Main Lobbies + 3 Sister Lobbies)
        lobby_data = [
            ("RPH", "Rampurhat Lobby", "03461-255-321", "Sri Badal Mondal (CCC/RPH)", False, "Loop Line Operation & Freight Lobby"),
            ("BWN", "Barddhaman Lobby", "0342-2621-234", "Sri Brajesh Kumar Sinha (CCC/BWN)", False, "Main Line & Chord Junction Lobby"),
            ("HWH", "Howrah Lobby", "033-2660-1234", "Sri Prasanta Panja (CCC/HWH)", False, "Headquarters Main Electric & EMU Running Lobby"),
            ("DKAE", "Dankuni Lobby", "033-2659-9988", "Mr. Pijush Ghosh (CCC/DKAE)", False, "Freight Complex & Coaching Yard Base"),
            ("BHP", "Bolpur Shantiniketan Lobby", "03463-252-440", "Sri T. K. Sen (CCC/BHP)", False, "Passenger & Express Crew Booking Depot"),
            ("TAK", "Tarakeswar Lobby", "03212-276-300", "Sri Mintu Pal (CCC/TAK)", False, "Suburban EMU High Frequency Line Lobby"),
            ("AZ", "Azimganj Lobby", "03483-253-400", "Sri Amalendu Malakar (CCC/AZ)", False, "Murshidabad Section Branch & Main Operation"),
            ("KWAE", "Katwa Lobby", "03453-255-120", "Sri Bidhan Chandra Ray (CCC/KWAE)", False, "Bandel-Katwa-Azimganj Section Lobby"),
            ("PKR", "Pakur Lobby", "06435-222-111", "Sri D. K. Sharma (CCC/PKR)", False, "Stone Loading & Heavy Freight Operation Lobby"),
            # Sister Lobbies
            ("NHT", "Nalhati Sister Lobby", "03465-257-890", "Operated under RPH/AZ", True, "Nalhati-Azimganj Link Crew Base (Sister Lobby to RPH/AZ)"),
            ("SNT", "Sainthia Sister Lobby", "03462-222-100", "Operated under RPH", True, "Sainthia Junction Loop & Freight Operational Base (Sister Lobby to RPH)"),
            ("KURV", "KURVA Sister Lobby", "0342-2700-111", "Operated under BWN", True, "KURVA Freight Marshalling & Yard Operation (Sister Lobby to BWN)")
        ]

        lobbies = {}
        for code, name, phone, ccc, is_sister, desc in lobby_data:
            lobby = Lobby.query.filter_by(code=code).first()
            if not lobby:
                lobby = Lobby(code=code, name=name, phone=phone, ccc_name=ccc, is_sister_lobby=is_sister, description=desc)
                db.session.add(lobby)
                db.session.flush()
            else:
                lobby.name = name
                lobby.ccc_name = ccc
                lobby.phone = phone
                lobby.is_sister_lobby = is_sister
                lobby.description = desc
            lobbies[code] = lobby

        db.session.commit()
        print("12 Lobbies (9 Main + 3 Sister) verified.")

        # 2. Seed Admin, Officers, and Control (TLC / PCNL)
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                role='admin',
                sub_role='System Administrator',
                full_name='Divisional System Admin',
                mobile='9000000000',
                email='admin.electop@er.railnet.gov.in',
                pf_number='ADM001',
                password_must_change=True
            )
            admin.set_password('12345')
            db.session.add(admin)

        # Control Users: TLC (Electric Traction Control) & PCNL (Diesel Power Control)
        controls_info = [
            ('TLC', 'TLC', 'Traction Loco Control / TLC HWH (Electric)', '9002022390', 'tlc.hwh@er.railnet.gov.in', 'TLC001'),
            ('PCNL', 'PCNL', 'Power Control / PCNL HWH (Diesel)', '9002022391', 'pcnl.hwh@er.railnet.gov.in', 'PCNL001'),
            ('CNL_HWH', 'CNL', 'Chief Power Controller / CNL HWH', '9002022399', 'cnl.hwh@er.railnet.gov.in', 'CNL001')
        ]
        for uname, srole, fname, mob, email, pf in controls_info:
            ctrl_user = User.query.filter_by(username=uname).first()
            if not ctrl_user:
                ctrl_user = User(
                    username=uname,
                    role='control',
                    sub_role=srole,
                    full_name=fname,
                    mobile=mob,
                    email=email,
                    pf_number=pf,
                    password_must_change=True
                )
                ctrl_user.set_password('12345')
                db.session.add(ctrl_user)

        # Officers (Master Requirement Draft: SR_DEEOP_HWH, AEEOP_HWH, AMEP_HWH)
        officers_info = [
            ('SR_DEEOP_HWH', 'Sr. DEE(OP)', 'Sri Arun Kumar Rana, IRSEE', 'Senior Divisional Electrical Engineer (OP)', '9002022300', 'srdee.op.hwh@er.railnet.gov.in', 'OFF001'),
            ('AEEOP_HWH', 'AEE(OP)', 'Sri Sourav Nandi', 'Assistant Electrical Engineer (OP)', '9002022301', 'aee.op.hwh@er.railnet.gov.in', 'OFF002'),
            ('AMEP_HWH', 'AME(P)', 'Sri Vishwambhar Prasad', 'Assistant Mechanical Engineer (Power)', '9002022302', 'ame.p.hwh@er.railnet.gov.in', 'OFF003'),
            ('DEE(OP)/HWH', 'DEE(OP)', 'Sri S. K. Pathak', 'Divisional Electrical Engineer (OP)', '9002022305', 'dee.op.hwh@er.railnet.gov.in', 'OFF004')
        ]

        officer_objs = {}
        for uname, subrole, fname, desig, mob, email, pf in officers_info:
            officer = User.query.filter_by(username=uname).first()
            if not officer:
                officer = User(
                    username=uname,
                    role='officer',
                    sub_role=subrole,
                    full_name=fname,
                    mobile=mob,
                    email=email,
                    pf_number=pf,
                    password_must_change=True
                )
                officer.set_password('12345')
                db.session.add(officer)
                db.session.flush()
            officer_objs[uname] = officer

        # 3. Seed Supervisors (CLIs) & Lobby In-Charges
        supervisors_info = [
            ('CLI_HWH_01', 'CLI', 'Sri Pradip Roy', 'Chief Loco Inspector (HWH)', '9830111101', 'HWH', 'CLI1001'),
            ('CLI_BWN_01', 'CLI', 'Sri Ramen Majumdar', 'Chief Loco Inspector (BWN)', '9830111102', 'BWN', 'CLI1002'),
            ('CLI_RPH_01', 'CLI', 'Sri Joydeb Karmakar', 'Chief Loco Inspector (RPH)', '9830111103', 'RPH', 'CLI1003'),
            ('CLI_DKAE_01', 'CLI', 'Sri Sanjay Bhattacharjee', 'Chief Loco Inspector (DKAE)', '9830111104', 'DKAE', 'CLI1004'),
            ('CLI_AZ_01', 'CLI', 'Sri Amalendu Malakar', 'Chief Loco Inspector (AZ)', '9830111105', 'AZ', 'CLI1005'),
            ('CLI_PKR_01', 'CLI', 'Sri D. K. Sharma', 'Chief Loco Inspector (PKR)', '9830111106', 'PKR', 'CLI1006'),
            ('CCC_HWH', 'CCC', 'Sri S. K. Roy', 'Chief Crew Controller (HWH)', '9830111107', 'HWH', 'CCC2001')
        ]

        cli_objs = {}
        for uname, subrole, fname, desig, mob, lcode, pf in supervisors_info:
            cli = User.query.filter_by(username=uname).first()
            if not cli:
                cli = User(
                    username=uname,
                    role='supervisor',
                    sub_role=subrole,
                    full_name=fname,
                    mobile=mob,
                    email=f"{uname.lower()}@er.railnet.gov.in",
                    pf_number=pf,
                    lobby_id=lobbies[lcode].id,
                    password_must_change=True
                )
                cli.set_password('12345')
                db.session.add(cli)
                db.session.flush()
            cli_objs[uname] = cli

        # Map In-Charge CLIs to Lobbies
        lobby_cli_map = {
            'HWH': 'CLI_HWH_01',
            'TAK': 'CLI_HWH_01',
            'BWN': 'CLI_BWN_01',
            'KURV': 'CLI_BWN_01',
            'RPH': 'CLI_RPH_01',
            'NHT': 'CLI_RPH_01',
            'SNT': 'CLI_RPH_01',
            'DKAE': 'CLI_DKAE_01',
            'AZ': 'CLI_AZ_01',
            'KWAE': 'CLI_AZ_01',
            'PKR': 'CLI_PKR_01',
            'BHP': 'CLI_PKR_01'
        }
        for lcode, cli_uname in lobby_cli_map.items():
            if lcode in lobbies and cli_uname in cli_objs:
                lobbies[lcode].in_charge_cli_id = cli_objs[cli_uname].id
        db.session.commit()
        print("Lobby in-charge CLIs mapped successfully.")

        # 4. Seed Sample Running Staff (Crews) mapped to CLIs
        crews_info = [
            ('9876543210', 'LPM', 'Sunil Kumar Mondal', 'CLI_HWH_01', 'HWH', '50201234567', 'HRMS-LPM01'),
            ('9876543211', 'MMAN', 'Bikash Chandra Paul', 'CLI_HWH_01', 'HWH', '50201234568', 'HRMS-MM01'),
            ('9876543212', 'LPG', 'Tarun Kanti Ghosh', 'CLI_BWN_01', 'BWN', '50201234569', 'HRMS-LPG01'),
            ('9876543213', 'ALP', 'Subhasish Chatterjee', 'CLI_HWH_01', 'HWH', '50201234570', 'HRMS-ALP01'),
            ('9876543214', 'Sr. ALP', 'Kalyan Roy', 'CLI_RPH_01', 'RPH', '50201234571', 'HRMS-SRALP01'),
            ('9876543215', 'LPP', 'Asim Das', 'CLI_DKAE_01', 'DKAE', '50201234572', 'HRMS-LPP01'),
            ('9876543216', 'LPS-II', 'Ranjan Mukherjee', 'CLI_HWH_01', 'HWH', '50201234573', 'HRMS-LPS01'),
            ('9876543217', 'LPS-I', 'Gouranga Halder', 'CLI_BWN_01', 'BWN', '50201234574', 'HRMS-LPS02')
        ]

        crew_objs = []
        for mob, subrole, fname, cli_key, lcode, pf, hrms in crews_info:
            crew = User.query.filter_by(username=mob).first()
            if not crew:
                crew = User(
                    username=mob,
                    role='crew',
                    sub_role=subrole,
                    full_name=fname,
                    mobile=mob,
                    email=f"{mob}@runningcrew.railnet",
                    pf_number=pf,
                    hrms_id=hrms,
                    lobby_id=lobbies[lcode].id,
                    cli_id=cli_objs[cli_key].id,
                    password_must_change=True
                )
                crew.set_password('12345')
                db.session.add(crew)
                db.session.flush()
            crew_objs.append(crew)

        # 4b. Seed 24-Column CrewCounsellingRecords matching hwh-division-operation-dashboard schema
        for crew, (mob, subrole, fname, cli_key, lcode, pf, hrms) in zip(crew_objs, crews_info):
            rec = CrewCounsellingRecord.query.filter_by(crew_user_id=crew.id).first()
            if not rec:
                rec = CrewCounsellingRecord(
                    crew_user_id=crew.id,
                    crew_id_str=f"{lcode}{crew.id:04d}",
                    cli_name=cli_objs[cli_key].full_name,
                    crew_name=crew.full_name,
                    crew_hq=lcode,
                    cug=mob,
                    designation=subrole,
                    designation_since="15-01-2022",
                    pf_no=pf,
                    grade="A" if "LPM" in subrole or "MMAN" in subrole else "B",
                    last_footplate=(date.today() - timedelta(days=22)).strftime("%d-%m-%Y"),
                    technical_counselling=(date.today() - timedelta(days=18)).strftime("%d-%m-%Y"),
                    safety_counselling=(date.today() - timedelta(days=12)).strftime("%d-%m-%Y"),
                    counselling_verified_by=cli_objs[cli_key].full_name,
                    last_spm_check=(date.today() - timedelta(days=25)).strftime("%d-%m-%Y"),
                    last_cvvrs_check=(date.today() - timedelta(days=20)).strftime("%d-%m-%Y"),
                    ba_fail_history="Nil",
                    mobile_habit="Normal",
                    spad_history="Nil",
                    da_case="Nil",
                    family_issue="Nil",
                    health_issue="Nil",
                    baby_below_6_months="No",
                    accident_prone="No",
                    remarks="Good road knowledge and attentive on footplate."
                )
                db.session.add(rec)
        db.session.commit()

        # 5. Seed Officer's Desk Messages ("Officers Say")
        officer_says = [
            {
                'designation': 'Sr. DEE(OP)/HWH',
                'officer_name': 'Mr. Arun Kumar Rana (IRSEE)',
                'tagline': 'Zero Tolerance to SPAD & Absolute Safety in High-Speed Running',
                'photo_filename': 'officer_sr_dee.jpg',
                'message': 'Welcome to the digital portal of the Electric Operation Department, Howrah Division. Our foremost priority is absolute safety on track, punctuality, and unwavering alertness of running staff. Every Loco Pilot, Motorman, and Assistant Loco Pilot must stringently comply with General & Subsidiary Rules, rigorously perform brake feel and continuity tests, and maintain continuous mutual vigilance on footplate. Safety is not a matter of chance, it is a conscious commitment.',
                'priority_order': 1
            },
            {
                'designation': 'AEE(OP)/HWH',
                'officer_name': 'Mr. Sourav Nandi',
                'tagline': 'Meticulous Inspection, Timely Counselling & Enhanced Skill Upgradation',
                'photo_filename': 'officer_aee.jpg',
                'message': 'Chief Loco Inspectors are the backbone of crew management. Consistent footplate monitoring, identifying deficiencies before they turn into unusual occurrences, and providing real-time psychological and technical counselling are vital. Ensure all running staff complete their mandatory refresher, PME, and Automatic Block competencies strictly within due dates.',
                'priority_order': 2
            },
            {
                'designation': 'AME(P)/HWH',
                'officer_name': 'Mr. Viwshambhar Prasad',
                'tagline': 'Optimal Energy Efficiency & Locomotive Health Assurance',
                'photo_filename': 'officer_ame.jpg',
                'message': 'Traction rolling stock reliability depends directly on disciplined handling. Strict adherence to Neutral Section coasting procedures, vigilant OHE monitoring, correct whistle codes, and prompt reporting of any pantograph or undergear abnormalities save valuable divisional assets and avert delays.',
                'priority_order': 3
            }
        ]

        for osay in officer_says:
            if not OfficerSay.query.filter_by(designation=osay['designation']).first():
                db.session.add(OfficerSay(**osay))

        sr_dee = officer_objs.get('SR_DEEOP_HWH') or officer_objs.get('Sr. DEE(OP)/HWH')
        aee = officer_objs.get('AEEOP_HWH') or officer_objs.get('AEE(OP)/HWH')

        # 6. Seed Sr. DEE(OP) Instructions & Notices
        sample_notices = [
            {
                'title': 'Safety Drive: Observance of Foggy Weather Precautions as per GR 3.61 & SR 4.50',
                'category': 'Sr. DEE(OP) Instruction',
                'content': 'All Running Staff (LPM/LPP/MMAN/LPG/ALP) must ensure strict observance of maximum speed restrictions in foggy and tempestuous weather. Speed in Absolute Block must never exceed 60 KMPH. Sound intermittent W/L whistle and ensure proper use of Fog Pass / Detonators as laid down.',
                'target_audience': 'ALL',
                'published_by_id': sr_dee.id,
                'is_urgent': True
            },
            {
                'title': 'Intensive Inspection on Neutral Section Coasting and DJ Tripping Procedures',
                'category': 'Sr. DEE(OP) Instruction',
                'content': 'Under Chapter XVII Rule 17.07, all Loco Pilots and Motormen are instructed to coast through Neutral Sections only after opening the Circuit Breaker (DJ) and dropping pantograph where notified. Do not attempt re-closing inside dead zones.',
                'target_audience': 'ALL',
                'published_by_id': sr_dee.id,
                'is_urgent': True
            },
            {
                'title': 'Mandatory Exchange of All-Right Signals with Station Staff and Guard (SR 4.42)',
                'category': 'Notice',
                'content': 'All running staff must exchange All-Right signals without fail on both sides while passing stations and cabins. In EMU trains, bell signal code 00 must be acknowledged properly.',
                'target_audience': 'CREW_ONLY',
                'published_by_id': aee.id,
                'is_urgent': False
            },
            {
                'title': 'Provisional Seniority List of Loco Pilot Mail/Express (LPM) - Howrah Division 2026',
                'category': 'Seniority',
                'content': 'The provisional seniority list of Loco Pilot Mail/Express (Level-6) of Electric OP, Howrah Division is published for information of all concerned. Representations if any may be submitted via nominated CLI within 21 days.',
                'target_audience': 'ALL',
                'published_by_id': sr_dee.id,
                'is_urgent': False
            },
            {
                'title': 'Result of Promotional Suitability Test for LPG to LPP Selection (Batch Oct-2026)',
                'category': 'Result',
                'content': 'Following candidates from Howrah, Barddhaman, and Rampurhat lobbies have successfully qualified the promotional training and suitability test for the post of Loco Pilot Passenger (LPP).',
                'target_audience': 'ALL',
                'published_by_id': sr_dee.id,
                'is_urgent': False
            }
        ]

        for n_data in sample_notices:
            if not Notice.query.filter_by(title=n_data['title']).first():
                db.session.add(Notice(**n_data))

        # 7. Seed Daily Counselling Topics & Case Analyses
        sample_counselling = [
            {
                'topic_date': date.today(),
                'title': 'Case Analysis: Analysis of Uncoupling Incident in BZLE-TYAE Section and RS Valve Application',
                'content': '''Key Points for Footplate Counselling:
1. Ensure proper visual examination of transition couplers and CBC locks before departure.
2. In case of air pressure / vacuum drop, ALP must visually inspect the rake and angle cocks without delay as per SR 4.31.
3. Observe speed restriction on falling gradients in accordance with SR 4.14 / SR 4.48.
4. Continuous mutual calling of signal aspects between LP and ALP (SR 3.83).''',
                'case_analysis': 'On 26.05.2026 at BZLE-TYAE section, uncoupling of load occurred. The investigation revealed improper locking check during engine changeover. Loco Pilots are cautioned that coupling integrity must be physically checked in presence of Guard before signing joint BPC memo.',
                'rule_reference': 'GR 4.32, SR 4.31, SR 6.08 (Train Parting)',
                'issued_by_id': sr_dee.id
            },
            {
                'topic_date': date.today() - timedelta(days=1),
                'title': 'Signal Passing at Danger (SPAD) Prevention: Sighting Distance & Calling-on Arm Observance',
                'content': '''1. Never exceed 15 KMPH when passing a Calling-on Signal taken "OFF" (GR 3.13 / GR 3.79).
2. When approaching a Stop signal at "ON", bring train to complete stop 100 metres in rear.
3. In Automatic territory, after stopping at Red with 'A' marker (1 min day / 2 min night), proceed at speed not exceeding 15 KMPH under strict caution (GR 9.02).''',
                'case_analysis': 'Analysis of near-miss incidents shows lack of communication between ALP and LP in suburban EMU/MEMU sections. ALP must remain in front cab while approaching any station or junction signal.',
                'rule_reference': 'GR 3.79, GR 3.80, GR 9.02, SR 3.83',
                'issued_by_id': aee.id
            }
        ]

        for c_data in sample_counselling:
            if not CounsellingTopic.query.filter_by(title=c_data['title']).first():
                db.session.add(CounsellingTopic(**c_data))

        # 8. Seed Training Records
        sample_training = [
            (crew_objs[0].id, 'Refresher ELEC', 'ZRTI Bhuli', date.today() - timedelta(days=700), date.today() + timedelta(days=395), 'ZRTI/EL/2024/991', 'Valid'),
            (crew_objs[0].id, 'Automatic Block System', 'DTC Howrah', date.today() - timedelta(days=160), date.today() + timedelta(days=20), 'DTC/ABS/2026/102', 'Due within 30 days'),
            (crew_objs[1].id, 'Refresher EMU/MEMU', 'DTC Howrah', date.today() - timedelta(days=1100), date.today() - timedelta(days=5), 'DTC/EMU/2023/45', 'Overdue for refresher'),
            (crew_objs[1].id, 'PME (Medical Category A-1)', 'B.R. Singh Hospital', date.today() - timedelta(days=300), date.today() + timedelta(days=65), 'PME/BRS/2025/782', 'Valid'),
            (crew_objs[2].id, 'Refresher DSL', 'ZRTI Bhuli', date.today() - timedelta(days=800), date.today() + timedelta(days=295), 'ZRTI/DSL/2024/31', 'Valid'),
            (crew_objs[3].id, 'Initial Induction (ELEC & GR&SR)', 'ZRTI Bhuli', date.today() - timedelta(days=200), date.today() + timedelta(days=895), 'ZRTI/IND/2026/410', 'Initial Training Completed')
        ]

        for cid, ttype, inst, last_d, due_d, cert, rem in sample_training:
            rec = TrainingRecord.query.filter_by(crew_id=cid, training_type=ttype).first()
            if not rec:
                rec = TrainingRecord(
                    crew_id=cid,
                    training_type=ttype,
                    institute=inst,
                    last_done_date=last_d,
                    due_date=due_d,
                    certificate_no=cert,
                    remarks=rem
                )
                db.session.add(rec)

        # 9. Seed GR & SR Rules Repository
        rules_data = [
            ("Chapter III", "Signals", "GR 3.61", "Placing of detonators in thick, foggy or tempestuous weather", 
             "In thick, foggy or tempestuous weather impairing visibility, whenever it is necessary to indicate to the Loco Pilot of an approaching train the locality of a signal, two detonators shall be placed on the line, about 10 metres apart, and at least 270 metres outside the signal concerned.",
             "SR 3.61(d): In foggy weather when station signals cannot be seen, the Station Master shall send two trained men to act as fog signalmen outside the first stop signal. Placement not required where double Distant signals are provided or reliable Fog Safe Device exists on locomotive.",
             "Detonators / Foggy Weather", "2 detonators 10m apart, 270m in rear of First Stop Signal."),
            
            ("Chapter IV", "Working of Trains", "GR 4.09", "Caution Order (Forms T/409, T/A 409, T/B 409)",
             "Whenever, in consequence of the line being under repair or for any other reason, special precautions are necessary, a Caution Order detailing kilometres and speed shall be handed to the Loco Pilot.",
             "SR 4.09: Issued in Form T/409 (on green paper / green font). 'NIL' Caution Order is Form T/A 409. Reminder Caution Order is Form T/B 409. Record foils preserved for 12 months.",
             "Caution Orders", "T/409 Caution Order, T/A 409 Nil Caution, T/B 409 Reminder Caution."),

            ("Chapter IV", "Working of Trains", "SR 4.50", "Sounding of Engine Whistle & Whistle Codes",
             "Loco Pilots must sound whistle according to prescribed code: 'O' short whistle, 'â€”' long whistle.",
             "SR 4.50(a): 0-0 Passing stop signal at ON on proper authority; â€” â€” 0 Opening circuit breaker [DJ]; 0000 Accident / train cannot proceed; â€” continuous Approaching tunnel/cutting/W-L board.",
             "Whistle Codes", "Whistle codes are mandatory for safety communication."),

            ("Chapter XVII", "Electrified Sections", "GR 17.07", "Tripping of Circuit Breakers at Neutral Sections",
             "Loco Pilot of electric locomotive or EMU shall coast through the neutral section, duly switching off power.",
             "SR 17.07: Warning boards for Neutral Section are fixed 500m and 250m ahead. At switch-off point, Board Fig III is provided. At switch-on point, Board Fig IV is provided. Brakes must be fully released before entering.",
             "OHE & Traction", "Warning at 500m & 250m; switch off DJ; coast through; switch on after Fig IV board."),

            ("Chapter IX", "Automatic Block", "GR 9.02", "Automatic Stop Signal passed at 'ON'",
             "When Loco Pilot finds an Automatic Stop Signal with 'A' marker at 'ON', bring train to stop. Wait 1 minute by day, 2 minutes by night. If still ON, sound whistle, exchange signal with Guard, proceed at restricted speed.",
             "SR 9.02(i): Proceed with great caution not exceeding 15 KMPH even if visibility is clear. Maintain minimum distance of 150m (75m for EMU) or two OHE spans from preceding train. During dense fog, max speed 10 KMPH.",
             "Automatic Signalling", "Wait 1 min day / 2 min night, max 15 kmph, dense fog 10 kmph, 150m spacing.")
        ]

        for c_no, c_title, r_no, r_title, gr, sr, cat, kp in rules_data:
            if not ELearningRule.query.filter_by(rule_no=r_no).first():
                db.session.add(ELearningRule(
                    chapter_no=c_no,
                    chapter_title=c_title,
                    rule_no=r_no,
                    rule_title=r_title,
                    general_rule=gr,
                    subsidiary_rule=sr,
                    category=cat,
                    key_points=kp
                ))

        db.session.commit()
        print("Seed data successfully inserted into MySQL database.")

if __name__ == '__main__':
    seed()
