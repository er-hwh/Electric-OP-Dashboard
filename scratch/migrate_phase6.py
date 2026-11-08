import os
import sys
import sqlite3

sqlite_path = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\supporting data\electric_op.db"

print("--- 1. Migrating SQLite ---")
con = sqlite3.connect(sqlite_path)
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS google_sheet_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    sheet_url VARCHAR(500) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    allowed_roles VARCHAR(255) DEFAULT 'admin,officer,control,supervisor,crew',
    lobby_id INTEGER,
    traction_type VARCHAR(20) DEFAULT 'BOTH',
    is_embedded BOOLEAN DEFAULT 0,
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_by_id INTEGER,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (lobby_id) REFERENCES lobbies (id),
    FOREIGN KEY (created_by_id) REFERENCES users (id)
);
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS unusual_incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_number VARCHAR(100) UNIQUE,
    incident_date DATE NOT NULL,
    incident_time VARCHAR(10),
    section VARCHAR(100) NOT NULL,
    station_location VARCHAR(100),
    train_no VARCHAR(50),
    loco_no VARCHAR(50),
    traction_type VARCHAR(20) DEFAULT 'BOTH',
    incident_category VARCHAR(100) NOT NULL,
    crew_id INTEGER,
    crew_name_manual VARCHAR(120),
    alp_name_manual VARCHAR(120),
    lobby_id INTEGER,
    cli_id INTEGER,
    brief_description TEXT NOT NULL,
    primary_cause TEXT,
    immediate_action TEXT,
    rectification_time VARCHAR(100),
    delay_minutes INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'REPORTED',
    attachment_path VARCHAR(255),
    reported_by_id INTEGER,
    reported_by_role VARCHAR(50),
    officer_remarks TEXT,
    officer_remarked_by_id INTEGER,
    officer_remarked_at DATETIME,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (crew_id) REFERENCES users (id),
    FOREIGN KEY (lobby_id) REFERENCES lobbies (id),
    FOREIGN KEY (cli_id) REFERENCES users (id),
    FOREIGN KEY (reported_by_id) REFERENCES users (id),
    FOREIGN KEY (officer_remarked_by_id) REFERENCES users (id)
);
""")

# Create Indexes
cur.execute("CREATE INDEX IF NOT EXISTS idx_sheets_cat ON google_sheet_links(category);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_sheets_active ON google_sheet_links(is_active);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_incidents_date ON unusual_incidents(incident_date);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_incidents_status ON unusual_incidents(status);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_incidents_cat ON unusual_incidents(incident_category);")
cur.execute("CREATE INDEX IF NOT EXISTS idx_incidents_lobby ON unusual_incidents(lobby_id);")

con.commit()
con.close()
print("SQLite migration completed.")

print("\n--- 2. Migrating MySQL ---")
try:
    import pymysql
    mycon = pymysql.connect(host='localhost', port=3306, user='root', password='', database='electric_op_hwh')
    mycur = mycon.cursor()

    mycur.execute("""
    CREATE TABLE IF NOT EXISTS google_sheet_links (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        sheet_url VARCHAR(500) NOT NULL,
        category VARCHAR(100) NOT NULL,
        description TEXT,
        allowed_roles VARCHAR(255) DEFAULT 'admin,officer,control,supervisor,crew',
        lobby_id INT NULL,
        traction_type VARCHAR(20) DEFAULT 'BOTH',
        is_embedded TINYINT(1) DEFAULT 0,
        display_order INT DEFAULT 0,
        is_active TINYINT(1) DEFAULT 1,
        created_by_id INT NULL,
        created_at DATETIME NULL,
        updated_at DATETIME NULL,
        INDEX idx_sheets_cat (category),
        INDEX idx_sheets_active (is_active)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    mycur.execute("""
    CREATE TABLE IF NOT EXISTS unusual_incidents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        incident_number VARCHAR(100) UNIQUE,
        incident_date DATE NOT NULL,
        incident_time VARCHAR(10) NULL,
        section VARCHAR(100) NOT NULL,
        station_location VARCHAR(100) NULL,
        train_no VARCHAR(50) NULL,
        loco_no VARCHAR(50) NULL,
        traction_type VARCHAR(20) DEFAULT 'BOTH',
        incident_category VARCHAR(100) NOT NULL,
        crew_id INT NULL,
        crew_name_manual VARCHAR(120) NULL,
        alp_name_manual VARCHAR(120) NULL,
        lobby_id INT NULL,
        cli_id INT NULL,
        brief_description TEXT NOT NULL,
        primary_cause TEXT NULL,
        immediate_action TEXT NULL,
        rectification_time VARCHAR(100) NULL,
        delay_minutes INT DEFAULT 0,
        status VARCHAR(50) DEFAULT 'REPORTED',
        attachment_path VARCHAR(255) NULL,
        reported_by_id INT NULL,
        reported_by_role VARCHAR(50) NULL,
        officer_remarks TEXT NULL,
        officer_remarked_by_id INT NULL,
        officer_remarked_at DATETIME NULL,
        created_at DATETIME NULL,
        updated_at DATETIME NULL,
        INDEX idx_incidents_date (incident_date),
        INDEX idx_incidents_status (status),
        INDEX idx_incidents_cat (incident_category),
        INDEX idx_incidents_lobby (lobby_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    mycon.commit()
    mycon.close()
    print("MySQL migration completed successfully.")
except Exception as e:
    print(f"MySQL note/warning: {e}")
