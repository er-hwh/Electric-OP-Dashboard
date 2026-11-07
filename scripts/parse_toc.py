import re

with open("scripts/raw_toc_text.txt", "r", encoding="utf-8") as f:
    text = f.read()

lines = [l.strip() for l in text.split("\n") if l.strip()]

chapters = []
current_chap = None

# Pattern to find CHAPTER - I or CHAPTER I or CHAPTER - XIV
chap_re = re.compile(r'^CHAPTER\s*[\-–]?\s*([IVX]+)$', re.I)
rule_num_re = re.compile(r'^(\d{1,2}\.\d{2})$')

i = 0
while i < len(lines):
    line = lines[i]
    m_chap = chap_re.match(line)
    if m_chap:
        roman = m_chap.group(1).upper()
        # Next line is the title
        title_parts = []
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if nxt.startswith('---') or nxt in ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'GR', 'No.', 'Rules', 'Pages', 'Pages.', 'ARRANGEMENT OF RULES.', 'INDEX']:
                i += 1
                continue
            if chap_re.match(nxt) or rule_num_re.match(nxt) or re.match(r'^[A-Z]\.', nxt) or nxt.startswith('APPENDIX'):
                break
            title_parts.append(nxt)
            i += 1
        chap_title = " ".join(title_parts).strip()
        current_chap = {
            'number': f"CHAPTER {roman}",
            'roman': roman,
            'title': chap_title,
            'rules': []
        }
        chapters.append(current_chap)
        continue
    
    m_rule = rule_num_re.match(line)
    if m_rule and current_chap:
        rule_no = m_rule.group(1)
        # Next lines until page number (a digit)
        i += 1
        title_parts = []
        page_no = None
        while i < len(lines):
            nxt = lines[i]
            if nxt.startswith('---') or nxt in ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'GR', 'No.', 'Rules', 'Pages', 'Pages.']:
                i += 1
                continue
            if re.match(r'^\d+$', nxt):
                page_no = int(nxt)
                i += 1
                break
            if rule_num_re.match(nxt) or chap_re.match(nxt):
                break
            title_parts.append(nxt)
            i += 1
        rule_title = " ".join(title_parts).strip()
        current_chap['rules'].append({
            'rule_no': f"GR {rule_no}",
            'pure_no': rule_no,
            'title': rule_title,
            'page': page_no
        })
        continue

    i += 1

print(f"Extracted {len(chapters)} chapters:")
total_rules = 0
for c in chapters:
    print(f"[{c['number']}] {c['title']} ({len(c['rules'])} rules)")
    total_rules += len(c['rules'])
    if c['rules']:
        print(f"   Sample: {c['rules'][0]['rule_no']} - {c['rules'][0]['title']} to {c['rules'][-1]['rule_no']}")

print(f"TOTAL RULES: {total_rules}")
