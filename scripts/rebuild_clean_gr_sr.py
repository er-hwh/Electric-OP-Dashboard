import json, re, sys, os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from database import db
from models import ELearningRule

CANONICAL_CHAPTERS = {
    'CHAPTER I': 'PRELIMINARY',
    'CHAPTER II': 'RULES APPLYING TO RAILWAY SERVANTS GENERALLY',
    'CHAPTER III': 'SIGNALS',
    'CHAPTER IV': 'WORKING OF TRAINS GENERALLY',
    'CHAPTER V': 'CONTROL AND WORKING OF STATIONS',
    'CHAPTER VI': 'ACCIDENTS AND UNUSUAL OCCURRENCES',
    'CHAPTER VII': 'SYSTEMS OF WORKING',
    'CHAPTER VIII': 'THE ABSOLUTE BLOCK SYSTEM',
    'CHAPTER IX': 'THE AUTOMATIC BLOCK SYSTEM',
    'CHAPTER X': 'THE FOLLOWING TRAINS SYSTEM',
    'CHAPTER XI': 'THE PILOT GUARD SYSTEM',
    'CHAPTER XII': 'THE TRAIN-STAFF AND TICKET SYSTEM',
    'CHAPTER XIII': 'THE ONE TRAIN ONLY SYSTEM',
    'CHAPTER XIV': 'BLOCK WORKING - GENERAL PROVISIONS',
    'CHAPTER XV': 'PERMANENT WAY AND WORKS',
    'CHAPTER XVI': 'LEVEL CROSSINGS',
    'CHAPTER XVII': 'WORKING OF TRAINS ON ELECTRIFIED SECTIONS OF RAILWAYS',
    'CHAPTER XVIII': 'MISCELLANEOUS'
}

# Rule number prefix to Chapter mapping
def get_canonical_chapter(rule_no):
    # e.g. "GR 3.61" -> 3 -> CHAPTER III
    m = re.search(r'(\d+)\.', rule_no)
    if not m:
        return 'CHAPTER I', CANONICAL_CHAPTERS['CHAPTER I']
    chap_int = int(m.group(1))
    roman_map = {
        1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
        6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X',
        11: 'XI', 12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV',
        16: 'XVI', 17: 'XVII', 18: 'XVIII'
    }
    roman = roman_map.get(chap_int, 'I')
    chap_no = f"CHAPTER {roman}"
    return chap_no, CANONICAL_CHAPTERS[chap_no]

# Load existing JSON rules
with open('static/data/gr_sr_rules.json', 'r', encoding='utf-8') as f:
    existing_rules = json.load(f)

# Rules to exclude (fake extra rules created from previous bad regex)
FAKE_RULES = {
    'GR 1.04', 'GR 1.05', 'GR 1.06', 'GR 1.07', 'GR 1.08', 'GR 1.09', 'GR 1.10',
    'GR 1.11', 'GR 1.12', 'GR 1.13', 'GR 1.14', 'GR 1.15', 'GR 1.16', 'GR 1.17',
    'GR 1.18', 'GR 1.19', 'GR 1.20',
    'GR 2.0', 'GR 2.1', 'GR 2.12', 'GR 2.13',
    'GR 4.1'
}

clean_rules = []
for r in existing_rules:
    r_no = r['rule_no'].strip()
    if r_no in FAKE_RULES:
        continue

    # Fix GR 2.09
    if r_no == 'GR 2.09':
        r['rule_title'] = "Taking alcoholic drink, sedative, narcotic, stimulant drug or preparation"
        r['general_rule'] = (
            "(1) While on duty, no railway servant shall, whether he is directly connected with the working of trains or not, "
            "be in a state of intoxication or in a state in which, by reason of his having taken or used any alcoholic drink, "
            "sedative, narcotic or stimulant drug or preparation, his capacity to perform his duties is impaired.\n\n"
            "(2) No railway servant, directly connected with the working of trains, shall take or use any alcoholic drink, "
            "sedative, narcotic or stimulant drug or preparation within eight hours before the commencement of his duty or "
            "take or use any such drink, drug or preparation when on duty."
        )
        r['key_points'] = (
            "Strict statutory ban on alcohol, narcotics, stimulants on duty or within 8 hours prior to signing on. "
            "Mandatory breathalyzer testing compliance for all train running and safety staff."
        )

    # Standardize chapter
    chap_no, chap_title = get_canonical_chapter(r_no)
    r['chapter_no'] = chap_no
    r['chapter_title'] = chap_title
    clean_rules.append(r)

# Check if GR 8.09 is present, if not add it
has_809 = any(r['rule_no'] == 'GR 8.09' for r in clean_rules)
if not has_809:
    clean_rules.append({
        'rule_no': 'GR 8.09',
        'chapter_no': 'CHAPTER VIII',
        'chapter_title': CANONICAL_CHAPTERS['CHAPTER VIII'],
        'category': 'Block Working',
        'rule_title': "Obstruction in the face of an approaching train at a class 'B' station on single line",
        'general_rule': (
            "The line outside the Home signal in two-aspect signalling territory or outermost facing points "
            "in multiple-aspect or modified lower quadrant signalling territory in the direction of a train "
            "for which Line Clear has been given, shall only be obstructed when a Shunting Limit Board or an "
            "Advanced Starter is provided and under special instructions which take into consideration the speed, "
            "weight and brake power of trains, the gradients, the position of the first Stop signal and the distance "
            "from which that signal can be seen by the Loco Pilot of an approaching train."
        ),
        'subsidiary_rule': (
            "When Line Clear has been given for a train, neither any shunting shall be carried out nor any "
            "obstruction permitted within the station section under the provision of Rule 8.09 in thick, "
            "foggy and tempestuous weather impairing visibility."
        ),
        'key_points': (
            "Obstruction towards an incoming train on single line Class 'B' station is strictly prohibited unless "
            "an SLB or Advanced Starter is provided under approved special instructions."
        )
    })

# Natural sort by rule numbers
def rule_sort_key(r):
    m = re.search(r'(\d+)\.(\d+)', r['rule_no'])
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (999, 999)

clean_rules.sort(key=rule_sort_key)

print(f"Total clean canonical rules: {len(clean_rules)}")

# Save to JSON
with open('static/data/gr_sr_rules.json', 'w', encoding='utf-8') as f:
    json.dump(clean_rules, f, indent=2, ensure_ascii=False)

print("Saved clean canonical rules to static/data/gr_sr_rules.json!")

# Sync to MySQL database
app = create_app()
with app.app_context():
    # 1. Remove fake rules
    deleted_count = 0
    for fake_no in FAKE_RULES:
        found = ELearningRule.query.filter_by(rule_no=fake_no).all()
        for f in found:
            db.session.delete(f)
            deleted_count += 1
    
    # 2. Also remove any orphan non-GR&SR rows that have "Chapter IV: Working of Trains" or invalid rule_no
    invalid_rows = ELearningRule.query.filter(ELearningRule.chapter_no == 'Chapter IV').all()
    for row in invalid_rows:
        db.session.delete(row)
        deleted_count += 1

    # Remove non-GR rules with arbitrary chapter titles like "Duty Hours & HOER", "Railway Board Safety" etc.
    policy_rows = ELearningRule.query.filter(~ELearningRule.chapter_no.like('CHAPTER %')).all()
    for row in policy_rows:
        db.session.delete(row)
        deleted_count += 1

    db.session.commit()
    print(f"Deleted {deleted_count} fake/obsolete rows from MySQL.")

    # 3. Insert or update all 344 canonical rules
    synced_count = 0
    for r in clean_rules:
        db_rule = ELearningRule.query.filter_by(rule_no=r['rule_no']).first()
        if not db_rule:
            db_rule = ELearningRule(
                rule_no=r['rule_no'],
                chapter_no=r['chapter_no'],
                chapter_title=r['chapter_title'],
                category=r.get('category', 'General'),
                rule_title=r['rule_title'],
                general_rule=r.get('general_rule'),
                subsidiary_rule=r.get('subsidiary_rule'),
                key_points=r.get('key_points')
            )
            db.session.add(db_rule)
        else:
            db_rule.chapter_no = r['chapter_no']
            db_rule.chapter_title = r['chapter_title']
            db_rule.rule_title = r['rule_title']
            db_rule.general_rule = r.get('general_rule')
            db_rule.subsidiary_rule = r.get('subsidiary_rule')
            db_rule.key_points = r.get('key_points')
        synced_count += 1

    db.session.commit()
    print(f"Successfully synced all {synced_count} canonical GR & SR rules to MySQL!")

    # Verify final count in DB
    final_count = ELearningRule.query.count()
    print(f"Final total rules in MySQL elearning_rules: {final_count}")
