import json, sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import create_app
from models import ELearningRule

with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

print(f"Total rules in JSON: {len(rules)}")
chapters = {}
for r in rules:
    c_no = r.get('chapter_no', '')
    c_title = r.get('chapter_title', '')
    key = (c_no, c_title)
    if key not in chapters:
        chapters[key] = {'count': 0, 'sample_rules': []}
    chapters[key]['count'] += 1
    if len(chapters[key]['sample_rules']) < 4:
        chapters[key]['sample_rules'].append(r.get('rule_no'))

print("\n--- CHAPTERS IN JSON ---")
for (c_no, c_title), info in sorted(chapters.items(), key=lambda x: str(x[0])):
    print(f"[{c_no}] | Title: '{c_title}' | Count: {info['count']} | Samples: {info['sample_rules']}")

app = create_app()
with app.app_context():
    db_rules = ELearningRule.query.all()
    print(f"\nTotal rules in DB: {len(db_rules)}")
    db_chaps = {}
    for r in db_rules:
        k = (r.chapter_no, r.chapter_title)
        db_chaps[k] = db_chaps.get(k, 0) + 1
    print("\n--- CHAPTERS IN DB ---")
    for (c_no, c_title), cnt in sorted(db_chaps.items(), key=lambda x: str(x[0])):
        print(f"[{c_no}] | Title: '{c_title}' | Count: {cnt}")
