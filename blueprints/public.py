from flask import Blueprint, render_template, request, current_app, send_from_directory, flash, redirect, url_for, session
from database import db
from models import (
    Lobby, Notice, CounsellingTopic, CounsellingAcknowledgement, 
    OfficerSay, ELearningRule, PhotoGallery, User
)

public_bp = Blueprint('public', __name__)

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
        crew_count=crew_count,
        cli_count=cli_count
    )

@public_bp.route('/about')
def about():
    lobbies = Lobby.query.order_by(Lobby.code).all()
    officers = User.query.filter_by(role='officer').all()
    return render_template('public/about.html', lobbies=lobbies, officers=officers)

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
    c_type = request.args.get('type', 'ALL')
    query = CounsellingTopic.query.filter(
        (CounsellingTopic.status == 'APPROVED') | (CounsellingTopic.status.is_(None))
    )
    if c_type in ['MONTHLY', 'SPECIAL']:
        query = query.filter_by(counselling_type=c_type)
    c_list = query.order_by(CounsellingTopic.topic_date.desc(), CounsellingTopic.created_at.desc()).all()
    return render_template('public/counselling.html', counselling_list=c_list, current_type=c_type)

@public_bp.route('/counselling/<int:topic_id>')
def counselling_detail(topic_id):
    topic = CounsellingTopic.query.get_or_404(topic_id)
    ack = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.role == 'crew':
            ack = CounsellingAcknowledgement.query.filter_by(counselling_id=topic.id, crew_id=user.id).first()
    return render_template('public/counselling_detail.html', topic=topic, ack=ack)

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
    return render_template('public/contact.html', lobbies=lobbies, officers=officers)
