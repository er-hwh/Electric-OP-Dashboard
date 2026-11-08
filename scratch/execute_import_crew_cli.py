import os
import sys
import shutil
import re
from datetime import datetime, date

sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages")
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard")

import openpyxl
from app import create_app
from database import db
from models import User, Lobby

# Source files from user upload
src_crew_xlsx = r"C:\Users\Indian Railway\.gemini\antigravity\brain\e1c72f05-a097-45cf-9a3f-9cf48417738e\.user_uploaded\media_1794145035877_2afaaa06.xlsx"
src_cli_xlsx = r"C:\Users\Indian Railway\.gemini\antigravity\brain\e1c72f05-a097-45cf-9a3f-9cf48417738e\.user_uploaded\media_1794145049955_7edc5207.xlsx"

# Target paths in supporting data
base_dir = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard"
supp_dir = os.path.join(base_dir, "supporting data")
os.makedirs(supp_dir, exist_ok=True)

tgt_crew_xlsx = os.path.join(supp_dir, "crew_data_uploaded.xlsx")
tgt_cli_xlsx = os.path.join(supp_dir, "cli_biodata_uploaded.xlsx")

print("1. Copying raw uploaded Excel files to supporting data...")
shutil.copy2(src_crew_xlsx, tgt_crew_xlsx)
shutil.copy2(src_cli_xlsx, tgt_cli_xlsx)
print(f"Saved: {tgt_crew_xlsx} and {tgt_cli_xlsx}")

def parse_date_safe(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ['none', 'null', '-', 'na', '']:
        return None
    val_str = val_str.split(' ')[0]
    for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%b-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            pass
    return None

def clean_mobile(val):
    if not val:
        return ''
    digits = ''.join(c for c in str(val) if c.isdigit())
    if len(digits) == 12 and digits.startswith('91'):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith('0'):
        digits = digits[1:]
    return digits[:15]

def clean_str(val):
    if val is None:
        return ''
    s = str(val).strip()
    if s.endswith('.0') and not s.endswith('..0'):
        base = s[:-2]
        if base.replace('-', '').isdigit():
            s = base
    return s

def run_import():
    app = create_app()
    with app.app_context():
        print("\n2. Checking and creating Lobbies...")
        # Ensure BDC lobby exists
        bdc = Lobby.query.filter_by(code='BDC').first()
        if not bdc:
            bdc = Lobby(
                code='BDC',
                name='Bandel Lobby',
                phone='033-2631-2222',
                ccc_name='CCC Bandel',
                operational_jurisdiction='Bandel - Howrah / Bandel - Katwa / Bandel - Naihati sections',
                description='Bandel Junction Electric & Diesel Running Depot'
            )
            db.session.add(bdc)
            db.session.commit()
            print("Created Bandel Lobby (BDC).")

        lobbies = {l.code.upper(): l for l in Lobby.query.all()}
        print(f"Active lobbies: {list(lobbies.keys())}")

        print("\n3. Processing CLI Biodata (60 records)...")
        wb_cli = openpyxl.load_workbook(tgt_cli_xlsx, data_only=True)
        ws_cli = wb_cli.active

        cli_count = 0
        cli_map = {} # full_name_clean -> user_id

        # Headers on row 3: [S.No, LI ID, NAME, FATHER NAME, HQ, DOB*, DOA*, DOP*, EMP NO, PAN NO, QUALIFICATION, BASIC PAY, DESIG, MOBILE NO, ADDRESS]
        for row in ws_cli.iter_rows(min_row=4, values_only=True):
            li_id = clean_str(row[1]).upper()
            if not li_id or not li_id.startswith('HWH'):
                continue

            name = clean_str(row[2])
            father = clean_str(row[3])
            hq = clean_str(row[4]).upper()
            dob = parse_date_safe(row[5])
            doa = parse_date_safe(row[6])
            dop = parse_date_safe(row[7])
            emp_no = clean_str(row[8])
            pan_no = clean_str(row[9])
            qual = clean_str(row[10])
            basic_pay = clean_str(row[11])
            desig = clean_str(row[12]) or 'Chief Loco Inspector'
            mobile = clean_mobile(row[13])
            address = clean_str(row[14])

            lobby = lobbies.get(hq)
            lobby_id = lobby.id if lobby else lobbies['HWH'].id

            user = User.query.filter(User.username.ilike(li_id)).first()
            if not user:
                # Also check by mobile or full name if username differed
                if mobile:
                    user = User.query.filter(User.mobile == mobile, User.role == 'supervisor').first()
                if not user:
                    user = User(username=li_id)
                    user.set_password('12345')

            user.username = li_id
            user.full_name = name
            user.role = 'supervisor'
            user.sub_role = 'CLI'
            user.lobby_id = lobby_id
            user.mobile = mobile or user.mobile or '0000000000'
            user.pf_number = emp_no or user.pf_number
            user.date_of_birth = dob or user.date_of_birth
            user.date_of_appointment = doa or user.date_of_appointment
            user.is_active = True

            # Custom fields
            user.set_custom_field('father_name', father)
            user.set_custom_field('pan_no', pan_no)
            user.set_custom_field('qualification', qual)
            user.set_custom_field('basic_pay', basic_pay)
            user.set_custom_field('address', address)
            if dop:
                user.set_custom_field('date_of_promotion', dop.strftime('%d-%m-%Y'))

            db.session.add(user)
            db.session.flush()

            clean_name_key = re.sub(r'[^A-Z]', '', name.upper())
            cli_map[clean_name_key] = user.id
            cli_map[li_id] = user.id
            cli_count += 1

        db.session.commit()
        print(f"Successfully processed {cli_count} Chief Loco Inspectors.")

        # Additional alias mappings for crew dataset matching
        aliases = {
            'DEBASHISMAJUMDAR': cli_map.get('DEBASHISMAJUMDER'),
            'MRDEBASHISMAJUMDAR': cli_map.get('DEBASHISMAJUMDER'),
            'DEBASHISMAJUMDER': cli_map.get('DEBASHISMAJUMDER'),
            'AMALENDUMALAKAR': cli_map.get('AMALENDUMALAKAR'),
            'BIDHANCHANDRARAY': cli_map.get('BIDHANCHANDRARAY'),
            'TAPASRAKSHIT': cli_map.get('TAPASRAKSHIT'),
            'HEMANTAKUMARMUDI': cli_map.get('HEMANTAKUMARMUDI'),
            'NPANDIT': cli_map.get('NPANDIT'),
            'DHANPATSAH': cli_map.get('DHANPATSAH'),
            'ASHOKKUMAR': cli_map.get('ASHOKKUMAR'),
            'KASHINATHPRASAD': cli_map.get('KASHINATHPRASAD'),
            'SANJIBKUMARRAY': cli_map.get('SANJIBKUMARRAY'),
            'BIRENDRANARAYANCHATTERJEE': cli_map.get('BIRENDRANARAYANCHATTERJEE'),
            'TARAKSENGUPTA': cli_map.get('TARAKSENGUPTA'),
            'NPASWAN': cli_map.get('NPASWAN'),
            'MRINALDUTTA': cli_map.get('MRINALDUTTA'),
            'RAJIBRAKHIT': cli_map.get('RAJIBRAKHIT'),
            'SAIDULALAM': cli_map.get('SAIDULALAM'),
            'DHANURAMMAJHI': cli_map.get('DHANURAMMAJHI'),
            'LALAGAJENDRANARAYANAMBASTHA': cli_map.get('LALAGAJENDRANARAYANAMBASTHA'),
            'MINTUPAL': cli_map.get('MINTUPAL'),
            'SUSANTADAS': cli_map.get('SUSANTADAS'),
            'PRASANTAPANJA': cli_map.get('PRASANTAPANJA'),
            'TIRTHANKARBOSE': cli_map.get('TIRTHANKARBOSE'),
            'RAMUDGARDAS': cli_map.get('RAMUDGARDAS'),
            'TAPASBARMAN': cli_map.get('TAPASBARMAN'),
            'ASHOKNANDI': cli_map.get('ASHOKNANDI'),
            'PRIYARANJANKISHORE': cli_map.get('PRIYARANJANKISHORE'),
            'DHIRENDRAKUMAR': cli_map.get('DHIRENDRAKUMAR'),
            'SADANANDAPAL': cli_map.get('SADANANDAPAL'),
            'PIJUSHGHOSH': cli_map.get('PIJUSHGHOSH'),
            'AMARJYOTIPATHAK': cli_map.get('AMARJYOTIPATHAK'),
            'SUVADIPPAUL': cli_map.get('SUVADIPPAUL'),
            'HARISHANKARCHAKI': cli_map.get('HARISHANKARCHAKI'),
            'SANTOSHKUMARCHOUDHARY': cli_map.get('SANTOSHKUMARCHOUDHARY'),
            'PAPPU SINGH': cli_map.get('PAPPUSINGH'),
            'BRAJSHEKHARKUMAR': cli_map.get('BRAJSHEKHARKUMAR'),
            'UPENDRAKUMAR': cli_map.get('UPENDRAKUMAR'),
            'NABAKUMARGHOSH': cli_map.get('NABAKUMARGHOSH'),
            'BADALMONDAL': cli_map.get('BADALMONDAL'),
            'NAWALKISHOREDAS': cli_map.get('NAWALKISHOREDAS'),
            'MADHUSUDANROY': cli_map.get('MADHUSUDANROY'),
            'SUKANTABISWAS': cli_map.get('SUKANTABISWAS'),
            'SUKDIPSAREN': cli_map.get('SUKDIPSAREN'),
            'PINAKIGHOSH': cli_map.get('PINAKIGHOSH'),
            'GEORGETOPO': cli_map.get('GEORGETOPO'),
            'SATISHKUMAR': cli_map.get('SATISHKUMAR'),
            'KRISHNACHARONACHARYA': cli_map.get('KRISHNACHARONACHARYA'),
            'MANIDHARSINGH': cli_map.get('MANIDHARSINGH'),
            'SWARUPKUMARHALDER': cli_map.get('SWARUPKUMARHALDER'),
            'SEVAKANTROY': cli_map.get('SEVAKANTROY'),
            'AMARJEETKUMAR': cli_map.get('AMARJEETKUMAR'),
            'BIKASHKUMARCHANCHAL': cli_map.get('BIKASHKUMARCHANCHAL'),
            'MRITYUNJOYDALAL': cli_map.get('MRITYUNJOYDALAL'),
            'MDGHYASUDDIN': cli_map.get('MDGHYASUDDIN'),
            'KOUSHIKCHANDRA': cli_map.get('KOUSHIKCHANDRA'),
            'DEVENDRAKUMAR': cli_map.get('DEVENDRAKUMAR'),
            'SUCHITKUMAR': cli_map.get('SUCHITKUMAR'),
            'SAUMITRAGHOSH': cli_map.get('SAUMITRAGHOSH'),
            'RAKESHRAJAN': cli_map.get('RAKESHRAJAN'),
        }
        for k, v in aliases.items():
            if v and k not in cli_map:
                cli_map[k] = v

        print("\n4. Processing Crew Master Dataset (2,602 records)...")
        wb_crew = openpyxl.load_workbook(tgt_crew_xlsx, data_only=True)
        ws_crew = wb_crew.active

        crew_inserted = 0
        crew_updated = 0
        assigned_cli_count = 0
        lobby_counts = {}

        # Row 1 headers:
        # [0:S.NO, 1:CREWID, 2:CREW NAME, 3:FATHER, 4:GENDER, 5:HRMS ID, 6:TRACTION, 7:CADRE, 8:MOBILE NO, 9:CREW TYPE,
        #  10:BASIC PAY, 11:AVAIL DATE, 12:EMP CODE, 13:AU CODE, 14:Edu. Qual., 15:Tech. Qual., 16:DOB, 17:APP.DATE,
        #  18:I. PME, 19:LASTPROM., 20:B.Grp., 21:VISION, 22:T. MARK, 23:CLI Name, 24:Crew Grade, 25:Crew Photo]

        total_rows = ws_crew.max_row - 1
        for idx, row in enumerate(ws_crew.iter_rows(min_row=2, values_only=True)):
            crew_id = clean_str(row[1]).upper()
            if not crew_id:
                continue

            name = clean_str(row[2])
            father = clean_str(row[3])
            gender = clean_str(row[4]) or 'M'
            hrms_id = clean_str(row[5])
            traction = clean_str(row[6]) or 'ELEC'
            cadre = clean_str(row[7])
            mobile = clean_mobile(row[8])
            crew_type = clean_str(row[9]) or 'ALP'
            basic_pay = clean_str(row[10])
            avail_date = clean_str(row[11])
            emp_code = clean_str(row[12]) # PF Number
            au_code = clean_str(row[13])
            edu_qual = clean_str(row[14])
            tech_qual = clean_str(row[15])
            dob = parse_date_safe(row[16])
            app_date = parse_date_safe(row[17])
            pme_date = parse_date_safe(row[18])
            last_prom = parse_date_safe(row[19])
            b_grp = clean_str(row[20])
            vision = clean_str(row[21])
            t_mark = clean_str(row[22])
            cli_name_raw = clean_str(row[23])
            crew_grade = clean_str(row[24]).upper()
            if crew_grade not in ('A', 'B', 'C'):
                crew_grade = 'B' if 'B' in crew_grade else 'A'

            # Detect Lobby by prefix
            lobby_code = 'HWH'
            m = re.match(r'^([A-Z]+)', crew_id)
            if m:
                pref = m.group(1)
                if pref in lobbies:
                    lobby_code = pref
                elif pref == 'BDC':
                    lobby_code = 'BDC'
                elif pref == 'BHP':
                    lobby_code = 'BHP'
                elif pref == 'TAK':
                    lobby_code = 'TAK'
                elif pref == 'KURV':
                    lobby_code = 'KURV'

            lobby_obj = lobbies.get(lobby_code, lobbies['HWH'])
            lobby_counts[lobby_code] = lobby_counts.get(lobby_code, 0) + 1

            # Match Nominated CLI
            assigned_cli_id = None
            if cli_name_raw and cli_name_raw != '-':
                key = re.sub(r'[^A-Z]', '', cli_name_raw.upper())
                assigned_cli_id = cli_map.get(key)
                if not assigned_cli_id:
                    # Partial search
                    for k, v in cli_map.items():
                        if k in key or key in k:
                            assigned_cli_id = v
                            break
                if assigned_cli_id:
                    assigned_cli_count += 1

            # Find or create User
            crew_user = User.query.filter(User.username.ilike(crew_id)).first()
            if not crew_user and emp_code:
                crew_user = User.query.filter(User.pf_number == emp_code, User.role == 'crew').first()
            if not crew_user and mobile:
                crew_user = User.query.filter(User.mobile == mobile, User.role == 'crew').first()

            if not crew_user:
                crew_user = User(username=crew_id)
                crew_user.set_password('12345')
                crew_inserted += 1
            else:
                crew_updated += 1

            crew_user.username = crew_id
            crew_user.full_name = name
            crew_user.role = 'crew'
            crew_user.sub_role = crew_type
            crew_user.mobile = mobile or crew_user.mobile or '0000000000'
            crew_user.pf_number = emp_code or crew_user.pf_number
            crew_user.hrms_id = hrms_id or crew_user.hrms_id
            crew_user.lobby_id = lobby_obj.id
            crew_user.cli_id = assigned_cli_id
            crew_user.date_of_birth = dob or crew_user.date_of_birth
            crew_user.date_of_appointment = app_date or crew_user.date_of_appointment
            crew_user.pme_last_done_date = pme_date or crew_user.pme_last_done_date
            crew_user.safety_grading = crew_grade
            crew_user.traction_type = traction
            crew_user.is_active = True

            # Custom fields
            crew_user.set_custom_field('father_name', father)
            crew_user.set_custom_field('gender', gender)
            crew_user.set_custom_field('cadre', cadre)
            crew_user.set_custom_field('basic_pay', basic_pay)
            crew_user.set_custom_field('avail_date', avail_date)
            crew_user.set_custom_field('au_code', au_code)
            crew_user.set_custom_field('edu_qual', edu_qual)
            crew_user.set_custom_field('tech_qual', tech_qual)
            crew_user.set_custom_field('blood_group', b_grp)
            crew_user.set_custom_field('vision', vision)
            crew_user.set_custom_field('identification_mark', t_mark)
            crew_user.set_custom_field('nominated_cli_name', cli_name_raw)
            if last_prom:
                crew_user.set_custom_field('last_promotion_date', last_prom.strftime('%d-%m-%Y'))

            db.session.add(crew_user)

            # Flush periodically
            if (idx + 1) % 200 == 0:
                db.session.commit()
                print(f"Processed {idx + 1}/{total_rows} crew members...")

        db.session.commit()
        print(f"\nFinished Crew Ingestion!")
        print(f"New Crews Created: {crew_inserted}")
        print(f"Existing Crews Updated: {crew_updated}")
        print(f"Total Active Crews in DB: {User.query.filter_by(role='crew', is_active=True).count()}")
        print(f"Total Active CLIs in DB: {User.query.filter_by(role='supervisor', sub_role='CLI', is_active=True).count()}")
        print(f"Crews with Assigned CLI: {assigned_cli_count}")
        print("Crews by Lobby prefix:")
        for k, v in sorted(lobby_counts.items()):
            print(f"  - {k}: {v} crews")

if __name__ == '__main__':
    run_import()
