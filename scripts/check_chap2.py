import json

with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

for r in rules:
    if r.get('chapter_no') == 'CHAPTER II':
        print(f"{r['rule_no']} : {r['rule_title']}")
