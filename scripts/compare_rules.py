import json

with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    existing_rules = json.load(f)

from parse_toc import chapters as toc_chapters

toc_rule_map = {}
for c in toc_chapters:
    c_num = c['number']
    if c_num == 'CHAPTER XVII' and c['title'] == 'MISCELLANEOUS':
        c_num = 'CHAPTER XVIII'
    for r in c['rules']:
        toc_rule_map[r['rule_no']] = {
            'chapter_no': c_num,
            'chapter_title': c['title'].strip(),
            'rule_title': r['title']
        }

print(f"Total Canonical TOC rules: {len(toc_rule_map)}")
print(f"Total Existing JSON rules: {len(existing_rules)}")

existing_map = {r['rule_no']: r for r in existing_rules}

extra_in_existing = [r_no for r_no in existing_map if r_no not in toc_rule_map]
missing_in_existing = [r_no for r_no in toc_rule_map if r_no not in existing_map]

print("\n--- EXTRA RULES IN EXISTING JSON (NOT IN OFFICIAL TOC) ---")
for r_no in extra_in_existing:
    r = existing_map[r_no]
    print(f"[{r.get('chapter_no')}] {r_no}: {r.get('rule_title')[:70]}")

print("\n--- MISSING IN EXISTING JSON (IN OFFICIAL TOC) ---")
for r_no in missing_in_existing:
    r = toc_rule_map[r_no]
    print(f"[{r.get('chapter_no')}] {r_no}: {r.get('rule_title')}")
