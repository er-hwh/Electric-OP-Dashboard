import os
from datetime import date
import warnings
from sqlalchemy.exc import LegacyAPIWarning
from flask import Flask, session, g
from config import Config
from database import db

warnings.filterwarnings('ignore', category=LegacyAPIWarning)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    # Context processor to inject current logged in user and lobby list everywhere
    @app.context_processor
    def inject_global_data():
        from models import User, Lobby, Message
        user = None
        unread_count = 0
        if 'user_id' in session:
            user = db.session.get(User, session['user_id'])
            if user:
                # Count unread messages
                if user.is_officer():
                    unread_count = Message.query.filter(
                        (Message.status == 'FORWARDED_TO_OFFICER') |
                        (Message.recipient_id == user.id),
                        Message.is_read == False
                    ).count()
                elif user.is_supervisor():
                    unread_count = Message.query.filter(
                        Message.recipient_id == user.id,
                        Message.status == 'PENDING_CLI_REVIEW',
                        Message.is_read == False
                    ).count()
                elif user.is_crew():
                    unread_count = Message.query.filter(
                        Message.recipient_id == user.id,
                        Message.is_read == False
                    ).count()

        lobbies = Lobby.query.order_by(Lobby.code).all()
        return dict(current_user=user, all_lobbies=lobbies, unread_count=unread_count, today=date.today(), date=date)

    # Register Blueprints
    from blueprints.auth import auth_bp
    from blueprints.public import public_bp
    from blueprints.admin import admin_bp
    from blueprints.officer import officer_bp
    from blueprints.supervisor import supervisor_bp
    from blueprints.crew import crew_bp
    from blueprints.elearning import elearning_bp
    from blueprints.control import control_bp
    from blueprints.duty_hours import duty_hours_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(officer_bp, url_prefix='/officer')
    app.register_blueprint(supervisor_bp, url_prefix='/supervisor')
    app.register_blueprint(crew_bp, url_prefix='/crew')
    app.register_blueprint(elearning_bp, url_prefix='/elearning')
    app.register_blueprint(control_bp, url_prefix='/control')
    app.register_blueprint(control_bp, name='control_root')
    app.register_blueprint(duty_hours_bp)

    @app.route('/favicon.ico')
    def favicon():
        return ('', 204)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        # Ensure default Admin & CNL users exist
        try:
            from models import User
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    role='admin',
                    sub_role='System Administrator',
                    full_name='Divisional System Admin',
                    password_must_change=True
                )
                admin.set_password('12345')
                db.session.add(admin)

            cnl_user = User.query.filter_by(username='CNL_HWH').first()
            if not cnl_user:
                cnl_user = User(
                    username='CNL_HWH',
                    role='control',
                    sub_role='CNL',
                    full_name='Chief Power Controller / CNL HWH',
                    mobile='9002022399',
                    password_must_change=True
                )
                cnl_user.set_password('12345')
                db.session.add(cnl_user)

            db.session.commit()
        except Exception as e:
            pass

    print("Starting Electric Operation Department, Howrah Division Portal on http://127.0.0.1:5000 ...")
    app.run(host='0.0.0.0', port=5000, debug=True)
