import os
import sqlite3
import logging
from contextlib import contextmanager

logger = logging.getLogger("control_db")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "supporting data", "control_operational.db")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DB = os.environ.get("MYSQL_DB", "electric_op_hwh")

_tables_initialized = False

class DictCursorWrapper:
    """Wrapper to make sqlite3 row factory behave like a dictionary cursor."""
    def __init__(self, cursor):
        self.cursor = cursor
        self.description = cursor.description

    def execute(self, sql, params=None):
        # Convert %s to ? if sqlite
        sql = sql.replace("%s", "?")
        if params is None:
            return self.cursor.execute(sql)
        return self.cursor.execute(sql, params)

    def executemany(self, sql, params):
        sql = sql.replace("%s", "?")
        return self.cursor.executemany(sql, params)

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        if hasattr(row, 'keys'):
            return dict(row)
        if self.cursor.description:
            cols = [col[0] for col in self.cursor.description]
            return dict(zip(cols, row))
        return row

    def fetchall(self):
        rows = self.cursor.fetchall()
        if not rows:
            return []
        if hasattr(rows[0], 'keys'):
            return [dict(r) for r in rows]
        cols = [col[0] for col in self.cursor.description]
        return [dict(zip(cols, r)) for r in rows]

    def close(self):
        self.cursor.close()

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount


class ResilientConnection:
    def __init__(self, conn, is_sqlite=False):
        self.conn = conn
        self.is_sqlite = is_sqlite

    def cursor(self, dictionary=True):
        if self.is_sqlite:
            self.conn.row_factory = sqlite3.Row
            raw_cur = self.conn.cursor()
            return DictCursorWrapper(raw_cur)
        else:
            try:
                # mysql.connector or pymysql
                if hasattr(self.conn, 'cursor'):
                    import pymysql.cursors
                    return self.conn.cursor(pymysql.cursors.DictCursor if dictionary else None)
            except Exception:
                pass
            return self.conn.cursor()

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def get_connection():
    """Returns a resilient database connection (MySQL if available, otherwise SQLite)."""
    # 1. Try MySQL
    try:
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
            charset='utf8mb4',
            connect_timeout=2
        )
        _ensure_tables(ResilientConnection(conn, is_sqlite=False))
        return ResilientConnection(conn, is_sqlite=False)
    except Exception as e:
        logger.info(f"MySQL not available ({e}). Using SQLite fallback: {SQLITE_DB_PATH}")

    # 2. Try MySQL with 'hwh_dashboard' db
    try:
        import pymysql
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database="hwh_dashboard",
            charset='utf8mb4',
            connect_timeout=2
        )
        _ensure_tables(ResilientConnection(conn, is_sqlite=False))
        return ResilientConnection(conn, is_sqlite=False)
    except Exception:
        pass

    # 3. Fallback to SQLite
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH, timeout=20.0)
    resilient = ResilientConnection(sqlite_conn, is_sqlite=True)
    _ensure_tables(resilient)
    return resilient


def _ensure_tables(conn):
    global _tables_initialized
    if _tables_initialized:
        return

    cur = conn.cursor(dictionary=False)
    try:
        # Crew master
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crew_master (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crew_id VARCHAR(50) UNIQUE,
                crew_name VARCHAR(150),
                designation VARCHAR(50),
                crew_hq VARCHAR(50),
                mobile VARCHAR(30),
                cli_name VARCHAR(150),
                cli_id VARCHAR(50),
                status VARCHAR(50) DEFAULT 'ACTIVE',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS crew_master (
                id INT AUTO_INCREMENT PRIMARY KEY,
                crew_id VARCHAR(50) UNIQUE,
                crew_name VARCHAR(150),
                designation VARCHAR(50),
                crew_hq VARCHAR(50),
                mobile VARCHAR(30),
                cli_name VARCHAR(150),
                cli_id VARCHAR(50),
                status VARCHAR(50) DEFAULT 'ACTIVE',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Upload history
        cur.execute("""
            CREATE TABLE IF NOT EXISTS upload_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                username VARCHAR(100),
                file_name VARCHAR(255),
                total_rows INT DEFAULT 0,
                inserted_count INT DEFAULT 0,
                updated_count INT DEFAULT 0,
                failed_count INT DEFAULT 0
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS upload_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                username VARCHAR(100),
                file_name VARCHAR(255),
                total_rows INT DEFAULT 0,
                inserted_count INT DEFAULT 0,
                updated_count INT DEFAULT 0,
                failed_count INT DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # CLI users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cli_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cli_id VARCHAR(50) UNIQUE,
                cli_name VARCHAR(150),
                lobby VARCHAR(50),
                mobile VARCHAR(30),
                role VARCHAR(30) DEFAULT 'cli'
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS cli_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                cli_id VARCHAR(50) UNIQUE,
                cli_name VARCHAR(150),
                lobby VARCHAR(50),
                mobile VARCHAR(30),
                role VARCHAR(30) DEFAULT 'cli'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Availability status options
        cur.execute("""
            CREATE TABLE IF NOT EXISTS availability_status_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status_name VARCHAR(50) UNIQUE,
                is_active INT DEFAULT 1
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS availability_status_options (
                id INT AUTO_INCREMENT PRIMARY KEY,
                status_name VARCHAR(50) UNIQUE,
                is_active TINYINT(1) DEFAULT 1
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Crew availability
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crew_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                s_no VARCHAR(50),
                crew_id VARCHAR(50),
                name VARCHAR(150),
                origdesig VARCHAR(50),
                sign_off VARCHAR(100),
                available VARCHAR(80),
                available_text VARCHAR(80),
                rest_hours VARCHAR(50),
                mobile_no_reg VARCHAR(30),
                status VARCHAR(50),
                remarks TEXT,
                train_no VARCHAR(80),
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS crew_availability (
                id INT AUTO_INCREMENT PRIMARY KEY,
                s_no VARCHAR(50),
                crew_id VARCHAR(50),
                name VARCHAR(150),
                origdesig VARCHAR(50),
                sign_off VARCHAR(100),
                available VARCHAR(80),
                available_text VARCHAR(80),
                rest_hours VARCHAR(50),
                mobile_no_reg VARCHAR(30),
                status VARCHAR(50),
                remarks TEXT,
                train_no VARCHAR(80),
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Duty hours files
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duty_hours_files (
                id VARCHAR(50) PRIMARY KEY,
                filename VARCHAR(255),
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                headers_json TEXT,
                header_row INT,
                sl_col INT,
                sign_off_col INT
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS duty_hours_files (
                id VARCHAR(50) PRIMARY KEY,
                filename VARCHAR(255),
                upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                headers_json LONGTEXT,
                header_row INT,
                sl_col INT,
                sign_off_col INT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Duty hours rows
        cur.execute("""
            CREATE TABLE IF NOT EXISTS duty_hours_rows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id VARCHAR(50),
                row_index INT,
                sl_no VARCHAR(50),
                sign_off_date VARCHAR(20),
                row_data_json TEXT
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS duty_hours_rows (
                id INT AUTO_INCREMENT PRIMARY KEY,
                file_id VARCHAR(50),
                row_index INT,
                sl_no VARCHAR(50),
                sign_off_date VARCHAR(20),
                row_data_json LONGTEXT,
                INDEX idx_file_date (file_id, sign_off_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Gradient register
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gradient_register (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                div_rly VARCHAR(50),
                section VARCHAR(100),
                line VARCHAR(50),
                km_from INT,
                met_from INT,
                km_to INT,
                met_to INT,
                gauge VARCHAR(50),
                length_m INT,
                direction VARCHAR(50),
                grade VARCHAR(50)
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS gradient_register (
                id INT AUTO_INCREMENT PRIMARY KEY,
                div_rly VARCHAR(50),
                section VARCHAR(100),
                line VARCHAR(50),
                km_from INT,
                met_from INT,
                km_to INT,
                met_to INT,
                gauge VARCHAR(50),
                length_m INT,
                direction VARCHAR(50),
                grade VARCHAR(50)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Long hours tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_daily_duty_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_date DATE,
                record_year INT,
                record_month VARCHAR(3),
                record_day INT,
                total_duty_count INT DEFAULT 0,
                source_file_name VARCHAR(255),
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS tbl_daily_duty_summary (
                id INT AUTO_INCREMENT PRIMARY KEY,
                record_date DATE NOT NULL,
                record_year INT NOT NULL,
                record_month VARCHAR(3) NOT NULL,
                record_day INT NOT NULL,
                total_duty_count INT NOT NULL DEFAULT 0,
                source_file_name VARCHAR(255),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_posted_routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_name VARCHAR(500) UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS tbl_posted_routes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                route_name VARCHAR(500) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Long hours master tables
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_long_hours_master (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_batch_id VARCHAR(50),
                source_file_name VARCHAR(255),
                record_hash VARCHAR(64) UNIQUE,
                sign_on_date DATE,
                sign_on_time VARCHAR(20),
                sign_off_date DATE,
                sign_off_time VARCHAR(20),
                lp_name VARCHAR(255),
                alp_name VARCHAR(255),
                crew_id VARCHAR(50),
                train_no VARCHAR(50),
                loco_no VARCHAR(50),
                long_hours_section VARCHAR(100),
                on_stn VARCHAR(50),
                cto_stn VARCHAR(50),
                dep_stn VARCHAR(50),
                arr_stn VARCHAR(50),
                cmo_stn VARCHAR(50),
                off_stn VARCHAR(50),
                hwh_div_seconds INT DEFAULT 0,
                oth_div_seconds INT DEFAULT 0,
                total_seconds INT DEFAULT 0,
                pdd_seconds INT DEFAULT 0,
                pad_seconds INT DEFAULT 0,
                wheel_movement_seconds INT DEFAULT 0,
                sign_on_to_dep_seconds INT DEFAULT 0,
                wheel_stop_to_off_seconds INT DEFAULT 0,
                detn_ic_point VARCHAR(255),
                remarks TEXT,
                scenario_type INT,
                row_data_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS tbl_long_hours_master (
                id INT AUTO_INCREMENT PRIMARY KEY,
                upload_batch_id VARCHAR(50) NOT NULL,
                source_file_name VARCHAR(255) NOT NULL,
                record_hash VARCHAR(64) UNIQUE NOT NULL,
                sign_on_date DATE,
                sign_on_time VARCHAR(20),
                sign_off_date DATE,
                sign_off_time VARCHAR(20),
                lp_name VARCHAR(255),
                alp_name VARCHAR(255),
                crew_id VARCHAR(50),
                train_no VARCHAR(50),
                loco_no VARCHAR(50),
                long_hours_section VARCHAR(100),
                on_stn VARCHAR(50),
                cto_stn VARCHAR(50),
                dep_stn VARCHAR(50),
                arr_stn VARCHAR(50),
                cmo_stn VARCHAR(50),
                off_stn VARCHAR(50),
                hwh_div_seconds INT DEFAULT 0,
                oth_div_seconds INT DEFAULT 0,
                total_seconds INT DEFAULT 0,
                pdd_seconds INT DEFAULT 0,
                pad_seconds INT DEFAULT 0,
                wheel_movement_seconds INT DEFAULT 0,
                sign_on_to_dep_seconds INT DEFAULT 0,
                wheel_stop_to_off_seconds INT DEFAULT 0,
                detn_ic_point VARCHAR(255),
                remarks TEXT,
                scenario_type INT,
                row_data_json LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_sign_off_date (sign_off_date),
                INDEX idx_long_hours_section (long_hours_section),
                INDEX idx_scenario_type (scenario_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_long_hours_sections (
                section_name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS tbl_long_hours_sections (
                section_name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tbl_long_hours_upload_log (
                upload_batch_id VARCHAR(50) PRIMARY KEY,
                original_file_name VARCHAR(255) NOT NULL,
                uploaded_by VARCHAR(100) NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_rows INT DEFAULT 0,
                inserted_rows INT DEFAULT 0,
                updated_rows INT DEFAULT 0,
                failed_rows INT DEFAULT 0,
                remarks TEXT
            );
        """ if conn.is_sqlite else """
            CREATE TABLE IF NOT EXISTS tbl_long_hours_upload_log (
                upload_batch_id VARCHAR(50) PRIMARY KEY,
                original_file_name VARCHAR(255) NOT NULL,
                uploaded_by VARCHAR(100) NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_rows INT DEFAULT 0,
                inserted_rows INT DEFAULT 0,
                updated_rows INT DEFAULT 0,
                failed_rows INT DEFAULT 0,
                remarks TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # Prepopulate default status options if empty
        cur.execute("SELECT COUNT(*) as cnt FROM availability_status_options")
        row = cur.fetchone()
        cnt = row['cnt'] if isinstance(row, dict) else row[0]
        if cnt == 0:
            defaults = [
                "Leave", "Training", "Night Off", "Enquiry", "Book Up",
                "PME", "Absent", "LR", "RMC Sick", "PMC Sick",
                "Suspension", "Transfer", "CCNL", "Stationary Duty",
                "T/YD", "ET Duty", "OUT", "Other"
            ]
            for status in defaults:
                try:
                    cur.execute(
                        "INSERT OR IGNORE INTO availability_status_options (status_name, is_active) VALUES (?, 1)"
                        if conn.is_sqlite else
                        "INSERT IGNORE INTO availability_status_options (status_name, is_active) VALUES (%s, 1)",
                        (status,)
                    )
                except Exception:
                    pass

        conn.commit()
        _tables_initialized = True
    except Exception as err:
        logger.error(f"Error ensuring control tables: {err}")
    finally:
        cur.close()
