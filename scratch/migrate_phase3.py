from app import create_app
from database import db
from models import CLIMovement, CrewCounsellingRecord
import sqlite3

app = create_app()
with app.app_context():
    db.create_all()
    print("db.create_all() executed.")
    
    conn = sqlite3.connect('supporting data/electric_op.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(crew_counselling_records)")
    cols = [row[1] for row in cursor.fetchall()]
    print("Existing crew_counselling_records cols count:", len(cols))
    
    if 'officer_remarks' not in cols:
        cursor.execute("ALTER TABLE crew_counselling_records ADD COLUMN officer_remarks TEXT")
        print("Added officer_remarks to crew_counselling_records")
    if 'officer_remarked_by_id' not in cols:
        cursor.execute("ALTER TABLE crew_counselling_records ADD COLUMN officer_remarked_by_id INTEGER")
        print("Added officer_remarked_by_id to crew_counselling_records")
    if 'officer_remarked_at' not in cols:
        cursor.execute("ALTER TABLE crew_counselling_records ADD COLUMN officer_remarked_at DATETIME")
        print("Added officer_remarked_at to crew_counselling_records")
        
    cursor.execute("PRAGMA table_info(cli_movements)")
    cli_cols = [row[1] for row in cursor.fetchall()]
    print("cli_movements columns:", cli_cols)
    
    conn.commit()
    conn.close()
    print("Migration successful.")
