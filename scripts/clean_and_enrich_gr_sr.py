import os
import sys
import re
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

JSON_PATH = os.path.join(ROOT_DIR, 'static', 'data', 'gr_sr_rules.json')


def clean_text(text):
    if not text:
        return ""
    
    # 1. Clean up characters without breaking text
    text = text.replace('\ufffd', ' - ')
    text = re.sub(r'\s*\?\s*', ' ', text)

    
    # 2. Fix broken words common in PDF font extraction
    text = re.sub(r'(\b[a-zA-Z]+)-\s*\n\s*([a-zA-Z]+\b)', r'\1\2', text) # hyphenated line breaks
    text = re.sub(r'\bneces\s+sary\b', 'necessary', text, flags=re.I)
    text = re.sub(r'\bou\s+tside\b', 'outside', text, flags=re.I)
    text = re.sub(r'\bwhistl\s+e\b', 'whistle', text, flags=re.I)
    text = re.sub(r'\bmul\s+tiple\b', 'multiple', text, flags=re.I)
    text = re.sub(r'\bauth\s+ority\b', 'authority', text, flags=re.I)
    text = re.sub(r'\boper\s+ation\b', 'operation', text, flags=re.I)
    text = re.sub(r'\bper\s+mitted\b', 'permitted', text, flags=re.I)
    text = re.sub(r'\bcondi\s+tion\b', 'condition', text, flags=re.I)
    text = re.sub(r'\bsta\s+tion\b', 'station', text, flags=re.I)
    text = re.sub(r'\bsig\s+nal\b', 'signal', text, flags=re.I)
    text = re.sub(r'\bapp\s+roved\b', 'approved', text, flags=re.I)

    # 3. Remove standalone PDF page numbers (e.g. \n 115 \n or \n 259 \n)
    text = re.sub(r'\n\s*\d{1,3}\s*\n', '\n', text)
    text = re.sub(r'<<<PAGE_\d+>>>\s*', '', text)

    # 4. Remove dangling fragments like "sections -" or "rules -" at the very beginning
    text = re.sub(r'^[a-z\s\-,\.:]+\n', '', text)

    # 5. Normalize multiple spaces and extra blank lines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

    return text.strip()

def generate_key_points(rule_no, title, chapter_title, gr_text, sr_text):
    combined = (title + " " + gr_text + " " + (sr_text or "")).lower()
    
    if "detonator" in combined or "3.61" in rule_no:
        return "Mandatory 2 detonators 10m apart at 270m outside First Stop Signal in thick/foggy weather. Loco Pilot must reduce speed and be prepared to stop."
    elif "whistle" in combined or "4.50" in rule_no:
        return "Whistle codes must be strictly adhered to: Continuous whistle when approaching curves/cuttings/level crossings; 'O' (short) and '-' (long) codes for Guard and assistance."
    elif "neutral section" in combined or "17.07" in rule_no:
        return "Mandatory coasting through Neutral Section. Lower throttle to '0' at 250m board, Open DJ/VCB at SWITCH OFF board, Close DJ/VCB at SWITCH ON board. Do NOT apply brakes inside neutral section."
    elif "automatic stop signal" in combined or "9.02" in rule_no:
        return "When Automatic Signal is at 'ON': Wait 1 min by day / 2 min by night. Proceed with extreme caution at max 15 km/h (clear weather) or 10 km/h (foggy weather) up to next signal."
    elif "caution order" in combined or "4.09" in rule_no:
        return "Verify Caution Order (T/409, Nil T/A 409, Reminder T/B 409) against speed restrictions and permanent way work zones before departure."
    elif "spad" in combined or "danger" in combined:
        return "Stop dead before any Danger signal. Never pass a Stop signal at 'ON' without valid written authority (e.g. T/369(3b)) and Pilot-in order."
    elif "shunting" in combined:
        return "Maximum shunting speed 15 km/h. Guard or Shunting Supervisor must supervise movement. Never shunt towards unblocked line without line clear."
    elif "level crossing" in combined or "gate" in combined:
        return "Sound continuous intermittent whistle when approaching 'W/L' board. Sighting distance must be observed. In case of gate signal 'ON', proceed as per G.R. 16.06."
    elif "brake" in combined:
        return "Ensure BP pressure 5.0 kg/cm² and FP 6.0 kg/cm². Perform mandatory brake feel and continuity tests at first opportunity."
    else:
        return f"Strict statutory compliance with {chapter_title} - {title}. Mandatory knowledge for all running and safety operating staff."

def process():
    print(f"Loading {JSON_PATH}...")
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    print(f"Processing {len(rules)} rules...")
    for r in rules:
        r['general_rule'] = clean_text(r.get('general_rule', ''))
        r['subsidiary_rule'] = clean_text(r.get('subsidiary_rule', ''))
        r['key_points'] = generate_key_points(
            r.get('rule_no', ''),
            r.get('rule_title', ''),
            r.get('chapter_title', ''),
            r['general_rule'],
            r['subsidiary_rule']
        )

    # Save cleaned JSON
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
    print(f"Saved cleaned JSON to {JSON_PATH} ({os.path.getsize(JSON_PATH)} bytes).")

    # Sync with MySQL
    try:
        from app import create_app
        from database import db
        from models import ELearningRule

        flask_app = create_app()
        with flask_app.app_context():
            print("Syncing cleaned data into MySQL elearning_rules table...")
            for r in rules:
                rule_record = ELearningRule.query.filter_by(rule_no=r['rule_no']).first()
                if rule_record:
                    rule_record.rule_title = r['rule_title']
                    rule_record.general_rule = r['general_rule']
                    rule_record.subsidiary_rule = r['subsidiary_rule']
                    rule_record.key_points = r['key_points']
                    rule_record.category = r['category']
            db.session.commit()
            print("MySQL update completed successfully!")
    except Exception as e:
        print(f"MySQL error: {e}")

if __name__ == '__main__':
    process()
