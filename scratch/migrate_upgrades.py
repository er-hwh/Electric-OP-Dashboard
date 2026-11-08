import os
import sys
import sqlite3

# Set paths
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages")
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard")

sqlite_path = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\supporting data\electric_op.db"

tables_sql = [
    """
    CREATE TABLE IF NOT EXISTS carousel_slides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(200) NOT NULL,
        subtitle VARCHAR(300),
        image_path VARCHAR(300) NOT NULL,
        button_text VARCHAR(100),
        button_url VARCHAR(300),
        display_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_by_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(created_by_id) REFERENCES users(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS safety_bulletins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bulletin_no VARCHAR(100),
        title VARCHAR(250) NOT NULL,
        bulletin_date DATE,
        category VARCHAR(100) DEFAULT 'Safety Bulletin',
        description TEXT,
        attachment_path VARCHAR(300),
        is_active BOOLEAN DEFAULT 1,
        created_by_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(created_by_id) REFERENCES users(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS rule_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(250) NOT NULL,
        category VARCHAR(100) NOT NULL,
        rule_reference VARCHAR(100),
        description TEXT,
        pdf_path VARCHAR(300) NOT NULL,
        display_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_by_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(created_by_id) REFERENCES users(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS learning_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(250) NOT NULL,
        traction_type VARCHAR(50) DEFAULT 'COMMON',
        category VARCHAR(100) DEFAULT 'Loco Study Material',
        description TEXT,
        content TEXT,
        attachment_path VARCHAR(300),
        external_url VARCHAR(300),
        display_order INTEGER DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
        created_by_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(created_by_id) REFERENCES users(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS page_contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_key VARCHAR(100) UNIQUE NOT NULL,
        title VARCHAR(200) NOT NULL,
        content_value TEXT NOT NULL,
        updated_by_id INTEGER,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(updated_by_id) REFERENCES users(id)
    );
    """
]

def migrate_sqlite():
    print(f"Connecting to SQLite: {sqlite_path}")
    conn = sqlite3.connect(sqlite_path)
    cur = conn.cursor()
    for sql in tables_sql:
        cur.execute(sql)
    conn.commit()
    print("SQLite tables verified / created.")

    # Check initial default page contents
    default_pages = [
        ('home_mission', 'Department Mission', 'To provide safe, reliable, efficient and punctual electric and diesel locomotive operations across the Howrah Division, adhering to the highest standards of safety, operating discipline, and crew welfare.'),
        ('home_vision', 'Department Vision', 'Zero Accident, Zero SPAD, 100% electrified operations, technological modernisation of crew management and continuous skill upgradation of running staff.'),
        ('safety_slogan', 'Safety Slogan', 'Safety First, Service Always - Alert Crew, Safe Rail.'),
        ('emergency_contacts', 'Emergency Contacts', 'TLC (Traction Loco Control): 22328, 033-2641-3652 | PCNL (Power Control): 22666, 22667 | Sr. DEE(OP) Control Room: 22440'),
        ('elearning_overview', 'E-Learning Portal Overview', 'Official Eastern Railway Howrah Division E-Learning Portal providing interactive modules, question banks, loco diagrams and operating rules.')
    ]
    for key, title, val in default_pages:
        cur.execute("SELECT id FROM page_contents WHERE content_key = ?", (key,))
        if not cur.fetchone():
            cur.execute("INSERT INTO page_contents (content_key, title, content_value) VALUES (?, ?, ?)", (key, title, val))
    conn.commit()
    conn.close()
    print("Default page contents seeded in SQLite.")

def migrate_mysql():
    try:
        import pymysql
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="",
            port=3306,
            database="electric_op_hwh",
            connect_timeout=2
        )
        cur = conn.cursor()
        print("Connected to MySQL electric_op_hwh.")
        mysql_tables = [
            """
            CREATE TABLE IF NOT EXISTS carousel_slides (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                subtitle VARCHAR(300),
                image_path VARCHAR(300) NOT NULL,
                button_text VARCHAR(100),
                button_url VARCHAR(300),
                display_order INT DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_by_id INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX (is_active),
                INDEX (display_order)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS safety_bulletins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bulletin_no VARCHAR(100),
                title VARCHAR(250) NOT NULL,
                bulletin_date DATE,
                category VARCHAR(100) DEFAULT 'Safety Bulletin',
                description TEXT,
                attachment_path VARCHAR(300),
                is_active BOOLEAN DEFAULT 1,
                created_by_id INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX (is_active),
                INDEX (bulletin_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS rule_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(250) NOT NULL,
                category VARCHAR(100) NOT NULL,
                rule_reference VARCHAR(100),
                description TEXT,
                pdf_path VARCHAR(300) NOT NULL,
                display_order INT DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_by_id INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX (category),
                INDEX (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS learning_materials (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(250) NOT NULL,
                traction_type VARCHAR(50) DEFAULT 'COMMON',
                category VARCHAR(100) DEFAULT 'Loco Study Material',
                description TEXT,
                content TEXT,
                attachment_path VARCHAR(300),
                external_url VARCHAR(300),
                display_order INT DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_by_id INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX (traction_type),
                INDEX (is_active)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            """
            CREATE TABLE IF NOT EXISTS page_contents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                content_key VARCHAR(100) UNIQUE NOT NULL,
                title VARCHAR(200) NOT NULL,
                content_value TEXT NOT NULL,
                updated_by_id INT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        ]
        for sql in mysql_tables:
            cur.execute(sql)
        conn.commit()

        # Seed default page contents
        default_pages = [
            ('home_mission', 'Department Mission', 'To provide safe, reliable, efficient and punctual electric and diesel locomotive operations across the Howrah Division, adhering to the highest standards of safety, operating discipline, and crew welfare.'),
            ('home_vision', 'Department Vision', 'Zero Accident, Zero SPAD, 100% electrified operations, technological modernisation of crew management and continuous skill upgradation of running staff.'),
            ('safety_slogan', 'Safety Slogan', 'Safety First, Service Always - Alert Crew, Safe Rail.'),
            ('emergency_contacts', 'Emergency Contacts', 'TLC (Traction Loco Control): 22328, 033-2641-3652 | PCNL (Power Control): 22666, 22667 | Sr. DEE(OP) Control Room: 22440'),
            ('elearning_overview', 'E-Learning Portal Overview', 'Official Eastern Railway Howrah Division E-Learning Portal providing interactive modules, question banks, loco diagrams and operating rules.')
        ]
        for key, title, val in default_pages:
            cur.execute("SELECT id FROM page_contents WHERE content_key = %s", (key,))
            if not cur.fetchone():
                cur.execute("INSERT INTO page_contents (content_key, title, content_value) VALUES (%s, %s, %s)", (key, title, val))
        conn.commit()
        conn.close()
        print("MySQL tables verified and seeded.")
    except Exception as e:
        print(f"MySQL migration notice: {e}")

if __name__ == '__main__':
    migrate_sqlite()
    migrate_mysql()
    print("Migration finished successfully.")
