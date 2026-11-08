from flask import Blueprint, render_template, request, current_app, send_from_directory, flash, redirect, url_for, session
from sqlalchemy import func
from database import db
from models import (
    Lobby, Notice, CounsellingTopic, CounsellingAcknowledgement, 
    OfficerSay, ELearningRule, PhotoGallery, User
)

public_bp = Blueprint('public', __name__)

def get_lobby_strength_data():
    """Calculates comprehensive live lobby information and running staff cadre strength."""
    lobbies = Lobby.query.order_by(Lobby.code).all()

    # Pre-fetch counts for efficiency
    crew_counts = dict(
        db.session.query(User.lobby_id, func.count(User.id))
        .filter(User.role == 'crew')
        .group_by(User.lobby_id)
        .all()
    )

    cli_counts = dict(
        db.session.query(User.lobby_id, func.count(User.id))
        .filter(User.role == 'supervisor')
        .group_by(User.lobby_id)
        .all()
    )

    # Cadre breakdown by lobby and sub_role
    role_breakdown = db.session.query(
        User.lobby_id, User.sub_role, func.count(User.id)
    ).filter(User.role == 'crew').group_by(User.lobby_id, User.sub_role).all()

    cadre_by_lobby = {}
    total_lp = 0
    total_mman = 0
    total_sht = 0
    total_alp = 0

    for lid, srole, cnt in role_breakdown:
        if lid not in cadre_by_lobby:
            cadre_by_lobby[lid] = {'lp': 0, 'mman': 0, 'sht': 0, 'alp': 0, 'other': 0}
        srole_clean = (srole or '').upper().strip()
        if any(x in srole_clean for x in ['LPM', 'LPP', 'LPG', 'SGD', 'SGDP', 'MAIL', 'PASS', 'GOODS']):
            cadre_by_lobby[lid]['lp'] += cnt
            total_lp += cnt
        elif 'MMAN' in srole_clean or 'MOTOR' in srole_clean:
            cadre_by_lobby[lid]['mman'] += cnt
            total_mman += cnt
        elif any(x in srole_clean for x in ['SHT', 'SHUNTER', 'LPS']):
            cadre_by_lobby[lid]['sht'] += cnt
            total_sht += cnt
        elif 'ALP' in srole_clean:
            cadre_by_lobby[lid]['alp'] += cnt
            total_alp += cnt
        else:
            cadre_by_lobby[lid]['other'] += cnt

    result = []
    total_crews = 0
    total_clis = 0
    supervised_count = 0
    outpost_count = 0

    no_sup_codes = {'KURV', 'NHT', 'SNT'}

    for l in lobbies:
        c_cnt = crew_counts.get(l.id, 0)
        cl_cnt = cli_counts.get(l.id, 0)
        total_crews += c_cnt
        total_clis += cl_cnt

        has_sup = (
            l.code not in no_sup_codes and 
            bool(l.ccc_name) and 
            l.ccc_name.strip().lower() not in ['no supervisor', 'none', '']
        )
        if has_sup:
            supervised_count += 1
            sup_name = l.ccc_name.split('(')[0].strip() if l.ccc_name else "In-Charge"
            status_text = "Supervised Depot"
            status_badge = "success"
        else:
            outpost_count += 1
            sup_name = "No Supervisor"
            status_text = "Outpost / Unmanned"
            status_badge = "secondary"

        c_stats = cadre_by_lobby.get(l.id, {'lp': 0, 'mman': 0, 'sht': 0, 'alp': 0, 'other': 0})

        if l.code == 'KURV':
            remarks = "KURVA Yard & Marshalling Operations (Operated under BWN/Yard Master)"
        elif l.code == 'NHT':
            remarks = "Nalhati Branch & Link Crew Base (Operated under RPH/AZ)"
        elif l.code == 'SNT':
            remarks = "Sainthia Junction Loop Base (Operated under RPH)"
        elif l.code == 'HWH':
            remarks = "HQ Main Electric, EMU & Coaching Operations Base"
        elif l.code == 'BWN':
            remarks = "Main Line, Chord Junction & High Density Freight Base"
        elif l.code == 'RPH':
            remarks = "Loop Line Freight, Coal & Mineral Traffic Base"
        elif l.code == 'PKR':
            remarks = "Stone Loading & Heavy Freight Operational Depot"
        elif l.code == 'DKAE':
            remarks = "Dankuni Freight Complex & Coaching Yard Base"
        elif l.code == 'BHP':
            remarks = "Bolpur Shantiniketan Passenger & Express Depot"
        elif l.code == 'KWAE':
            remarks = "Katwa-Azimganj & Bandel Section Operations"
        elif l.code == 'AZ':
            remarks = "Azimganj Murshidabad Branch Operations Depot"
        elif l.code == 'TAK':
            remarks = "Tarakeswar Suburban EMU Branch Line Base"
        else:
            remarks = l.description or "Running Staff Depot"

        result.append({
            'lobby': l,
            'code': l.code,
            'name': l.name,
            'phone': l.phone or 'N/A',
            'has_supervisor': has_sup,
            'supervisor_name': sup_name,
            'ccc_full': l.ccc_name if has_sup else 'No Supervisor',
            'status_text': status_text,
            'status_badge': status_badge,
            'crew_count': c_cnt,
            'cli_count': cl_cnt,
            'cadre': c_stats,
            'remarks': remarks
        })

    summary = {
        'total_crew': total_crews,
        'total_cli': total_clis,
        'supervised_lobbies': supervised_count,
        'outpost_lobbies': outpost_count,
        'total_lobbies': len(lobbies),
        'total_lp': total_lp,
        'total_mman': total_mman,
        'total_sht': total_sht,
        'total_alp': total_alp
    }

    return result, summary

@public_bp.route('/')
def index():
    # Fetch active notices
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).limit(8).all()
    # Fetch active counselling topics
    counselling_list = CounsellingTopic.query.order_by(CounsellingTopic.topic_date.desc()).limit(4).all()
    # Fetch officer says
    officer_says = OfficerSay.query.filter_by(is_active=True).order_by(OfficerSay.priority_order).all()
    # Fetch photo gallery items
    gallery_items = PhotoGallery.query.order_by(PhotoGallery.created_at.desc()).limit(6).all()
    # Lobbies count & summary
    lobbies = Lobby.query.order_by(Lobby.code).all()
    lobby_strengths, strength_summary = get_lobby_strength_data()
    # Counts
    crew_count = User.query.filter_by(role='crew', is_active=True).count()
    cli_count = User.query.filter_by(role='supervisor', is_active=True).count()

    return render_template(
        'public/index.html',
        notices=notices,
        counselling_list=counselling_list,
        officer_says=officer_says,
        gallery_items=gallery_items,
        lobbies=lobbies,
        lobby_strengths=lobby_strengths,
        strength_summary=strength_summary,
        crew_count=crew_count,
        cli_count=cli_count
    )

@public_bp.route('/about')
def about():
    lobbies = Lobby.query.order_by(Lobby.code).all()
    officers = User.query.filter_by(role='officer').all()
    lobby_strengths, strength_summary = get_lobby_strength_data()
    return render_template(
        'public/about.html', 
        lobbies=lobbies, 
        officers=officers,
        lobby_strengths=lobby_strengths,
        strength_summary=strength_summary
    )

@public_bp.route('/instructions')
def instructions():
    sr_dee_instructions = Notice.query.filter(
        Notice.category.in_(['Sr. DEE(OP) Instruction', 'Safety Drive']),
        Notice.is_active == True
    ).order_by(Notice.created_at.desc()).all()
    return render_template('public/instructions.html', instructions=sr_dee_instructions)

@public_bp.route('/notices')
def notices():
    category = request.args.get('category', 'ALL')
    query = Notice.query.filter_by(is_active=True)
    if category != 'ALL':
        query = query.filter_by(category=category)
    notice_list = query.order_by(Notice.created_at.desc()).all()
    return render_template('public/notices.html', notices=notice_list, current_category=category)

@public_bp.route('/counselling')
def counselling():
    """Daily Safety Counselling removed as standalone public module; accessible inside user login dashboards."""
    flash('Safety counselling is now integrated into the authenticated user dashboard. Please sign in to view counselling records.', 'info')
    if 'user_id' in session:
        from blueprints.auth import redirect_by_role
        user = User.query.get(session['user_id'])
        if user:
            return redirect_by_role(user)
    return redirect(url_for('auth.login'))

@public_bp.route('/counselling/<int:topic_id>')
def counselling_detail(topic_id):
    flash('Safety counselling is now integrated into the authenticated user dashboard.', 'info')
    if 'user_id' in session:
        from blueprints.auth import redirect_by_role
        user = User.query.get(session['user_id'])
        if user:
            return redirect_by_role(user)
    return redirect(url_for('auth.login'))

@public_bp.route('/loco-info')
def loco_info():
    """Public portal: Loco Information for Electric & Diesel Locomotives."""
    return render_template('public/loco_info.html')

@public_bp.route('/rules')
def rules():
    """Public portal: Important Rules & Regulations."""
    return redirect(url_for('elearning.index'))

@public_bp.route('/learning-materials')
def learning_materials():
    """Public portal: Centralized Learning Materials."""
    return render_template('public/learning_materials.html')

@public_bp.route('/elearning')
def elearning():
    rules = ELearningRule.query.all()
    categories = db.session.query(ELearningRule.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    selected_cat = request.args.get('category', 'ALL')
    if selected_cat != 'ALL':
        rules = ELearningRule.query.filter_by(category=selected_cat).all()
    return render_template('public/elearning.html', rules=rules, categories=categories, selected_cat=selected_cat)

@public_bp.route('/gallery')
def gallery():
    items = PhotoGallery.query.order_by(PhotoGallery.created_at.desc()).all()
    return render_template('public/gallery.html', items=items)

@public_bp.route('/contact')
def contact():
    lobbies = Lobby.query.order_by(Lobby.code).all()
    officers = User.query.filter_by(role='officer').all()
    lobby_strengths, strength_summary = get_lobby_strength_data()
    return render_template(
        'public/contact.html', 
        lobbies=lobbies, 
        officers=officers,
        lobby_strengths=lobby_strengths,
        strength_summary=strength_summary
    )
