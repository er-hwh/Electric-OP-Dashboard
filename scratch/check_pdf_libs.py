import sys
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages")

for lib in ['pypdf', 'PyPDF2', 'pdfplumber', 'fitz', 'openpyxl', 'flask', 'sqlite3']:
    try:
        __import__(lib)
        print(f"[OK] {lib}")
    except ImportError as e:
        print(f"[FAIL] {lib}: {e}")
