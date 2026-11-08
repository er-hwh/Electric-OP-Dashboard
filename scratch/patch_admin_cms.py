import os
import sys

admin_file = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\blueprints\admin.py"

with open(admin_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Update model imports if not present
old_import = "GoogleSheetLink, UnusualIncident"
new_import = "GoogleSheetLink, UnusualIncident, CarouselSlide, SafetyBulletin, RuleDocument, LearningMaterial, PageContent"

if "CarouselSlide" not in content:
    content = content.replace(old_import, new_import)

cms_code = '''

# ==============================================================================
# CMS & CONTENT MANAGEMENT (BULLETINS, CAROUSEL, RULES, LEARNING, PAGES)
# ==============================================================================

@admin_bp.route('/cms/bulletins', methods=['GET', 'POST'])
def cms_bulletins():
    """Admin: Upload & manage Latest Safety Bulletins with PDF attachments."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        bulletin_no = request.form.get('bulletin_no', '').strip()
        category = request.form.get('category', 'Safety Bulletin').strip()
        bulletin_date_str = request.form.get('bulletin_date', '').strip()
        description = request.form.get('description', '').strip()
        is_active = request.form.get('is_active') == '1'

        if not title:
            flash('Bulletin title is required.', 'danger')
            return redirect(url_for('admin.cms_bulletins'))

        b_date = date.today()
        if bulletin_date_str:
            try:
                b_date = datetime.strptime(bulletin_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        attachment_path = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                fname = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                save_fname = f"sb_{ts}_{fname}"
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'bulletins')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, save_fname))
                attachment_path = f"uploads/bulletins/{save_fname}"

        bulletin = SafetyBulletin(
            bulletin_no=bulletin_no,
            title=title,
            bulletin_date=b_date,
            category=category,
            description=description,
            attachment_path=attachment_path,
            is_active=is_active,
            created_by_id=session.get('user_id')
        )
        db.session.add(bulletin)
        db.session.commit()
        flash(f'Safety bulletin "{title}" published successfully.', 'success')
        return redirect(url_for('admin.cms_bulletins'))

    bulletins = SafetyBulletin.query.order_by(SafetyBulletin.bulletin_date.desc(), SafetyBulletin.id.desc()).all()
    return render_template('admin/cms_bulletins.html', bulletins=bulletins)


@admin_bp.route('/cms/bulletins/<int:bulletin_id>/toggle', methods=['POST'])
def cms_bulletin_toggle(bulletin_id):
    b = SafetyBulletin.query.get_or_404(bulletin_id)
    b.is_active = not b.is_active
    db.session.commit()
    flash(f'Bulletin "{b.title}" is now {"Active" if b.is_active else "Inactive"}.', 'info')
    return redirect(url_for('admin.cms_bulletins'))


@admin_bp.route('/cms/bulletins/<int:bulletin_id>/delete', methods=['POST'])
def cms_bulletin_delete(bulletin_id):
    b = SafetyBulletin.query.get_or_404(bulletin_id)
    if b.attachment_path:
        full_p = os.path.join(current_app.root_path, 'static', b.attachment_path.replace('/', os.sep))
        if os.path.exists(full_p):
            try:
                os.remove(full_p)
            except Exception:
                pass
    db.session.delete(b)
    db.session.commit()
    flash('Bulletin deleted successfully.', 'warning')
    return redirect(url_for('admin.cms_bulletins'))


@admin_bp.route('/cms/carousel', methods=['GET', 'POST'])
def cms_carousel():
    """Admin: Upload banner photos for homepage hero carousel."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        subtitle = request.form.get('subtitle', '').strip()
        button_text = request.form.get('button_text', '').strip()
        button_url = request.form.get('button_url', '').strip()
        display_order = int(request.form.get('display_order', 0) or 0)
        is_active = request.form.get('is_active') == '1'

        if not title:
            flash('Slide title is required.', 'danger')
            return redirect(url_for('admin.cms_carousel'))

        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                fname = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                save_fname = f"slide_{ts}_{fname}"
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'carousel')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, save_fname))
                image_path = f"uploads/carousel/{save_fname}"

        if not image_path:
            flash('An image file is required for carousel slide.', 'danger')
            return redirect(url_for('admin.cms_carousel'))

        slide = CarouselSlide(
            title=title,
            subtitle=subtitle,
            image_path=image_path,
            button_text=button_text,
            button_url=button_url,
            display_order=display_order,
            is_active=is_active,
            created_by_id=session.get('user_id')
        )
        db.session.add(slide)
        db.session.commit()
        flash(f'Carousel slide "{title}" uploaded successfully.', 'success')
        return redirect(url_for('admin.cms_carousel'))

    slides = CarouselSlide.query.order_by(CarouselSlide.display_order.asc(), CarouselSlide.id.desc()).all()
    return render_template('admin/cms_carousel.html', slides=slides)


@admin_bp.route('/cms/carousel/<int:slide_id>/toggle', methods=['POST'])
def cms_carousel_toggle(slide_id):
    s = CarouselSlide.query.get_or_404(slide_id)
    s.is_active = not s.is_active
    db.session.commit()
    flash(f'Slide "{s.title}" status updated.', 'info')
    return redirect(url_for('admin.cms_carousel'))


@admin_bp.route('/cms/carousel/<int:slide_id>/delete', methods=['POST'])
def cms_carousel_delete(slide_id):
    s = CarouselSlide.query.get_or_404(slide_id)
    if s.image_path:
        full_p = os.path.join(current_app.root_path, 'static', s.image_path.replace('/', os.sep))
        if os.path.exists(full_p):
            try:
                os.remove(full_p)
            except Exception:
                pass
    db.session.delete(s)
    db.session.commit()
    flash('Slide deleted successfully.', 'warning')
    return redirect(url_for('admin.cms_carousel'))


@admin_bp.route('/cms/rules', methods=['GET', 'POST'])
def cms_rules():
    """Admin: Upload Rules & Regulations with PDF attachment."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', 'General Rules (GR)').strip()
        rule_reference = request.form.get('rule_reference', '').strip()
        description = request.form.get('description', '').strip()
        display_order = int(request.form.get('display_order', 0) or 0)
        is_active = request.form.get('is_active') == '1'

        if not title:
            flash('Rule document title is required.', 'danger')
            return redirect(url_for('admin.cms_rules'))

        pdf_path = None
        if 'pdf_file' in request.files:
            file = request.files['pdf_file']
            if file and file.filename:
                fname = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                save_fname = f"rule_{ts}_{fname}"
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'rules')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, save_fname))
                pdf_path = f"uploads/rules/{save_fname}"

        if not pdf_path:
            flash('A PDF document is required for Rule & Regulation upload.', 'danger')
            return redirect(url_for('admin.cms_rules'))

        doc = RuleDocument(
            title=title,
            category=category,
            rule_reference=rule_reference,
            description=description,
            pdf_path=pdf_path,
            display_order=display_order,
            is_active=is_active,
            created_by_id=session.get('user_id')
        )
        db.session.add(doc)
        db.session.commit()
        flash(f'Rule Document "{title}" published successfully.', 'success')
        return redirect(url_for('admin.cms_rules'))

    docs = RuleDocument.query.order_by(RuleDocument.display_order.asc(), RuleDocument.id.desc()).all()
    return render_template('admin/cms_rules.html', docs=docs)


@admin_bp.route('/cms/rules/<int:rule_id>/toggle', methods=['POST'])
def cms_rule_toggle(rule_id):
    doc = RuleDocument.query.get_or_404(rule_id)
    doc.is_active = not doc.is_active
    db.session.commit()
    flash(f'Rule "{doc.title}" status updated.', 'info')
    return redirect(url_for('admin.cms_rules'))


@admin_bp.route('/cms/rules/<int:rule_id>/delete', methods=['POST'])
def cms_rule_delete(rule_id):
    doc = RuleDocument.query.get_or_404(rule_id)
    if doc.pdf_path:
        full_p = os.path.join(current_app.root_path, 'static', doc.pdf_path.replace('/', os.sep))
        if os.path.exists(full_p):
            try:
                os.remove(full_p)
            except Exception:
                pass
    db.session.delete(doc)
    db.session.commit()
    flash('Rule document deleted successfully.', 'warning')
    return redirect(url_for('admin.cms_rules'))


@admin_bp.route('/cms/learning', methods=['GET', 'POST'])
def cms_learning():
    """Admin: Upload Learning Materials with content & PDF options."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        traction_type = request.form.get('traction_type', 'COMMON').strip()
        category = request.form.get('category', 'Loco Study Material').strip()
        description = request.form.get('description', '').strip()
        content = request.form.get('content', '').strip()
        external_url = request.form.get('external_url', '').strip()
        display_order = int(request.form.get('display_order', 0) or 0)
        is_active = request.form.get('is_active') == '1'

        if not title:
            flash('Learning material title is required.', 'danger')
            return redirect(url_for('admin.cms_learning'))

        attachment_path = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                fname = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S')
                save_fname = f"learn_{ts}_{fname}"
                upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'learning')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, save_fname))
                attachment_path = f"uploads/learning/{save_fname}"

        mat = LearningMaterial(
            title=title,
            traction_type=traction_type,
            category=category,
            description=description,
            content=content,
            attachment_path=attachment_path,
            external_url=external_url,
            display_order=display_order,
            is_active=is_active,
            created_by_id=session.get('user_id')
        )
        db.session.add(mat)
        db.session.commit()
        flash(f'Learning Material "{title}" added successfully.', 'success')
        return redirect(url_for('admin.cms_learning'))

    materials = LearningMaterial.query.order_by(LearningMaterial.display_order.asc(), LearningMaterial.id.desc()).all()
    return render_template('admin/cms_learning.html', materials=materials)


@admin_bp.route('/cms/learning/<int:mat_id>/toggle', methods=['POST'])
def cms_learning_toggle(mat_id):
    mat = LearningMaterial.query.get_or_404(mat_id)
    mat.is_active = not mat.is_active
    db.session.commit()
    flash(f'Material "{mat.title}" status updated.', 'info')
    return redirect(url_for('admin.cms_learning'))


@admin_bp.route('/cms/learning/<int:mat_id>/delete', methods=['POST'])
def cms_learning_delete(mat_id):
    mat = LearningMaterial.query.get_or_404(mat_id)
    if mat.attachment_path:
        full_p = os.path.join(current_app.root_path, 'static', mat.attachment_path.replace('/', os.sep))
        if os.path.exists(full_p):
            try:
                os.remove(full_p)
            except Exception:
                pass
    db.session.delete(mat)
    db.session.commit()
    flash('Learning material deleted successfully.', 'warning')
    return redirect(url_for('admin.cms_learning'))


@admin_bp.route('/cms/pages', methods=['GET', 'POST'])
def cms_pages():
    """Admin: Key-Value Page Content Management (CMS)."""
    if request.method == 'POST':
        for p in PageContent.query.all():
            val = request.form.get(f'content_{p.id}')
            title = request.form.get(f'title_{p.id}')
            if val is not None:
                p.content_value = val.strip()
            if title is not None:
                p.title = title.strip()
            p.updated_by_id = session.get('user_id')

        new_key = request.form.get('new_content_key', '').strip()
        new_title = request.form.get('new_title', '').strip()
        new_val = request.form.get('new_content_value', '').strip()
        if new_key and new_title and new_val:
            existing = PageContent.query.filter_by(content_key=new_key).first()
            if not existing:
                new_item = PageContent(
                    content_key=new_key,
                    title=new_title,
                    content_value=new_val,
                    updated_by_id=session.get('user_id')
                )
                db.session.add(new_item)

        db.session.commit()
        flash('Page content updated successfully.', 'success')
        return redirect(url_for('admin.cms_pages'))

    pages = PageContent.query.order_by(PageContent.id.asc()).all()
    return render_template('admin/cms_pages.html', pages=pages)
'''

if "def cms_bulletins" not in content:
    content += cms_code

with open(admin_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated blueprints/admin.py with CMS routes and model imports.")
