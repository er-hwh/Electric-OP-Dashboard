import json, sys, os
sys.path.insert(0, os.path.abspath('.'))

with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)

for chap_roman in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII']:
    chap_name = f'CHAPTER {chap_roman}'
    chap_rules = [r for r in rules if r.get('chapter_no') == chap_name]
    titles = set(r.get('chapter_title') for r in chap_rules)
    rule_nos = [r.get('rule_no') for r in chap_rules]
    print(f"{chap_name}: {len(chap_rules)} rules | Titles: {titles}")
    if rule_nos:
        print(f"   First: {rule_nos[0]} | Last: {rule_nos[-1]} | Sample: {rule_nos[:6]}")
