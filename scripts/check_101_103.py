import json

with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

for r in rules[:3]:
    print(f"=== {r['rule_no']} : {r['rule_title']} ===")
    print("GR:", r.get('general_rule')[:100] if r.get('general_rule') else 'None')
    print("SR:", r.get('subsidiary_rule')[:200] if r.get('subsidiary_rule') else 'None')
