import os
import sys
from datetime import datetime, date, timedelta
from app import create_app
from database import db
from sqlalchemy import text
from models import MedicalRecord, TrainingRecord, User

app = create_app()

with app.app_context():
    print("Running Phase 4 Database Migrations...")
    db.create_all()
    print("db.create_all() executed.")

    # 1. Add columns to users table
    user_cols = [
        ('date_of_birth', 'DATE'),
        ('date_of_appointment', 'DATE'),
        ('pme_last_done_date', 'DATE'),
        ('pme_due_date', 'DATE'),
        ('pme_fitness_status', 'VARCHAR(50) DEFAULT "Fit A-One"')
    ]
    for col, col_type in user_cols:
        try:
            db.session.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
            db.session.commit()
            print(f"Added column {col} to users")
        except Exception as e:
            db.session.rollback()
            # print(f"Column {col} already exists or error: {e}")

    # 2. Add columns to training_records table
    tr_cols = [
        ('training_category', 'VARCHAR(50) DEFAULT "REFRESHER"'),
        ('validity_months', 'INTEGER DEFAULT 36')
    ]
    for col, col_type in tr_cols:
        try:
            db.session.execute(text(f"ALTER TABLE training_records ADD COLUMN {col} {col_type}"))
            db.session.commit()
            print(f"Added column {col} to training_records")
        except Exception as e:
            db.session.rollback()

    print("Phase 4 schema migration complete.")
