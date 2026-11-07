import json

with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

for r in rules:
    if r['rule_no'] == 'GR 2.09':
        print("=== EXISTING GR 2.09 ===")
        print("Title:", r.get('rule_title'))
        print("GR:", r.get('general_rule'))
        print("SR:", r.get('subsidiary_rule'))
        break
