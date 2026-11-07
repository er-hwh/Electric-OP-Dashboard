import os
import sys
import re
import json
import time
from pypdf import PdfReader

PDF_PATH = r'C:\Users\Indian Railway\.gemini\antigravity\brain\9513809e-d90d-4964-98bd-d36e4e05f542\.user_uploaded\media_1791962055864_26843c4a.pdf'
OUTPUT_JSON = r'c:\Users\Indian Railway\Desktop\Electric OP Dashboard\static\data\gr_sr_rules.json'

os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)

CHAPTER_TITLES = {
    'I': ('CHAPTER I', 'PRELIMINARY', 'Preliminary'),
    'II': ('CHAPTER II', 'RULES APPLYING TO RAILWAY SERVANTS GENERALLY', 'General Discipline & Conduct'),
    'III': ('CHAPTER III', 'SIGNALS', 'Signals & Interlocking'),
    'IV': ('CHAPTER IV', 'WORKING OF TRAINS GENERALLY', 'Train Operation & Crew Duties'),
    'V': ('CHAPTER V', 'CONTROL AND WORKING OF STATIONS', 'Station Working & Shunting'),
    'VI': ('CHAPTER VI', 'ACCIDENTS AND UNUSUAL OCCURRENCES', 'Accidents & Emergency Working'),
    'VII': ('CHAPTER VII', 'SYSTEMS OF WORKING', 'Systems of Working'),
    'VIII': ('CHAPTER VIII', 'THE ABSOLUTE BLOCK SYSTEM', 'Absolute Block System'),
    'IX': ('CHAPTER IX', 'THE AUTOMATIC BLOCK SYSTEM', 'Automatic Block System'),
    'X': ('CHAPTER X', 'THE FOLLOWING TRAINS SYSTEM', 'Special Systems of Working'),
    'XI': ('CHAPTER XI', 'THE PILOT GUARD SYSTEM', 'Special Systems of Working'),
    'XII': ('CHAPTER XII', 'THE TRAIN-STAFF AND TICKET SYSTEM', 'Special Systems of Working'),
    'XIII': ('CHAPTER XIII', 'THE ONE TRAIN ONLY SYSTEM', 'Special Systems of Working'),
    'XIV': ('CHAPTER XIV', 'BLOCK WORKING - GENERAL PROVISIONS', 'Block Working & Tokenless'),
    'XV': ('CHAPTER XV', 'PERMANENT WAY AND WORKS', 'Engineering & Track Protection'),
    'XVI': ('CHAPTER XVI', 'LEVEL CROSSINGS', 'Level Crossings & Gatemen'),
    'XVII': ('CHAPTER XVII', 'WORKING OF TRAINS ON ELECTRIFIED SECTIONS OF RAILWAYS', '25kV AC Traction & OHE Safety'),
    'XVIII': ('CHAPTER XVIII', 'MISCELLANEOUS', 'Miscellaneous')
}

def determine_chapter(rule_num_str):
    try:
        major = int(rule_num_str.split('.')[0])
        roman_map = {
            1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII',
            8: 'VIII', 9: 'IX', 10: 'X', 11: 'XI', 12: 'XII', 13: 'XIII',
            14: 'XIV', 15: 'XV', 16: 'XVI', 17: 'XVII', 18: 'XVIII'
        }
        return roman_map.get(major, 'I')
    except Exception:
        return 'I'

def parse_pdf():
    t_start = time.time()
    print(f"Reading PDF from: {PDF_PATH}", flush=True)
    reader = PdfReader(PDF_PATH)
    total_pages = len(reader.pages)
    print(f"Total pages in PDF: {total_pages}", flush=True)

    # 1. First parse the Table of Contents on pages 11-20 (index 10-20)
    toc_rules = {}
    for p_no in range(10, 21):
        txt = reader.pages[p_no].extract_text() or ''
        for line in txt.split('\n'):
            line = line.strip()
            # Match: "1.01 Short title and Commencement 1" or "3.61 Placing of detonators... 56"
            m = re.match(r'^(\d{1,2}\.\d{1,2})\s+(.+?)\s+(\d{1,3})$', line)
            if m:
                r_num = m.group(1)
                r_title = m.group(2).strip()
                r_page = int(m.group(3))
                toc_rules[r_num] = {
                    'rule_num': r_num,
                    'rule_title': r_title,
                    'book_page': r_page
                }
    print(f"Extracted {len(toc_rules)} rules metadata from Table of Contents.", flush=True)

    # 2. Extract full text from page 22 onwards (0-indexed 21)
    print("Extracting book page texts with progress reporting...", flush=True)
    all_pages_text = []
    for p_no in range(21, total_pages):
        t = reader.pages[p_no].extract_text() or ''
        all_pages_text.append((p_no + 1, t))
        if (p_no + 1) % 50 == 0 or (p_no + 1) == total_pages:
            print(f"  Processed {p_no + 1}/{total_pages} pages ({time.time() - t_start:.1f}s elapsed)...", flush=True)

    print(f"Extracted {len(all_pages_text)} content pages in {time.time() - t_start:.1f}s.", flush=True)

    # 3. Concatenate and split text by rules
    combined_text = ""
    for p_num, p_txt in all_pages_text:
        combined_text += f"\n<<<PAGE_{p_num}>>>\n" + p_txt

    # Match rule starts:
    pattern = re.compile(r'\n(?=(\d{1,2}\.\d{1,2})\.?\s+[A-Z])')
    splits = pattern.split(combined_text)

    rules_data = []
    seen_rule_nums = set()
    
    i = 1
    while i < len(splits):
        r_num = splits[i]
        chunk = splits[i+1] if i+1 < len(splits) else ""
        i += 2

        if r_num in seen_rule_nums:
            continue
        seen_rule_nums.add(r_num)

        lines = chunk.strip().split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # Clean title
        title_from_chunk = re.sub(rf'^{re.escape(r_num)}\.?\s*', '', first_line).strip(' .-:')
        rule_title = toc_rules.get(r_num, {}).get('rule_title', title_from_chunk)
        if not rule_title or len(rule_title) < 3:
            rule_title = title_from_chunk or f"Rule {r_num}"

        # Clean out page markers
        cleaned_body = re.sub(r'<<<PAGE_\d+>>>\s*', '', chunk)
        
        # Separate General Rule and Subsidiary Rule (SR)
        sr_split = re.split(r'\n\s*(?:S\.?R\.?|SR)\s*(?:\d{1,2}\.\d{1,2})?[\.\s\:\-]', cleaned_body, maxsplit=1)
        
        if len(sr_split) > 1:
            gr_text = sr_split[0].strip()
            sr_text = sr_split[1].strip()
        else:
            gr_text = cleaned_body.strip()
            sr_text = ""

        # Remove rule header from gr_text if duplicated
        gr_text = re.sub(rf'^{re.escape(r_num)}\.?\s*[^\n]+\n?', '', gr_text).strip()

        # Chapter info
        chap_roman = determine_chapter(r_num)
        ch_no, ch_name, cat = CHAPTER_TITLES.get(chap_roman, ('CHAPTER I', 'PRELIMINARY', 'General'))

        rules_data.append({
            'rule_no': f"GR {r_num}",
            'rule_num_only': r_num,
            'rule_title': rule_title,
            'chapter_no': ch_no,
            'chapter_title': ch_name,
            'category': cat,
            'general_rule': gr_text[:12000],
            'subsidiary_rule': sr_text[:12000] if sr_text else None,
            'key_points': f"Mandatory compliance with Eastern Railway {ch_name} (Rule {r_num})."
        })

    # Sort rules numerically
    def sort_key(item):
        parts = item['rule_num_only'].split('.')
        try:
            return (int(parts[0]), int(parts[1]))
        except Exception:
            return (999, 999)

    rules_data.sort(key=sort_key)
    print(f"Successfully structured {len(rules_data)} unique General & Subsidiary rules!", flush=True)

    # Save to JSON
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, indent=2, ensure_ascii=False)
    print(f"Saved complete rules database to {OUTPUT_JSON} (File size: {os.path.getsize(OUTPUT_JSON)} bytes)", flush=True)

    # Populate / Sync with MySQL database
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(OUTPUT_JSON))))
        from app import create_app
        from database import db
        from models import ELearningRule


        flask_app = create_app()
        with flask_app.app_context():
            print("Syncing with MySQL database (elearning_rules table)...", flush=True)
            for r in rules_data:
                existing = ELearningRule.query.filter_by(rule_no=r['rule_no']).first()
                if not existing:
                    new_rule = ELearningRule(
                        chapter_no=r['chapter_no'],
                        chapter_title=r['chapter_title'],
                        rule_no=r['rule_no'],
                        rule_title=r['rule_title'],
                        general_rule=r['general_rule'],
                        subsidiary_rule=r['subsidiary_rule'],
                        category=r['category'],
                        key_points=r['key_points']
                    )
                    db.session.add(new_rule)
                else:
                    existing.chapter_no = r['chapter_no']
                    existing.chapter_title = r['chapter_title']
                    existing.rule_title = r['rule_title']
                    if len(r['general_rule']) > 20:
                        existing.general_rule = r['general_rule']
                    if r['subsidiary_rule']:
                        existing.subsidiary_rule = r['subsidiary_rule']
                    existing.category = r['category']
            db.session.commit()
            print(f"Database sync complete! Total rules in MySQL: {ELearningRule.query.count()}", flush=True)
    except Exception as e:
        print(f"MySQL sync notice: {e}", flush=True)

    print(f"ALL DONE in {time.time() - t_start:.1f}s!", flush=True)
    return rules_data

if __name__ == '__main__':
    parse_pdf()
