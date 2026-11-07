import os
import sys
import re
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

JSON_PATH = os.path.join(ROOT_DIR, 'static', 'data', 'gr_sr_rules.json')

CLAUSE_REGEX = re.compile(r'^\s*(\(\d+\)|\([a-z]\)|\[[a-z]\]|\([ivx]+\)|\[[ivx]+\]|\d+\.|\bNote\b|\bException\b|\bProvided\b)', re.I)

def rejoin_text(text):
    if not text:
        return ""
    
    # Split text by newlines
    lines = text.split('\n')
    paragraphs = []
    current_para = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_para:
                paragraphs.append(current_para)
                current_para = ""
            continue

        # If line starts a new clause e.g. (1), (a), [a], [i], 1., Note:
        if CLAUSE_REGEX.match(stripped):
            if current_para:
                paragraphs.append(current_para)
            current_para = stripped
        else:
            if current_para:
                # Rejoin line to current paragraph with a single space
                current_para += " " + stripped
            else:
                current_para = stripped

    if current_para:
        paragraphs.append(current_para)

    # Recombine with clean double newline between full paragraphs
    return "\n\n".join(paragraphs)

def run():
    print(f"Reading {JSON_PATH}...")
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    print(f"Rejoining paragraphs across {len(rules)} rules...")
    for r in rules:
        r['general_rule'] = rejoin_text(r.get('general_rule', ''))
        r['subsidiary_rule'] = rejoin_text(r.get('subsidiary_rule', ''))

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
    print(f"Saved {JSON_PATH} ({os.path.getsize(JSON_PATH)} bytes).")

    # Update MySQL
    try:
        from app import create_app
        from database import db
        from models import ELearningRule

        flask_app = create_app()
        with flask_app.app_context():
            print("Syncing rejoined paragraphs to MySQL...")
            for r in rules:
                rule_record = ELearningRule.query.filter_by(rule_no=r['rule_no']).first()
                if rule_record:
                    rule_record.general_rule = r['general_rule']
                    rule_record.subsidiary_rule = r['subsidiary_rule']
            db.session.commit()
            print("MySQL update completed successfully!")
    except Exception as e:
        print(f"MySQL error: {e}")

if __name__ == '__main__':
    run()
