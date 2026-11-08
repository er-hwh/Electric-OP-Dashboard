import os
import sys
import sqlite3

REPO_DIR = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard"
VENV_PKGS = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages"
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
if VENV_PKGS not in sys.path:
    sys.path.insert(1, VENV_PKGS)

print("=== STARTING PHASE 5 DATABASE MIGRATION ===")

# 1. Migrate SQLite database
sqlite_path = os.path.join(REPO_DIR, 'supporting data', 'electric_op.db')
if os.path.exists(sqlite_path):
    print(f"Migrating SQLite: {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()

    def add_sqlite_col(tbl, col, dtype):
        try:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {dtype}")
            print(f"  [SQLite] Added {tbl}.{col}")
        except Exception as e:
            print(f"  [SQLite] Skipped {tbl}.{col}: {e}")

    # Notice columns
    add_sqlite_col("notices", "traction_type", "VARCHAR(20) DEFAULT 'ALL'")
    add_sqlite_col("notices", "is_mandatory", "BOOLEAN DEFAULT 1")
    add_sqlite_col("notices", "requires_signature", "BOOLEAN DEFAULT 0")
    add_sqlite_col("notices", "approved_by_id", "INTEGER REFERENCES users(id)")
    add_sqlite_col("notices", "approval_date", "DATETIME")
    add_sqlite_col("notices", "officer_remarks", "TEXT")

    # NoticeAcknowledgement columns
    add_sqlite_col("notice_acknowledgements", "ip_address", "VARCHAR(50)")
    add_sqlite_col("notice_acknowledgements", "device_info", "VARCHAR(255)")
    add_sqlite_col("notice_acknowledgements", "is_confirmed", "BOOLEAN DEFAULT 1")

    # CounsellingTopic columns
    add_sqlite_col("counselling_topics", "traction_type", "VARCHAR(20) DEFAULT 'ALL'")
    add_sqlite_col("counselling_topics", "drive_name", "VARCHAR(100)")
    add_sqlite_col("counselling_topics", "is_mandatory", "BOOLEAN DEFAULT 1")

    # Create crew_counselling_logs table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS crew_counselling_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cli_id INTEGER NOT NULL REFERENCES users(id),
        crew_id INTEGER NOT NULL REFERENCES users(id),
        counselling_date DATE NOT NULL,
        counselling_type VARCHAR(50) DEFAULT 'MONTHLY_SAFETY',
        topic VARCHAR(255) NOT NULL,
        topic_id INTEGER REFERENCES counselling_topics(id),
        location VARCHAR(100) DEFAULT 'Lobby',
        counselling_mode VARCHAR(50) DEFAULT 'One-to-One',
        crew_response TEXT,
        cli_remarks TEXT,
        crew_acknowledged BOOLEAN DEFAULT 0,
        acknowledged_at DATETIME,
        acknowledgement_note VARCHAR(255),
        officer_remarks TEXT,
        officer_remarked_by_id INTEGER REFERENCES users(id),
        officer_remarked_at DATETIME,
        created_at DATETIME
    )
    """)
    print("  [SQLite] Created crew_counselling_logs table if not exists")

    conn.commit()
    conn.close()

# 2. Migrate MySQL database if available
try:
    import pymysql
    my_conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        port=3306,
        database='electric_op_hwh',
        connect_timeout=2
    )
    print("Migrating MySQL database: electric_op_hwh")
    m_cur = my_conn.cursor()

    def add_mysql_col(tbl, col, dtype):
        try:
            m_cur.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {dtype}")
            print(f"  [MySQL] Added {tbl}.{col}")
        except Exception as e:
            print(f"  [MySQL] Skipped {tbl}.{col}: {e}")

    add_mysql_col("notices", "traction_type", "VARCHAR(20) DEFAULT 'ALL'")
    add_mysql_col("notices", "is_mandatory", "BOOLEAN DEFAULT 1")
    add_mysql_col("notices", "requires_signature", "BOOLEAN DEFAULT 0")
    add_mysql_col("notices", "approved_by_id", "INT NULL")
    add_mysql_col("notices", "approval_date", "DATETIME NULL")
    add_mysql_col("notices", "officer_remarks", "TEXT NULL")

    add_mysql_col("notice_acknowledgements", "ip_address", "VARCHAR(50) NULL")
    add_mysql_col("notice_acknowledgements", "device_info", "VARCHAR(255) NULL")
    add_mysql_col("notice_acknowledgements", "is_confirmed", "BOOLEAN DEFAULT 1")

    add_mysql_col("counselling_topics", "traction_type", "VARCHAR(20) DEFAULT 'ALL'")
    add_mysql_col("counselling_topics", "drive_name", "VARCHAR(100) NULL")
    add_mysql_col("counselling_topics", "is_mandatory", "BOOLEAN DEFAULT 1")

    m_cur.execute("""
    CREATE TABLE IF NOT EXISTS crew_counselling_logs (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cli_id INT NOT NULL,
        crew_id INT NOT NULL,
        counselling_date DATE NOT NULL,
        counselling_type VARCHAR(50) DEFAULT 'MONTHLY_SAFETY',
        topic VARCHAR(255) NOT NULL,
        topic_id INT NULL,
        location VARCHAR(100) DEFAULT 'Lobby',
        counselling_mode VARCHAR(50) DEFAULT 'One-to-One',
        crew_response TEXT NULL,
        cli_remarks TEXT NULL,
        crew_acknowledged BOOLEAN DEFAULT 0,
        acknowledged_at DATETIME NULL,
        acknowledgement_note VARCHAR(255) NULL,
        officer_remarks TEXT NULL,
        officer_remarked_by_id INT NULL,
        officer_remarked_at DATETIME NULL,
        created_at DATETIME NULL,
        INDEX idx_cli (cli_id),
        INDEX idx_crew (crew_id),
        INDEX idx_cdate (counselling_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("  [MySQL] Created crew_counselling_logs table if not exists")

    my_conn.commit()
    my_conn.close()
except Exception as e:
    print(f"MySQL migration skipped or not running: {e}")

print("=== PHASE 5 DATABASE MIGRATION COMPLETE ===")
