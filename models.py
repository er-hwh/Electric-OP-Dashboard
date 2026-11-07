from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

class Lobby(db.Model):
    __tablename__ = 'lobbies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False) # HWH, BWN, RPH, etc.
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50))
    ccc_name = db.Column(db.String(100)) # Chief Crew Controller Name
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='lobby', lazy='dynamic', foreign_keys='User.lobby_id')

    def __repr__(self):
        return f"<Lobby {self.code} - {self.name}>"


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False) # admin, Sr. DEE(OP)/HWH, CLI ID, Mobile
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False) # 'admin', 'officer', 'supervisor', 'crew'
    sub_role = db.Column(db.String(50)) # 'Sr. DEE(OP)', 'AEE(OP)', 'AME(P)', 'CCC', 'CLI', 'LPM', 'LPP', 'MMAN', 'LPG', 'LPS-II', 'LPS-I', 'Sr. ALP', 'ALP'
    full_name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20))
    email = db.Column(db.String(100))
    pf_number = db.Column(db.String(50)) # PF / Staff No / HRMS ID
    hrms_id = db.Column(db.String(50))
    
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=True)
    cli_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Nominated CLI for running staff
    
    is_active = db.Column(db.Boolean, default=True)
    password_must_change = db.Column(db.Boolean, default=True) # True until user changes from '12345'
    profile_image = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assigned_crews = db.relationship('User', backref=db.backref('nominated_cli', remote_side=[id]), lazy='dynamic')
    footplate_inspections = db.relationship('FootplateInspection', backref='inspector_cli', foreign_keys='FootplateInspection.cli_id', lazy='dynamic')
    crew_inspections = db.relationship('FootplateInspection', backref='inspected_crew', foreign_keys='FootplateInspection.crew_id', lazy='dynamic')
    training_records = db.relationship('TrainingRecord', backref='crew_member', foreign_keys='TrainingRecord.crew_id', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        if password == '12345':
            self.password_must_change = True
        else:
            self.password_must_change = False

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_officer(self):
        return self.role == 'officer'

    def is_supervisor(self):
        return self.role == 'supervisor'

    def is_crew(self):
        return self.role == 'crew'

    def is_admin(self):
        return self.role == 'admin'

    def is_control(self):
        return self.role == 'control' or self.sub_role in ['CNL', 'Control', 'Power Controller', 'TLC', 'Chief Power Controller', 'PCNL']

    @property
    def power_level(self):
        """
        Hierarchy of Power:
        5: Admin (Highest - System Administration & System Edit)
        4: Officer (Sr. DEE(OP) > DEE(OP) > AEE(OP) / AME(P))
        3: CNL (Control / Power Controller / TLC)
        2: CLI (Chief Loco Inspector & CCC Supervisor)
        1: Crew (Running Staff - LPM, LPP, LPG, LPS, ALP)
        0: Public / Guest
        """
        if self.is_admin():
            return 5
        elif self.is_officer():
            return 4
        elif self.is_control():
            return 3
        elif self.is_supervisor():
            return 2
        elif self.is_crew():
            return 1
        return 0

    @property
    def power_level_name(self):
        if self.is_admin():
            return "System Administrator (Level 5)"
        elif self.is_officer():
            return f"{self.officer_level_title} (Level 4)"
        elif self.is_control():
            return "Control / CNL (Level 3)"
        elif self.is_supervisor():
            return f"Supervisor / {self.sub_role or 'CLI'} (Level 2)"
        elif self.is_crew():
            return f"Running Staff / {self.sub_role or 'Crew'} (Level 1)"
        return "Public User"

    @property
    def officer_rank(self):
        """
        Officer Hierarchy:
        1: Sr. DEE(OP)/HWH (Branch Officer - Head of Branch)
        2: DEE(OP)/HWH     (Divisional Electrical Engineer)
        3: AEE(OP)/HWH     (Assistant Electrical Engineer)
        4: AME(P)/HWH      (Assistant Mechanical Engineer - Power)
        5: Other Officers
        """
        if not self.is_officer():
            return 99
        s = (self.sub_role or '').upper().replace(' ', '')
        if 'SR.DEE' in s or 'SRDEE' in s:
            return 1
        elif 'DEE' in s:
            return 2
        elif 'AEE' in s:
            return 3
        elif 'AME' in s:
            return 4
        return 5

    @property
    def officer_level_title(self):
        rank = self.officer_rank
        if rank == 1:
            return "Branch Officer (Head of Branch)"
        elif rank == 2:
            return "Divisional Officer"
        elif rank in [3, 4]:
            return "Assistant Officer"
        return "Divisional Officer"

    def is_senior_officer(self):
        """Returns True if officer is Sr. DEE(OP) or DEE(OP)."""
        return self.is_officer() and self.officer_rank <= 2

    def can_edit_system(self):
        """Strict Rule: Only Admin can perform system edits."""
        return self.is_admin()


class Notice(db.Model):
    __tablename__ = 'notices'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), default='Notice') # 'Notice', 'Circular', 'Safety Drive', 'Instruction', 'Seniority', 'Result'
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    target_audience = db.Column(db.String(50), default='ALL') # 'ALL', 'CLI_ONLY', 'CREW_ONLY', 'LOBBY_WISE'
    target_lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=True)
    published_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    is_urgent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    publisher = db.relationship('User', foreign_keys=[published_by_id])
    target_lobby = db.relationship('Lobby', foreign_keys=[target_lobby_id])
    acknowledgements = db.relationship('NoticeAcknowledgement', backref='notice', lazy='dynamic', cascade='all, delete-orphan')


class NoticeAcknowledgement(db.Model):
    __tablename__ = 'notice_acknowledgements'
    
    id = db.Column(db.Integer, primary_key=True)
    notice_id = db.Column(db.Integer, db.ForeignKey('notices.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow)
    remarks = db.Column(db.String(255))

    user = db.relationship('User', foreign_keys=[user_id])


class CounsellingTopic(db.Model):
    __tablename__ = 'counselling_topics'
    
    id = db.Column(db.Integer, primary_key=True)
    counselling_type = db.Column(db.String(50), default='MONTHLY') # 'MONTHLY', 'SPECIAL'
    month_year = db.Column(db.String(50)) # e.g. "October 2026"
    topic_date = db.Column(db.Date, default=date.today)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False) # Counselling instructions
    case_analysis = db.Column(db.Text) # Unusual occurrence / safety case study
    rule_reference = db.Column(db.String(100)) # e.g. "GR 3.61 & SR 3.61(d), SR 4.50"
    file_path = db.Column(db.String(255))
    
    # Workflow: DRAFT -> PENDING_APPROVAL -> APPROVED / REJECTED
    status = db.Column(db.String(50), default='APPROVED') 
    proposed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # CLI who drafted
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Officer who approved/signed
    approval_date = db.Column(db.DateTime, nullable=True)
    officer_signature_remarks = db.Column(db.Text, nullable=True)
    questions_json = db.Column(db.Text, nullable=True) # JSON array of safety check questions

    issued_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    issuer = db.relationship('User', foreign_keys=[issued_by_id])
    proposer = db.relationship('User', foreign_keys=[proposed_by_id])
    approver = db.relationship('User', foreign_keys=[approved_by_id])
    acknowledgements = db.relationship('CounsellingAcknowledgement', backref='counselling_topic', lazy='dynamic', cascade='all, delete-orphan')

    def get_questions(self):
        import json
        if not self.questions_json:
            return []
        try:
            return json.loads(self.questions_json)
        except Exception:
            return []


class CounsellingAcknowledgement(db.Model):
    __tablename__ = 'counselling_acknowledgements'
    
    id = db.Column(db.Integer, primary_key=True)
    counselling_id = db.Column(db.Integer, db.ForeignKey('counselling_topics.id'), nullable=False)
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow)
    quiz_score = db.Column(db.Integer, default=0)
    passed = db.Column(db.Boolean, default=True)
    understood = db.Column(db.Boolean, default=True)
    doubt_or_query = db.Column(db.Text)

    crew = db.relationship('User', foreign_keys=[crew_id])


class TrainingRecord(db.Model):
    __tablename__ = 'training_records'
    
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    training_type = db.Column(db.String(100), nullable=False) # 'Refresher DSL', 'Refresher ELEC', 'Refresher GR & SR', 'Automatic Block System', 'PME', 'Safety Camp'
    institute = db.Column(db.String(100), default='ZRTI Bhuli')
    last_done_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    certificate_no = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status_info(self):
        today = date.today()
        days_left = (self.due_date - today).days
        if days_left < 0:
            return {'status': 'OVERDUE', 'class': 'danger', 'badge': f'Overdue by {-days_left}d'}
        elif days_left <= 30:
            return {'status': 'DUE_SOON', 'class': 'warning', 'badge': f'Due in {days_left}d'}
        else:
            return {'status': 'VALID', 'class': 'success', 'badge': f'Valid ({days_left}d left)'}


class FootplateInspection(db.Model):
    __tablename__ = 'footplate_inspections'
    
    id = db.Column(db.Integer, primary_key=True)
    cli_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    inspection_date = db.Column(db.Date, nullable=False, default=date.today)
    train_no = db.Column(db.String(50))
    loco_no = db.Column(db.String(50))
    from_station = db.Column(db.String(50))
    to_station = db.Column(db.String(50))
    departure_time = db.Column(db.String(20))
    arrival_time = db.Column(db.String(20))
    grading = db.Column(db.String(10), default='A') # 'A', 'B', 'C', 'D'
    footplate_km = db.Column(db.Float, default=0.0) # Actual KM travelled on footplate for KMA (Rule 1515 ACS 64)
    aspects_covered = db.Column(db.Text) # Signal exchange, RS valve test, calling-on aspect, neutral section coasting
    deficiencies = db.Column(db.Text)
    counselling_given = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # None if escalated to all officers
    forwarded_by_cli_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='CREW_TO_CLI') # 'CREW_TO_CLI', 'CLI_FORWARD_TO_OFFICER', 'OFFICER_DIRECT_CREW', 'OFFICER_TO_CLI', 'CLI_TO_CREW'
    status = db.Column(db.String(50), default='PENDING_CLI_REVIEW') # 'PENDING_CLI_REVIEW', 'FORWARDED_TO_OFFICER', 'RESOLVED_BY_CLI', 'OFFICER_REPLIED', 'DELIVERED'
    
    cli_remarks = db.Column(db.Text)
    officer_remarks = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])
    forwarder_cli = db.relationship('User', foreign_keys=[forwarded_by_cli_id])
    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')


class OfficerSay(db.Model):
    __tablename__ = 'officer_says'
    
    id = db.Column(db.Integer, primary_key=True)
    designation = db.Column(db.String(100), nullable=False) # Sr. DEE(OP)/HWH, AEE(OP)/HWH, AME(P)/HWH
    officer_name = db.Column(db.String(150), nullable=False)
    photo_filename = db.Column(db.String(255), default='officer_default.png')
    tagline = db.Column(db.String(255))
    message = db.Column(db.Text, nullable=False)
    priority_order = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)


class CrewCounsellingRecord(db.Model):
    """Stores per-crew counselling records imported from the Master Counselling Sheet (Excel)."""
    __tablename__ = 'crew_counselling_records'

    id = db.Column(db.Integer, primary_key=True)
    crew_id_str = db.Column(db.String(30))            # CMS Crew ID e.g. AZ1069
    crew_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Linked User row if found
    cli_name = db.Column(db.String(150))               # CLI column from sheet
    crew_name = db.Column(db.String(150))
    crew_hq = db.Column(db.String(30))
    cug = db.Column(db.String(30))
    designation = db.Column(db.String(30))
    designation_since = db.Column(db.String(50))
    pf_no = db.Column(db.String(50))
    grade = db.Column(db.String(10))
    last_footplate = db.Column(db.String(100))
    technical_counselling = db.Column(db.String(100))
    safety_counselling = db.Column(db.String(100))
    counselling_verified_by = db.Column(db.String(100))
    last_spm_check = db.Column(db.String(100))
    last_cvvrs_check = db.Column(db.String(100))
    ba_fail_history = db.Column(db.String(100))
    mobile_habit = db.Column(db.String(100))
    spad_history = db.Column(db.String(100))
    da_case = db.Column(db.String(100))
    family_issue = db.Column(db.Text)
    health_issue = db.Column(db.Text)
    baby_below_6_months = db.Column(db.String(20))
    accident_prone = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    crew_user = db.relationship('User', foreign_keys=[crew_user_id], backref='counselling_record')


class ELearningRule(db.Model):
    __tablename__ = 'elearning_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    chapter_no = db.Column(db.String(50))
    chapter_title = db.Column(db.String(150))
    rule_no = db.Column(db.String(50), nullable=False) # e.g. "GR 3.61", "SR 4.50"
    rule_title = db.Column(db.String(255), nullable=False)
    general_rule = db.Column(db.Text)
    subsidiary_rule = db.Column(db.Text)
    category = db.Column(db.String(100)) # "Signals", "Train Working", "OHE & Traction", "Caution Orders"
    key_points = db.Column(db.Text)
    youtube_video_id = db.Column(db.String(100))
    youtube_title = db.Column(db.String(255))
    animation_json = db.Column(db.Text)

    def get_animation(self):
        import json
        if not self.animation_json:
            return None
        try:
            return json.loads(self.animation_json)
        except Exception:
            return None


class ELearningQuiz(db.Model):
    __tablename__ = 'elearning_quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id_str = db.Column(db.String(50))
    chapter_no = db.Column(db.String(50))
    chapter_title = db.Column(db.String(150))
    rule_ref = db.Column(db.String(100))
    question = db.Column(db.Text, nullable=False)
    options_json = db.Column(db.Text, nullable=False)
    correct_index = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(50), default='Intermediate')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_options(self):
        import json
        if not self.options_json:
            return []
        try:
            return json.loads(self.options_json)
        except Exception:
            return []


class PhotoGallery(db.Model):
    __tablename__ = 'photo_gallery'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), default='Operations') # 'Locomotives', 'Lobby Facilities', 'Safety Seminars', 'Inspection'
    image_filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
