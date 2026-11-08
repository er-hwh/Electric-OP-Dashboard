from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from database import db

class Lobby(db.Model):
    __tablename__ = 'lobbies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False) # HWH, BWN, RPH, etc.
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50))
    ccc_name = db.Column(db.String(100)) # Chief Crew Controller Name
    is_sister_lobby = db.Column(db.Boolean, default=False) # Sister lobbies: NHT, SNT, KURV
    in_charge_cli_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Assigned CLI In-Charge
    operational_jurisdiction = db.Column(db.String(255)) # Jurisdiction description / routes
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship('User', backref='lobby', lazy='dynamic', foreign_keys='User.lobby_id')
    in_charge_cli = db.relationship('User', foreign_keys=[in_charge_cli_id])

    def __repr__(self):
        return f"<Lobby {self.code} - {self.name}>"


class CustomField(db.Model):
    """Dynamic Custom Field Definitions for Crew Database."""
    __tablename__ = 'custom_fields'

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(50), default='crew') # 'crew', 'cli', etc.
    field_name = db.Column(db.String(100), nullable=False, unique=True) # key identifier e.g. blood_group
    field_label = db.Column(db.String(150), nullable=False) # human readable label
    field_type = db.Column(db.String(50), default='text') # 'text', 'number', 'date', 'select'
    options_json = db.Column(db.Text, nullable=True) # JSON list for dropdown options
    is_required = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_options(self):
        import json
        if not self.options_json:
            return []
        try:
            return json.loads(self.options_json)
        except Exception:
            return []


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
    operational_jurisdiction = db.Column(db.String(255))
    custom_fields_json = db.Column(db.Text, nullable=True) # Dynamic key-value store
    date_of_birth = db.Column(db.Date, nullable=True) # DOB for PME age frequency tiering
    date_of_appointment = db.Column(db.Date, nullable=True) # Service seniority
    pme_last_done_date = db.Column(db.Date, nullable=True)
    pme_due_date = db.Column(db.Date, nullable=True)
    pme_fitness_status = db.Column(db.String(50), default='Fit A-One')
    
    is_active = db.Column(db.Boolean, default=True)
    password_must_change = db.Column(db.Boolean, default=True) # True until user changes from '12345'
    profile_image = db.Column(db.String(255), default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assigned_crews = db.relationship('User', backref=db.backref('nominated_cli', remote_side=[id]), lazy='dynamic')
    footplate_inspections = db.relationship('FootplateInspection', backref='inspector_cli', foreign_keys='FootplateInspection.cli_id', lazy='dynamic')
    crew_inspections = db.relationship('FootplateInspection', backref='inspected_crew', foreign_keys='FootplateInspection.crew_id', lazy='dynamic')
    training_records = db.relationship('TrainingRecord', backref='crew_member', foreign_keys='TrainingRecord.crew_id', lazy='dynamic')

    def get_custom_fields(self):
        import json
        if not self.custom_fields_json:
            return {}
        try:
            return json.loads(self.custom_fields_json)
        except Exception:
            return {}

    def set_custom_field(self, key, value):
        import json
        data = self.get_custom_fields()
        data[key] = value
        self.custom_fields_json = json.dumps(data)

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

    def is_tlc(self):
        return self.role == 'control' and ('TLC' in (self.sub_role or '').upper() or self.username.upper() == 'TLC')

    def is_pcnl(self):
        return self.role == 'control' and ('PCNL' in (self.sub_role or '').upper() or self.username.upper() == 'PCNL')

    def is_control(self):
        return self.role == 'control' or self.is_tlc() or self.is_pcnl() or (self.sub_role or '').upper() in ['CNL', 'CONTROL', 'POWER CONTROLLER', 'TLC', 'PCNL', 'CHIEF POWER CONTROLLER']

    def can_access_tools(self):
        """Important tools access: Admin has full access, TLC and PCNL have operational tool access."""
        return self.is_admin() or self.is_control()

    @property
    def power_level(self):
        """
        Hierarchy of Power:
        5: Admin (Highest - System Administration & System Edit)
        4: Officer (Sr. DEE(OP) > AEE(OP) / AME(P)) & Control (TLC / PCNL - equal operational viewing parity + tools)
        2: CLI (Chief Loco Inspector Supervisor)
        1: Crew (Running Staff - LPM, LPP, MMAN, LPG, LPS-I, LPS-II, SALP, ALP)
        0: Public / Guest
        """
        if self.is_admin():
            return 5
        elif self.is_officer() or self.is_control():
            return 4
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
            return f"{self.sub_role or 'Officer'} (Level 4 - Officer)"
        elif self.is_tlc():
            return "Traction Loco Control - TLC (Level 4 - Operational Control)"
        elif self.is_pcnl():
            return "Power Control - PCNL (Level 4 - Operational Control)"
        elif self.is_control():
            return "Operational Control - TLC/PCNL (Level 4)"
        elif self.is_supervisor():
            return f"Chief Loco Inspector / {self.sub_role or 'CLI'} (Level 2)"
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

    def get_age(self, as_of_date=None):
        """Calculates employee age in completed years."""
        if not self.date_of_birth:
            return 35  # Sensible default if DOB not yet updated
        ref_date = as_of_date or date.today()
        years = ref_date.year - self.date_of_birth.year
        if (ref_date.month, ref_date.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        return max(years, 18)

    def compute_pme_frequency_years(self, age=None):
        """
        Railway Medical Standard (A-One Category):
        - Age <= 45 years: Every 4 years
        - Age > 45 to 55 years: Every 2 years
        - Age > 55 years: Every 1 year (Annual)
        """
        if age is None:
            age = self.get_age()
        if age <= 45:
            return 4
        elif age <= 55:
            return 2
        else:
            return 1

    def calculate_next_pme_due(self, last_done_date=None):
        """Calculates next PME due date based on age at last PME examination."""
        base_date = last_done_date or self.pme_last_done_date or date.today()
        age_at_pme = self.get_age(base_date)
        freq_years = self.compute_pme_frequency_years(age_at_pme)
        try:
            return base_date.replace(year=base_date.year + freq_years)
        except ValueError:
            return base_date.replace(year=base_date.year + freq_years, day=28)

    @property
    def pme_status_info(self):
        """Returns live PME status dictionary with badges."""
        if not self.pme_due_date:
            return {'status': 'NOT_SET', 'class': 'secondary', 'badge': 'PME Not Set', 'days': 999, 'days_left': 999}
        today = date.today()
        days_left = (self.pme_due_date - today).days
        if days_left < 0:
            return {'status': 'OVERDUE', 'class': 'danger', 'badge': f'PME Overdue by {-days_left}d', 'days': days_left, 'days_left': days_left}
        elif days_left <= 30:
            return {'status': 'DUE_SOON', 'class': 'warning', 'badge': f'PME Due in {days_left}d', 'days': days_left, 'days_left': days_left}
        else:
            return {'status': 'VALID', 'class': 'success', 'badge': f'Valid ({days_left}d left)', 'days': days_left, 'days_left': days_left}

    def get_last_counselling_date(self):
        """Returns the date of last safety counselling."""
        log = CrewCounsellingLog.query.filter_by(crew_id=self.id).order_by(CrewCounsellingLog.counselling_date.desc()).first()
        if log:
            return log.counselling_date
        rec = CrewCounsellingRecord.query.filter(
            (CrewCounsellingRecord.crew_user_id == self.id) |
            (CrewCounsellingRecord.cug == self.mobile) |
            (CrewCounsellingRecord.crew_id_str == self.username)
        ).first()
        if rec and rec.safety_counselling:
            try:
                from blueprints.supervisor import parse_date_value
                return parse_date_value(rec.safety_counselling)
            except Exception:
                return None
        return None

    @property
    def counselling_status(self):
        """Returns status of monthly safety counselling (>30 days alert)."""
        last_d = self.get_last_counselling_date()
        if not last_d:
            return {'status': 'OVERDUE', 'days_ago': 999, 'days_elapsed': 999, 'is_overdue': True, 'badge': 'danger', 'last_date': None, 'text': 'Overdue (>30d)'}
        days_ago = (date.today() - last_d).days
        is_over = (days_ago > 30)
        if is_over:
            return {'status': 'OVERDUE', 'days_ago': days_ago, 'days_elapsed': days_ago, 'is_overdue': True, 'badge': 'danger', 'last_date': last_d, 'text': f'Overdue ({days_ago}d ago)'}
        elif days_ago >= 25:
            return {'status': 'DUE_SOON', 'days_ago': days_ago, 'days_elapsed': days_ago, 'is_overdue': False, 'badge': 'warning', 'last_date': last_d, 'text': f'Due Soon ({30 - days_ago}d left)'}
        else:
            return {'status': 'OK', 'days_ago': days_ago, 'days_elapsed': days_ago, 'is_overdue': False, 'badge': 'success', 'last_date': last_d, 'text': f'Valid ({days_ago}d ago)'}



class Notice(db.Model):
    __tablename__ = 'notices'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    notice_number = db.Column(db.String(100), nullable=True) # Official circular reference e.g. HWH/E-OP/SAFETY/2026/04
    category = db.Column(db.String(100), default='Safety Circular') # 'Safety Circular', 'Electric Traction', 'Diesel Traction', 'GR & SR', 'Technical Bulletin', 'Notice'
    traction_type = db.Column(db.String(20), default='ALL') # 'ALL', 'ELECTRIC', 'DIESEL', 'BOTH'
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    target_audience = db.Column(db.String(50), default='ALL') # 'ALL', 'CLI_ONLY', 'CREW_ONLY', 'LOBBY_WISE'
    target_lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=True)
    published_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    is_active = db.Column(db.Boolean, default=True)
    is_urgent = db.Column(db.Boolean, default=False)
    is_mandatory = db.Column(db.Boolean, default=True) # Must be acknowledged by running crews before full portal access
    requires_signature = db.Column(db.Boolean, default=False) # Digital officer endorsement/sign-off required
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)
    officer_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def attachment_path(self):
        return self.file_path

    @attachment_path.setter
    def attachment_path(self, val):
        self.file_path = val

    @property
    def posted_by_id(self):
        return self.published_by_id

    @posted_by_id.setter
    def posted_by_id(self, val):
        self.published_by_id = val

    @property
    def approved_by(self):
        return self.approver

    # Relationships
    publisher = db.relationship('User', foreign_keys=[published_by_id])
    approver = db.relationship('User', foreign_keys=[approved_by_id])
    target_lobby = db.relationship('Lobby', foreign_keys=[target_lobby_id])
    acknowledgements = db.relationship('NoticeAcknowledgement', backref='notice', lazy='dynamic', cascade='all, delete-orphan')

    def get_ack_count(self):
        return self.acknowledgements.count()

    def is_acknowledged_by(self, user_id):
        return self.acknowledgements.filter_by(user_id=user_id).first() is not None

    def get_compliance_stats(self, lobby_id=None):
        """Returns total eligible, acknowledged, and percentage."""
        query = User.query.filter_by(role='crew', is_active=True)
        if self.target_lobby_id:
            query = query.filter_by(lobby_id=self.target_lobby_id)
        elif lobby_id:
            query = query.filter_by(lobby_id=lobby_id)
        total_eligible = query.count() or 1
        
        acked = self.acknowledgements.join(User, NoticeAcknowledgement.user_id == User.id).filter(User.role == 'crew', User.is_active == True)
        if self.target_lobby_id:
            acked = acked.filter(User.lobby_id == self.target_lobby_id)
        elif lobby_id:
            acked = acked.filter(User.lobby_id == lobby_id)
        ack_cnt = acked.count()
        pct = round((ack_cnt / total_eligible) * 100, 1) if total_eligible else 0
        return {
            'eligible': total_eligible,
            'total_crews': total_eligible,
            'acknowledged': ack_cnt,
            'acked_count': ack_cnt,
            'pending': max(0, total_eligible - ack_cnt),
            'unacked_count': max(0, total_eligible - ack_cnt),
            'percentage': min(100.0, pct)
        }


class NoticeAcknowledgement(db.Model):
    __tablename__ = 'notice_acknowledgements'
    
    id = db.Column(db.Integer, primary_key=True)
    notice_id = db.Column(db.Integer, db.ForeignKey('notices.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)
    device_info = db.Column(db.String(255), nullable=True)
    is_confirmed = db.Column(db.Boolean, default=True)
    remarks = db.Column(db.String(255))

    user = db.relationship('User', foreign_keys=[user_id])


class CounsellingTopic(db.Model):
    __tablename__ = 'counselling_topics'
    
    id = db.Column(db.Integer, primary_key=True)
    counselling_type = db.Column(db.String(50), default='MONTHLY') # 'MONTHLY', 'SPECIAL'
    traction_type = db.Column(db.String(20), default='ALL') # 'ALL', 'ELECTRIC', 'DIESEL', 'GENERAL'
    drive_name = db.Column(db.String(100), nullable=True)
    month_year = db.Column(db.String(50)) # e.g. "October 2026"
    topic_date = db.Column(db.Date, default=date.today)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False) # Counselling instructions
    case_analysis = db.Column(db.Text) # Unusual occurrence / safety case study
    rule_reference = db.Column(db.String(100)) # e.g. "GR 3.61 & SR 3.61(d), SR 4.50"
    file_path = db.Column(db.String(255))
    is_mandatory = db.Column(db.Boolean, default=True)
    
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

    def get_ack_count(self):
        return self.acknowledgements.count()


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


class CrewCounsellingLog(db.Model):
    """
    Individual CLI-to-crew safety and operational counselling sessions.
    Captures: Topic, Date, Location, Mode, Crew Response, CLI Remarks, and Crew Acknowledgement.
    """
    __tablename__ = 'crew_counselling_logs'

    id = db.Column(db.Integer, primary_key=True)
    cli_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    counselling_date = db.Column(db.Date, default=date.today, nullable=False)
    counselling_type = db.Column(db.String(50), default='MONTHLY_SAFETY') # 'MONTHLY_SAFETY', 'SPECIAL_DRIVE', 'TECHNICAL', 'SPAD_PREVENTION', 'FOOTPLATE'
    topic = db.Column(db.String(255), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('counselling_topics.id'), nullable=True)
    location = db.Column(db.String(100), default='Lobby')
    counselling_mode = db.Column(db.String(50), default='One-to-One') # 'One-to-One', 'Cab / Footplate', 'Group Briefing'
    crew_response = db.Column(db.Text) # Crew feedback, understanding, doubts
    cli_remarks = db.Column(db.Text) # CLI directives / observations
    
    crew_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    acknowledgement_note = db.Column(db.String(255), nullable=True)

    officer_remarks = db.Column(db.Text, nullable=True)
    officer_remarked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    officer_remarked_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    cli = db.relationship('User', foreign_keys=[cli_id])
    crew = db.relationship('User', foreign_keys=[crew_id])
    topic_ref = db.relationship('CounsellingTopic', foreign_keys=[topic_id])
    officer_remarker = db.relationship('User', foreign_keys=[officer_remarked_by_id])

    @property
    def is_recent(self):
        return (date.today() - self.counselling_date).days <= 30


class TrainingRecord(db.Model):
    __tablename__ = 'training_records'
    
    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    training_type = db.Column(db.String(100), nullable=False) 
    # 'Refresher ELEC', 'Refresher DSL', 'Refresher GR & SR', 'Automatic Block System', 'Safety Camp',
    # 'ALP to SALP Promotional', 'SALP to LPS Promotional', 'LPS to LPG Promotional', 
    # 'LPG to LPP Promotional', 'LPP to LPM Promotional', 'Simulator Training', '3-Phase Loco Induction'
    
    training_category = db.Column(db.String(50), default='REFRESHER') # 'REFRESHER', 'ABS', 'PROMOTIONAL', 'SAFETY_CAMP', 'SPECIAL'
    institute = db.Column(db.String(100), default='ZRTI Bhuli')
    last_done_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    validity_months = db.Column(db.Integer, default=36)
    certificate_no = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    crew = db.relationship('User', foreign_keys=[crew_id], overlaps="crew_member,training_records")

    @property
    def course_name(self):
        return self.training_type

    @property
    def completion_date(self):
        return self.last_done_date

    @classmethod
    def calculate_due_date(cls, last_done_date, training_type):
        """
        Railway Training Validity Rules:
        - Automatic Block System (ABS): 6 Months (180 days)
        - Safety Camp: 1 Year (12 months)
        - Refresher ELEC, Refresher DSL, Refresher GR & SR: 3 Years (36 months)
        - Promotional / Conversion: 3 Years (36 months)
        """
        tt_upper = (training_type or '').upper()
        if 'ABS' in tt_upper or 'AUTOMATIC BLOCK' in tt_upper:
            month = last_done_date.month + 6
            year = last_done_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            day = min(last_done_date.day, 28)
            return date(year, month, day)
        elif 'SAFETY CAMP' in tt_upper:
            try:
                return last_done_date.replace(year=last_done_date.year + 1)
            except ValueError:
                return last_done_date.replace(year=last_done_date.year + 1, day=28)
        else:
            try:
                return last_done_date.replace(year=last_done_date.year + 3)
            except ValueError:
                return last_done_date.replace(year=last_done_date.year + 3, day=28)

    @property
    def status_info(self):
        today = date.today()
        days_left = (self.due_date - today).days
        if days_left < 0:
            return {'status': 'OVERDUE', 'class': 'danger', 'badge': f'Overdue by {-days_left}d', 'days': days_left}
        elif days_left <= 30:
            return {'status': 'DUE_SOON', 'class': 'warning', 'badge': f'Due in {days_left}d', 'days': days_left}
        else:
            return {'status': 'VALID', 'class': 'success', 'badge': f'Valid ({days_left}d left)', 'days': days_left}


class MedicalRecord(db.Model):
    """Periodic Medical Examination (PME) Records for Running Staff (A-1 Category)."""
    __tablename__ = 'medical_records'

    id = db.Column(db.Integer, primary_key=True)
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    last_pme_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    medical_category = db.Column(db.String(20), default='A-One')
    fitness_status = db.Column(db.String(50), default='Fit A-One') # 'Fit A-One', 'Fit with Glasses', 'Fit without Glasses', 'Under Observation', 'Unfit A-One'
    hospital_name = db.Column(db.String(100), default='Divisional Railway Hospital Howrah')
    certificate_no = db.Column(db.String(100))
    age_at_pme = db.Column(db.Integer, default=35)
    frequency_years = db.Column(db.Integer, default=4) # 4, 2, or 1 based on age
    vision_acuity = db.Column(db.String(100), default='6/6, 6/6 without glasses')
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    crew = db.relationship('User', foreign_keys=[crew_id], backref=db.backref('pme_records', lazy='dynamic'))

    @property
    def hospital(self):
        return self.hospital_name

    @property
    def fit_memo_no(self):
        return self.certificate_no

    @property
    def examination_date(self):
        return self.last_pme_date

    @property
    def status_info(self):
        today = date.today()
        days_left = (self.due_date - today).days
        if days_left < 0:
            return {'status': 'OVERDUE', 'class': 'danger', 'badge': f'PME Overdue by {-days_left}d', 'days': days_left}
        elif days_left <= 30:
            return {'status': 'DUE_SOON', 'class': 'warning', 'badge': f'PME Due in {days_left}d', 'days': days_left}
        else:
            return {'status': 'VALID', 'class': 'success', 'badge': f'Valid ({days_left}d left)', 'days': days_left}


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
    officer_remarks = db.Column(db.Text)
    officer_remarked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    officer_remarked_at = db.Column(db.DateTime, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    crew_user = db.relationship('User', foreign_keys=[crew_user_id], backref='counselling_record')
    officer_reviewer = db.relationship('User', foreign_keys=[officer_remarked_by_id])


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


class CLIMovement(db.Model):
    """
    Daily CLI Movement & Operational Supervision Records.
    Subject to 3-month (90-day) data retention policy.
    Master crew records, counselling, training, and medical are permanent.
    """
    __tablename__ = 'cli_movements'

    id = db.Column(db.Integer, primary_key=True)
    cli_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_date = db.Column(db.Date, nullable=False, default=date.today)
    
    # Activity Classification
    # 'Footplate Inspection', 'CVVRS Inspection', 'SPM Analysis', 'Crew Counselling',
    # 'Loco Failure Attendance', 'Crew Problem Attendance', 'Yard Inspection', 
    # 'Station Inspection', 'Safety Seminar / Drive', 'Other Supervisory Duties'
    activity_type = db.Column(db.String(100), nullable=False) 

    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=True)
    location = db.Column(db.String(150))
    section_from = db.Column(db.String(50))
    section_to = db.Column(db.String(50))
    train_no = db.Column(db.String(50))
    loco_no = db.Column(db.String(50))
    footplate_km = db.Column(db.Float, default=0.0)
    departure_time = db.Column(db.String(20))
    arrival_time = db.Column(db.String(20))

    # Crew Attended / Inspected
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    crew_name_manual = db.Column(db.String(150))
    crew_id_str = db.Column(db.String(50)) # CMS ID / PF No
    crew_category = db.Column(db.String(50)) # LPM, LPP, LPG, etc.

    # Supervision Findings & Corrective Action
    grading = db.Column(db.String(10), default='A') # A, B, C, D
    observations_irregularities = db.Column(db.Text)
    corrective_action = db.Column(db.Text) # on-spot counselling, defect booked, action taken
    remarks = db.Column(db.Text)

    # Officer / Control Review & Remarks (Officers cannot edit CLI data, but can add remarks)
    officer_remarks = db.Column(db.Text)
    officer_remarked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    officer_remarked_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cli = db.relationship('User', foreign_keys=[cli_id], backref=db.backref('cli_movements', lazy='dynamic'))
    crew = db.relationship('User', foreign_keys=[crew_id])
    lobby = db.relationship('Lobby', foreign_keys=[lobby_id])
    officer_reviewer = db.relationship('User', foreign_keys=[officer_remarked_by_id])

    @classmethod
    def clean_old_movements(cls, days=90):
        """
        Enforce 3-Month Data Retention Policy:
        Purges daily CLI movement records older than `days` (default 90).
        Strictly touches ONLY `cli_movements` table.
        """
        cutoff = date.today() - timedelta(days=days)
        deleted = cls.query.filter(cls.activity_date < cutoff).delete()
        db.session.commit()
        return deleted

    @property
    def is_within_retention(self):
        cutoff = date.today() - timedelta(days=90)
        return self.activity_date >= cutoff


# ---------------------------------------------------------------------------
# PHASE 6: CENTRALIZED DIRECTORIES (GOOGLE SHEETS & UNUSUAL INCIDENT TRACKER)
# ---------------------------------------------------------------------------

class GoogleSheetLink(db.Model):
    __tablename__ = 'google_sheet_links'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    sheet_url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(100), nullable=False) # 'CLI_PERFORMANCE', 'CREW_MONITORING', 'TRAINING', 'PME', 'SAFETY_MONITORING', 'OPERATIONAL'
    description = db.Column(db.Text, nullable=True)
    allowed_roles = db.Column(db.String(255), default='admin,officer,control,supervisor,crew') # comma-separated
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=True)
    traction_type = db.Column(db.String(20), default='BOTH') # 'ELECTRIC', 'DIESEL', 'BOTH'
    is_embedded = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lobby = db.relationship('Lobby', foreign_keys=[lobby_id])
    creator = db.relationship('User', foreign_keys=[created_by_id])

    def is_accessible_by(self, user):
        """Check if a User object or role string has permission to view this sheet."""
        if not user or not self.is_active:
            return False
        role = user.role if hasattr(user, 'role') else str(user)
        if role == 'admin':
            return True
        allowed = [r.strip().lower() for r in (self.allowed_roles or '').split(',') if r.strip()]
        if not allowed or 'all' in allowed or role.lower() in allowed:
            # Check lobby restriction if present
            if self.lobby_id and hasattr(user, 'lobby_id') and user.lobby_id:
                if role.lower() in ('supervisor', 'crew') and user.lobby_id != self.lobby_id:
                    return False
            return True
        return False

    def get_embed_url(self):
        """Returns clean embed/preview URL for Google Sheets."""
        url = self.sheet_url or ''
        if '/edit' in url:
            return url.split('/edit')[0] + '/preview?rm=minimal'
        elif '/view' in url:
            return url.split('/view')[0] + '/preview?rm=minimal'
        elif not url.endswith('/preview') and 'docs.google.com' in url:
            return url + '/preview?rm=minimal'
        return url


class UnusualIncident(db.Model):
    __tablename__ = 'unusual_incidents'

    id = db.Column(db.Integer, primary_key=True)
    incident_number = db.Column(db.String(100), unique=True, index=True) # e.g. INC/HWH/2026/001
    incident_date = db.Column(db.Date, nullable=False, index=True)
    incident_time = db.Column(db.String(10), nullable=True) # e.g. "14:25"
    section = db.Column(db.String(100), nullable=False) # e.g. "HWH-BWN"
    station_location = db.Column(db.String(100), nullable=True) # e.g. "BWN Yard, Km 95/4"
    train_no = db.Column(db.String(50), nullable=True)
    loco_no = db.Column(db.String(50), nullable=True)
    traction_type = db.Column(db.String(20), default='BOTH') # 'ELECTRIC', 'DIESEL', 'BOTH'
    incident_category = db.Column(db.String(100), nullable=False, index=True) # SPAD, LOCO_FAILURE, OHE_BREAKDOWN, SIGNAL_FAILURE, DERAILMENT, FLAT_TYRE, CATTLE_RUN_OVER, ACP_UNUSUAL, UNUSUAL_SOUND, MISC
    crew_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    crew_name_manual = db.Column(db.String(120), nullable=True)
    alp_name_manual = db.Column(db.String(120), nullable=True)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobbies.id'), nullable=True, index=True)
    cli_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    brief_description = db.Column(db.Text, nullable=False)
    primary_cause = db.Column(db.Text, nullable=True)
    immediate_action = db.Column(db.Text, nullable=True)
    rectification_time = db.Column(db.String(100), nullable=True)
    delay_minutes = db.Column(db.Integer, default=0)
    status = db.Column(db.String(50), default='REPORTED', index=True) # REPORTED, UNDER_INVESTIGATION, ACTION_COMPLETED, CLOSED
    attachment_path = db.Column(db.String(255), nullable=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reported_by_role = db.Column(db.String(50), nullable=True) # 'TLC', 'PCNL', 'CLI', 'OFFICER', 'ADMIN'
    officer_remarks = db.Column(db.Text, nullable=True)
    officer_remarked_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    officer_remarked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    crew = db.relationship('User', foreign_keys=[crew_id])
    cli = db.relationship('User', foreign_keys=[cli_id])
    lobby = db.relationship('Lobby', foreign_keys=[lobby_id])
    reporter = db.relationship('User', foreign_keys=[reported_by_id])
    officer_reviewer = db.relationship('User', foreign_keys=[officer_remarked_by_id])

    @classmethod
    def generate_incident_number(cls):
        """Generates consecutive incident number e.g. INC/HWH/2026/001."""
        year = date.today().year
        prefix = f"INC/HWH/{year}/"
        last_rec = cls.query.filter(cls.incident_number.like(f"{prefix}%")).order_by(cls.id.desc()).first()
        if last_rec and last_rec.incident_number:
            try:
                seq = int(last_rec.incident_number.split('/')[-1]) + 1
            except ValueError:
                seq = cls.query.count() + 1
        else:
            seq = cls.query.count() + 1
        return f"{prefix}{seq:03d}"

    @property
    def status_badge(self):
        mapping = {
            'REPORTED': ('warning text-dark', 'fa-triangle-exclamation', 'Reported'),
            'UNDER_INVESTIGATION': ('info text-dark', 'fa-magnifying-glass', 'Under Investigation'),
            'ACTION_COMPLETED': ('primary', 'fa-wrench', 'Action Completed'),
            'CLOSED': ('success', 'fa-circle-check', 'Closed')
        }
        return mapping.get(self.status, ('secondary', 'fa-circle-info', self.status))

    @property
    def category_label(self):
        labels = {
            'SPAD': 'Signal Passing At Danger (SPAD)',
            'LOCO_FAILURE': 'Locomotive / Equipment Tripping',
            'OHE_BREAKDOWN': 'OHE Power Supply Disruption',
            'SIGNAL_FAILURE': 'Signaling & Interlocking Failure',
            'DERAILMENT': 'Derailment / Track Obstruction',
            'FLAT_TYRE': 'Hot Axle / Flat Tyre / Brake Binding',
            'CATTLE_RUN_OVER': 'Cattle Run Over / Trespass',
            'ACP_UNUSUAL': 'Alarm Chain Pulling (ACP)',
            'UNUSUAL_SOUND': 'Unusual Sound / Jerk by Crew',
            'MISC': 'Miscellaneous Operational Unusual'
        }
        return labels.get(self.incident_category, self.incident_category)


