with open("blueprints/duty_hours.py", "r", encoding="utf-8") as f:
    text = f.read()

helpers = """
def _unpack_file_meta(meta):
    if isinstance(meta, dict):
        return meta.get("header_row"), meta.get("sl_col"), meta.get("sign_off_col"), meta.get("headers_json")
    return meta

def _unpack_db_row(row):
    if isinstance(row, dict):
        return row.get("row_index"), row.get("sl_no"), row.get("sign_off_date"), row.get("row_data_json")
    return row
"""

# Insert helpers right after excel_json_default
text = text.replace(
    'return str(value)\n\ndef init_db_tables():',
    'return str(value)\n' + helpers + '\ndef init_db_tables():'
)

# Replace all occurrences of file_meta unpacking
text = text.replace(
    'header_row, sl_col, sign_off_col, headers_json = file_meta',
    'header_row, sl_col, sign_off_col, headers_json = _unpack_file_meta(file_meta)'
)

# Replace all occurrences of db_rows unpacking
text = text.replace(
    'for row in db_rows:\n            r_idx, sl_no, sign_off_date, row_data_json = row',
    'for row in db_rows:\n            r_idx, sl_no, sign_off_date, row_data_json = _unpack_db_row(row)'
)

with open("blueprints/duty_hours.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Replacement complete!")
