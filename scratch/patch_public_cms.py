import os

public_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\blueprints\public.py"

with open(public_file, 'r', encoding='utf-8') as f:
    code = f.read()

# Update import
old_import = "OfficerSay, ELearningRule, PhotoGallery, User"
new_import = "OfficerSay, ELearningRule, PhotoGallery, User, CarouselSlide, SafetyBulletin, RuleDocument, LearningMaterial, PageContent"
if "CarouselSlide" not in code:
    code = code.replace(old_import, new_import)

# Update index function
old_index_render = """    return render_template(
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
    )"""

new_index_prep = """    # Active Carousel Slides
    slides = CarouselSlide.query.filter_by(is_active=True).order_by(CarouselSlide.display_order.asc(), CarouselSlide.id.desc()).all()
    # Active Safety Bulletins
    bulletins = SafetyBulletin.query.filter_by(is_active=True).order_by(SafetyBulletin.bulletin_date.desc(), SafetyBulletin.id.desc()).limit(10).all()
    # Dynamic Page Contents
    mission_text = PageContent.get_val('home_mission', 'To provide safe, reliable, efficient and punctual electric and diesel locomotive operations across the Howrah Division, adhering to the highest standards of safety, operating discipline, and crew welfare.')
    vision_text = PageContent.get_val('home_vision', 'Zero Accident, Zero SPAD, 100% electrified operations, technological modernisation of crew management and continuous skill upgradation of running staff.')
    safety_slogan = PageContent.get_val('safety_slogan', 'Safety First, Service Always - Alert Crew, Safe Rail.')
    emergency_contacts = PageContent.get_val('emergency_contacts', 'TLC (Traction Loco Control): 22328, 033-2641-3652 | PCNL (Power Control): 22666, 22667 | Sr. DEE(OP) Control Room: 22440')

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
        cli_count=cli_count,
        slides=slides,
        bulletins=bulletins,
        mission_text=mission_text,
        vision_text=vision_text,
        safety_slogan=safety_slogan,
        emergency_contacts=emergency_contacts
    )"""

code = code.replace(old_index_render, new_index_prep)

# Update rules and learning_materials
old_rules_learning = """@public_bp.route('/rules')
def rules():
    \"\"\"Public portal: Important Rules & Regulations.\"\"\"
    return redirect(url_for('elearning.index'))

@public_bp.route('/learning-materials')
def learning_materials():
    \"\"\"Public portal: Centralized Learning Materials.\"\"\"
    return render_template('public/learning_materials.html')"""

new_rules_learning = """@public_bp.route('/rules')
def rules():
    \"\"\"Public portal: Important Rules & Regulations with PDF download/viewer.\"\"\"
    category = request.args.get('category', 'ALL')
    search = request.args.get('q', '').strip()

    query = RuleDocument.query.filter_by(is_active=True)
    if category != 'ALL':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            (RuleDocument.title.ilike(f'%{search}%')) |
            (RuleDocument.rule_reference.ilike(f'%{search}%')) |
            (RuleDocument.description.ilike(f'%{search}%'))
        )

    docs = query.order_by(RuleDocument.display_order.asc(), RuleDocument.id.desc()).all()
    categories = [c[0] for c in db.session.query(RuleDocument.category).distinct().all() if c[0]]

    return render_template(
        'public/rules.html',
        docs=docs,
        categories=categories,
        current_category=category,
        search=search
    )

@public_bp.route('/learning-materials')
def learning_materials():
    \"\"\"Public portal: Centralized Learning Materials & E-Learning Link.\"\"\"
    traction = request.args.get('traction', 'ALL')
    category = request.args.get('category', 'ALL')
    search = request.args.get('q', '').strip()

    query = LearningMaterial.query.filter_by(is_active=True)
    if traction != 'ALL':
        query = query.filter_by(traction_type=traction)
    if category != 'ALL':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            (LearningMaterial.title.ilike(f'%{search}%')) |
            (LearningMaterial.description.ilike(f'%{search}%')) |
            (LearningMaterial.content.ilike(f'%{search}%'))
        )

    materials = query.order_by(LearningMaterial.display_order.asc(), LearningMaterial.id.desc()).all()
    categories = [c[0] for c in db.session.query(LearningMaterial.category).distinct().all() if c[0]]

    return render_template(
        'public/learning_materials.html',
        materials=materials,
        categories=categories,
        current_traction=traction,
        current_category=category,
        search=search,
        elearning_url="https://elearninghwh.in/home_page.html"
    )

@public_bp.route('/bulletins')
def bulletins():
    \"\"\"Public portal: Latest Safety Bulletins & Circulars with PDF attachments.\"\"\"
    category = request.args.get('category', 'ALL')
    search = request.args.get('q', '').strip()

    query = SafetyBulletin.query.filter_by(is_active=True)
    if category != 'ALL':
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            (SafetyBulletin.title.ilike(f'%{search}%')) |
            (SafetyBulletin.bulletin_no.ilike(f'%{search}%')) |
            (SafetyBulletin.description.ilike(f'%{search}%'))
        )

    bulletin_list = query.order_by(SafetyBulletin.bulletin_date.desc(), SafetyBulletin.id.desc()).all()
    categories = [c[0] for c in db.session.query(SafetyBulletin.category).distinct().all() if c[0]]

    return render_template(
        'public/bulletins.html',
        bulletins=bulletin_list,
        categories=categories,
        current_category=category,
        search=search
    )"""

code = code.replace(old_rules_learning, new_rules_learning)

with open(public_file, 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated blueprints/public.py successfully.")
