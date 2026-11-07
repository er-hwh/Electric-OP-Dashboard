import re

with open("blueprints/duty_hours.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Replace the first query in filter_duty_hours
old_block1 = """            # Query matching rows (HEADER, FOOTER, or within the date range)
            cursor.execute(
                \"\"\"
                SELECT row_index, sl_no, sign_off_date, row_data_json 
                FROM duty_hours_rows 
                WHERE file_id = %s 
                  AND (
                    (sign_off_date NOT IN ('HEADER', 'FOOTER') 
                     AND STR_TO_DATE(sign_off_date, '%d-%m-%Y') BETWEEN STR_TO_DATE(%s, '%d-%m-%Y') AND STR_TO_DATE(%s, '%d-%m-%Y'))
                    OR sign_off_date = 'HEADER' 
                    OR sign_off_date = 'FOOTER'
                  )
                ORDER BY row_index
                \"\"\",
                (file_id, from_date, to_date)
            )"""

new_block1 = """            # Query matching rows (HEADER, FOOTER, or within the date range)
            if getattr(conn, "is_sqlite", False):
                fd_iso = f"{from_date[6:10]}-{from_date[3:5]}-{from_date[0:2]}" if len(from_date) == 10 else from_date
                td_iso = f"{to_date[6:10]}-{to_date[3:5]}-{to_date[0:2]}" if len(to_date) == 10 else to_date
                cursor.execute(
                    \"\"\"
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND (
                        (sign_off_date NOT IN ('HEADER', 'FOOTER') 
                         AND (substr(sign_off_date, 7, 4) || '-' || substr(sign_off_date, 4, 2) || '-' || substr(sign_off_date, 1, 2)) BETWEEN %s AND %s)
                        OR sign_off_date = 'HEADER' 
                        OR sign_off_date = 'FOOTER'
                      )
                    ORDER BY row_index
                    \"\"\",
                    (file_id, fd_iso, td_iso)
                )
            else:
                cursor.execute(
                    \"\"\"
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND (
                        (sign_off_date NOT IN ('HEADER', 'FOOTER') 
                         AND STR_TO_DATE(sign_off_date, '%%d-%%m-%%Y') BETWEEN STR_TO_DATE(%s, '%%d-%%m-%%Y') AND STR_TO_DATE(%s, '%%d-%%m-%%Y'))
                        OR sign_off_date = 'HEADER' 
                        OR sign_off_date = 'FOOTER'
                      )
                    ORDER BY row_index
                    \"\"\",
                    (file_id, from_date, to_date)
                )"""

# Normalize line breaks for matching
text_normalized = text.replace("\r\n", "\n")
old_block1_normalized = old_block1.replace("\r\n", "\n")

if old_block1_normalized in text_normalized:
    text_normalized = text_normalized.replace(old_block1_normalized, new_block1)
    print("Block 1 replaced successfully!")
else:
    print("WARNING: Block 1 not found!")

# 2. Replace the second query in download_route_summary
old_block2 = """            # Query matching rows
            cursor.execute(
                \"\"\"
                SELECT row_index, sl_no, sign_off_date, row_data_json 
                FROM duty_hours_rows 
                WHERE file_id = %s 
                  AND sign_off_date NOT IN ('HEADER', 'FOOTER') 
                  AND STR_TO_DATE(sign_off_date, '%d-%m-%Y') BETWEEN STR_TO_DATE(%s, '%d-%m-%Y') AND STR_TO_DATE(%s, '%d-%m-%Y')
                ORDER BY row_index
                \"\"\",
                (file_id, from_date, to_date)
            )"""

new_block2 = """            # Query matching rows
            if getattr(conn, "is_sqlite", False):
                fd_iso = f"{from_date[6:10]}-{from_date[3:5]}-{from_date[0:2]}" if len(from_date) == 10 else from_date
                td_iso = f"{to_date[6:10]}-{to_date[3:5]}-{to_date[0:2]}" if len(to_date) == 10 else to_date
                cursor.execute(
                    \"\"\"
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND sign_off_date NOT IN ('HEADER', 'FOOTER') 
                      AND (substr(sign_off_date, 7, 4) || '-' || substr(sign_off_date, 4, 2) || '-' || substr(sign_off_date, 1, 2)) BETWEEN %s AND %s
                    ORDER BY row_index
                    \"\"\",
                    (file_id, fd_iso, td_iso)
                )
            else:
                cursor.execute(
                    \"\"\"
                    SELECT row_index, sl_no, sign_off_date, row_data_json 
                    FROM duty_hours_rows 
                    WHERE file_id = %s 
                      AND sign_off_date NOT IN ('HEADER', 'FOOTER') 
                      AND STR_TO_DATE(sign_off_date, '%%d-%%m-%%Y') BETWEEN STR_TO_DATE(%s, '%%d-%%m-%%Y') AND STR_TO_DATE(%s, '%%d-%%m-%%Y')
                    ORDER BY row_index
                    \"\"\",
                    (file_id, from_date, to_date)
                )"""

old_block2_normalized = old_block2.replace("\r\n", "\n")

if old_block2_normalized in text_normalized:
    text_normalized = text_normalized.replace(old_block2_normalized, new_block2)
    print("Block 2 replaced successfully!")
else:
    print("WARNING: Block 2 not found!")

with open("blueprints/duty_hours.py", "w", encoding="utf-8") as f:
    f.write(text_normalized)

print("Replacement complete.")
