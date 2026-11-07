import json

with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

c4_rules = [r['rule_no'] for r in rules if r.get('chapter_no') == 'CHAPTER IV']
print("Total Chapter IV rules in existing JSON:", len(c4_rules))
print("Sample:", c4_rules)
expected = [f"GR 4.{str(i).zfill(2)}" for i in range(1, 67)]
missing = [r for r in expected if r not in c4_rules]
extra = [r for r in c4_rules if r not in expected]
print("Missing in Chapter IV:", missing)
print("Extra in Chapter IV:", extra)
