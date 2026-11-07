from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import db
from models import User, Lobby

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this portal section.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'warning')
                return redirect(url_for('auth.login'))
            user = User.query.get(session['user_id'])
            if not user or user.role not in roles:
                flash('Access denied. You do not have permission for this section.', 'danger')
                return redirect(url_for('public.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return redirect_by_role(user)

    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not identifier or not password:
            flash('Please enter both username/mobile and password.', 'danger')
            return render_template('auth/login.html')

        # Find user by username, mobile, or pf_number
        user = User.query.filter(
            (User.username == identifier) | 
            (User.mobile == identifier) | 
            (User.pf_number == identifier)
        ).first()

        # Support CCC lobby alias login (e.g. CCC/KWAE, CCC_KWAE)
        if not user and identifier.upper().startswith('CCC'):
            code = identifier.upper().replace('CCC/', '').replace('CCC_', '').strip()
            lobby_match = Lobby.query.filter_by(code=code).first()
            if lobby_match:
                user = User.query.filter_by(lobby_id=lobby_match.id, sub_role='CCC', is_active=True).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact Divisional Admin or CCC.', 'danger')
                return render_template('auth/login.html')

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['sub_role'] = user.sub_role
            session['full_name'] = user.full_name
            session['must_change_password'] = user.password_must_change

            flash(f'Welcome, {user.full_name} ({user.sub_role or user.role.title()})', 'success')
            
            # Next URL check or redirect by role
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect_by_role(user)
        else:
            flash('Invalid username/mobile or password. Please try again.', 'danger')

    return render_template('auth/login.html')


def redirect_by_role(user):
    if user.is_admin():
        return redirect(url_for('admin.dashboard'))
    elif user.is_control():
        return redirect(url_for('control.dashboard'))
    elif user.is_officer():
        return redirect(url_for('officer.dashboard'))
    elif user.is_supervisor():
        return redirect(url_for('supervisor.dashboard'))
    elif user.is_crew():
        return redirect(url_for('crew.dashboard'))
    return redirect(url_for('public.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    lobbies = Lobby.query.order_by(Lobby.code).all()
    clis = User.query.filter_by(role='supervisor', sub_role='CLI').all()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        pf_number = request.form.get('pf_number', '').strip()
        hrms_id = request.form.get('hrms_id', '').strip()
        designation = request.form.get('designation', '').strip()
        lobby_id = request.form.get('lobby_id')
        cli_id = request.form.get('cli_id')
        password = request.form.get('password', '12345').strip()

        if not full_name or not mobile or not designation or not lobby_id:
            flash('Please fill in all mandatory fields (Name, Mobile, Designation, Lobby).', 'danger')
            return render_template('auth/register.html', lobbies=lobbies, clis=clis)

        # Check existing mobile or PF
        existing = User.query.filter((User.username == mobile) | (User.mobile == mobile)).first()
        if existing:
            flash('A user with this mobile number already exists. Please login.', 'warning')
            return redirect(url_for('auth.login'))

        # Create new running crew user
        new_crew = User(
            username=mobile,
            role='crew',
            sub_role=designation,
            full_name=full_name,
            mobile=mobile,
            pf_number=pf_number,
            hrms_id=hrms_id,
            lobby_id=int(lobby_id) if lobby_id else None,
            cli_id=int(cli_id) if cli_id else None,
            is_active=True,  # Pre-activated as instructed
            password_must_change=(password == '12345')
        )
        new_crew.set_password(password)
        db.session.add(new_crew)
        db.session.commit()

        flash('Registration successful! You can now log in using your Mobile Number.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', lobbies=lobbies, clis=clis)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        old_password = request.form.get('old_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not user.check_password(old_password):
            flash('Current password is incorrect.', 'danger')
            return render_template('auth/change_password.html')

        if len(new_password) < 5:
            flash('New password must be at least 5 characters long.', 'danger')
            return render_template('auth/change_password.html')

        if new_password != confirm_password:
            flash('New password and confirmation do not match.', 'danger')
            return render_template('auth/change_password.html')

        if new_password == '12345':
            flash('You cannot use default password "12345". Please choose a secure password.', 'danger')
            return render_template('auth/change_password.html')

        user.set_password(new_password)
        user.password_must_change = False
        db.session.commit()
        session['must_change_password'] = False

        flash('Password successfully changed! The security warning has been cleared.', 'success')
        return redirect_by_role(user)

    return render_template('auth/change_password.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('public.index'))
