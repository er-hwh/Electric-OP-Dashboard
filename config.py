import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'howrah_electric_op_secret_key_2026')
    # Default MySQL connection using PyMySQL
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'electric_op_hwh')
    
    _mysql_uri = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    _db_url = os.environ.get('DATABASE_URL')
    if not _db_url:
        try:
            import pymysql
            _test_conn = pymysql.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                port=int(MYSQL_PORT),
                connect_timeout=1
            )
            _test_conn.close()
            _db_url = _mysql_uri
        except Exception:
            _sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'supporting data', 'electric_op.db')
            os.makedirs(os.path.dirname(_sqlite_path), exist_ok=True)
            _db_url = f"sqlite:///{_sqlite_path}"

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32 MB max upload limit
