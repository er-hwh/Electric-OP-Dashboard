from flask import Blueprint, render_template, request, jsonify
from database import db
from models import ELearningRule, ELearningQuiz, RuleDocument

elearning_bp = Blueprint('elearning', __name__)

import re
from collections import OrderedDict

CANONICAL_CHAPTER_MAP = {
    'CHAPTER I': 1, 'CHAPTER II': 2, 'CHAPTER III': 3, 'CHAPTER IV': 4,
    'CHAPTER V': 5, 'CHAPTER VI': 6, 'CHAPTER VII': 7, 'CHAPTER VIII': 8,
    'CHAPTER IX': 9, 'CHAPTER X': 10, 'CHAPTER XI': 11, 'CHAPTER XII': 12,
    'CHAPTER XIII': 13, 'CHAPTER XIV': 14, 'CHAPTER XV': 15, 'CHAPTER XVI': 16,
    'CHAPTER XVII': 17, 'CHAPTER XVIII': 18
}

def chapter_sort_key(chap_no):
    clean = (chap_no or '').upper().replace('-', ' ').strip()
    return CANONICAL_CHAPTER_MAP.get(clean, 999)

def rule_sort_key(rule):
    r_no = getattr(rule, 'rule_no', '') or ''
    m = re.search(r'(\d+)\.(\d+)', r_no)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return (999, 999)

@elearning_bp.route('/')
def index():
    query_str = request.args.get('q', '').strip()
    category = request.args.get('category', 'ALL')
    rule_param = request.args.get('rule', '').strip()
    rule_id_param = request.args.get('id', '').strip()

    # Base query for all rules
    all_rules_query = ELearningRule.query
    if category != 'ALL':
        all_rules_query = all_rules_query.filter_by(category=category)

    if query_str:
        all_rules_query = all_rules_query.filter(
            (ELearningRule.rule_no.ilike(f'%{query_str}%')) |
            (ELearningRule.rule_title.ilike(f'%{query_str}%')) |
            (ELearningRule.general_rule.ilike(f'%{query_str}%')) |
            (ELearningRule.subsidiary_rule.ilike(f'%{query_str}%')) |
            (ELearningRule.key_points.ilike(f'%{query_str}%'))
        )

    all_rules = sorted(all_rules_query.all(), key=rule_sort_key)

    # Determine Active Rule
    active_rule = None
    if rule_id_param and rule_id_param.isdigit():
        active_rule = ELearningRule.query.get(int(rule_id_param))
    elif rule_param:
        clean_target = rule_param.replace('_', ' ').strip()
        active_rule = ELearningRule.query.filter(
            (ELearningRule.rule_no.ilike(f'%{clean_target}%')) |
            (ELearningRule.rule_title.ilike(f'%{clean_target}%'))
        ).first()

    if not active_rule and all_rules:
        # Default to first search result or GR 1.01
        active_rule = all_rules[0]

    # Calculate Previous & Next Rules
    prev_rule = None
    next_rule = None
    if active_rule:
        for idx, r in enumerate(all_rules):
            if r.id == active_rule.id:
                if idx > 0:
                    prev_rule = all_rules[idx - 1]
                if idx < len(all_rules) - 1:
                    next_rule = all_rules[idx + 1]
                break

    # Group rules by chapter for the Table of Contents / Index Sidebar
    # Get all rules without query filter for complete index
    full_library = sorted(ELearningRule.query.all(), key=rule_sort_key)
    chapters_dict = OrderedDict()
    
    for r in full_library:
        ch_key = r.chapter_no or 'General'
        if ch_key not in chapters_dict:
            chapters_dict[ch_key] = {
                'chapter_no': ch_key,
                'chapter_title': r.chapter_title or ch_key,
                'rules': []
            }
        chapters_dict[ch_key]['rules'].append(r)

    # Sort rules within each chapter
    for ch_data in chapters_dict.values():
        ch_data['rules'].sort(key=rule_sort_key)

    # Sort chapters canonically (Chapter I to XVIII)
    sorted_chapters = sorted(chapters_dict.values(), key=lambda c: chapter_sort_key(c['chapter_no']))

    categories = [c[0] for c in db.session.query(ELearningRule.category).distinct().all() if c[0]]

    # Official Rule Books, Manuals & Operating Regulations (Non-GR&SR)
    active_tab = request.args.get('tab', 'grsr')
    doc_search = request.args.get('doc_search', '').strip()
    doc_cat = request.args.get('doc_cat', 'ALL').strip()

    doc_query = RuleDocument.query.filter_by(is_active=True)
    if doc_cat and doc_cat != 'ALL':
        doc_query = doc_query.filter_by(category=doc_cat)
    if doc_search:
        doc_query = doc_query.filter(
            (RuleDocument.title.ilike(f'%{doc_search}%')) |
            (RuleDocument.rule_reference.ilike(f'%{doc_search}%')) |
            (RuleDocument.description.ilike(f'%{doc_search}%')) |
            (RuleDocument.category.ilike(f'%{doc_search}%'))
        )
    rule_documents = doc_query.order_by(RuleDocument.display_order.asc(), RuleDocument.id.asc()).all()

    rule_docs_by_cat = OrderedDict()
    all_active_docs = RuleDocument.query.filter_by(is_active=True).order_by(RuleDocument.display_order.asc(), RuleDocument.id.asc()).all()
    for doc in all_active_docs:
        c = doc.category or 'General Manuals'
        if c not in rule_docs_by_cat:
            rule_docs_by_cat[c] = []
        rule_docs_by_cat[c].append(doc)

    return render_template(
        'public/elearning.html',
        chapters=sorted_chapters,
        all_rules=all_rules,
        active_rule=active_rule,
        prev_rule=prev_rule,
        next_rule=next_rule,
        categories=categories,
        selected_cat=category,
        query_str=query_str,
        total_rules_count=len(full_library),
        rule_documents=rule_documents,
        rule_docs_by_cat=rule_docs_by_cat,
        all_rule_docs_count=len(all_active_docs),
        active_tab=active_tab,
        doc_search=doc_search,
        doc_cat=doc_cat
    )

@elearning_bp.route('/api/rule/<int:rule_id>')
def api_rule(rule_id):
    rule = ELearningRule.query.get_or_404(rule_id)
    
    prev_rule = ELearningRule.query.filter(ELearningRule.id < rule.id).order_by(ELearningRule.id.desc()).first()
    next_rule = ELearningRule.query.filter(ELearningRule.id > rule.id).order_by(ELearningRule.id.asc()).first()

    return jsonify({
        'id': rule.id,
        'rule_no': rule.rule_no,
        'rule_title': rule.rule_title,
        'chapter_no': rule.chapter_no,
        'chapter_title': rule.chapter_title,
        'category': rule.category,
        'general_rule': rule.general_rule or '',
        'subsidiary_rule': rule.subsidiary_rule or '',
        'key_points': rule.key_points or '',
        'youtube_video_id': rule.youtube_video_id or '',
        'youtube_title': rule.youtube_title or '',
        'animation': rule.get_animation(),
        'prev_id': prev_rule.id if prev_rule else None,
        'prev_rule_no': prev_rule.rule_no if prev_rule else None,
        'next_id': next_rule.id if next_rule else None,
        'next_rule_no': next_rule.rule_no if next_rule else None,
    })


@elearning_bp.route('/api/rule/<int:rule_id>/video', methods=['POST'])
def api_save_rule_video(rule_id):
    # Strict Rule: Only Admin can edit system rules & learning media
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Admin login required to edit system rules.'}), 401
    current_u = User.query.get(session['user_id'])
    if not current_u or not current_u.is_admin():
        return jsonify({'success': False, 'message': 'Security Policy: System edits can only be performed by System Admin.'}), 403

    rule = ELearningRule.query.get_or_404(rule_id)
    data = request.get_json() or {}
    raw_video = (data.get('video_url') or data.get('youtube_video_id') or '').strip()
    title = (data.get('title') or '').strip()

    video_id = None
    if raw_video:
        m = re.search(r'(?:v=|\/|youtu\.be\/|embed\/)([0-9A-Za-z_-]{11})', raw_video)
        if m:
            video_id = m.group(1)
        elif len(raw_video) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', raw_video):
            video_id = raw_video

    rule.youtube_video_id = video_id
    if title:
        rule.youtube_title = title
    elif not rule.youtube_title and video_id:
        rule.youtube_title = f"{rule.rule_no}: {rule.rule_title}"

    db.session.commit()

    return jsonify({
        'success': True,
        'youtube_video_id': rule.youtube_video_id,
        'youtube_title': rule.youtube_title
    })



import os
import json

@elearning_bp.route('/troubleshooting')
def troubleshooting():
    json_path = os.path.join(elearning_bp.root_path, '..', 'static', 'data', 'loco_troubleshooting.json')
    topics = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                topics = json.load(f)
        except Exception:
            topics = []
    
    categories = sorted(list({t.get('category') for t in topics if t.get('category')}))
    return render_template('public/troubleshooting.html', topics=topics, categories=categories)


@elearning_bp.route('/forms-manual')
def forms_manual():
    # Operating forms list as extracted from Eastern Railway Appendix D
    return render_template('public/forms_manual.html')

def load_all_quizzes():
    # Try loading from database first
    try:
        db_quizzes = ELearningQuiz.query.order_by(ELearningQuiz.id).all()
        if db_quizzes:
            return [{
                'id': q.quiz_id_str,
                'chapter_no': q.chapter_no,
                'chapter_title': q.chapter_title,
                'rule_ref': q.rule_ref,
                'question': q.question,
                'options': q.get_options(),
                'correct_index': q.correct_index,
                'explanation': q.explanation,
                'difficulty': q.difficulty
            } for q in db_quizzes]
    except Exception:
        pass
    
    # Fallback to JSON file
    json_path = os.path.join(elearning_bp.root_path, '..', 'static', 'data', 'gr_sr_quizzes.json')
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []

@elearning_bp.route('/quiz')
def quiz():
    all_quizzes = load_all_quizzes()
    selected_chapter = request.args.get('chapter', '').strip()

    # Build ordered list of chapters with counts
    chapter_stats = OrderedDict()
    for q in all_quizzes:
        c_no = q.get('chapter_no', 'OTHER')
        c_title = q.get('chapter_title', '')
        if c_no not in chapter_stats:
            chapter_stats[c_no] = {
                'chapter_no': c_no,
                'chapter_title': c_title,
                'count': 0
            }
        chapter_stats[c_no]['count'] += 1

    chapters_list = list(chapter_stats.values())
    
    # Sort chapters canonically (Chapter I to XVIII, then Special)
    def quiz_chapter_sort_key(c):
        c_no = c['chapter_no']
        if c_no in CANONICAL_CHAPTER_MAP:
            return CANONICAL_CHAPTER_MAP[c_no]
        if 'SPECIAL' in c_no.upper() or 'CIRCULAR' in c_no.upper():
            return 990
        return 999

    chapters_list.sort(key=quiz_chapter_sort_key)

    # Filter quizzes if a specific chapter is requested
    if selected_chapter and selected_chapter.upper() != 'ALL':
        filtered_quizzes = [q for q in all_quizzes if q.get('chapter_no', '').upper() == selected_chapter.upper()]
    else:
        filtered_quizzes = all_quizzes
        selected_chapter = 'ALL'

    return render_template(
        'public/quiz.html',
        quizzes=filtered_quizzes,
        all_quizzes_json=json.dumps(all_quizzes, ensure_ascii=False),
        chapters=chapters_list,
        selected_chapter=selected_chapter,
        total_quiz_count=len(all_quizzes)
    )

@elearning_bp.route('/api/quiz')
def api_quiz():
    all_quizzes = load_all_quizzes()
    chapter = request.args.get('chapter', '').strip()
    if chapter and chapter.upper() != 'ALL':
        filtered = [q for q in all_quizzes if q.get('chapter_no', '').upper() == chapter.upper()]
    else:
        filtered = all_quizzes
    return jsonify({
        'success': True,
        'count': len(filtered),
        'total': len(all_quizzes),
        'quizzes': filtered
    })
