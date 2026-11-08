import os
import sys

base_dir = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard'

# 1. Update models.py to add @property lobby_name to Lobby
models_path = os.path.join(base_dir, 'models.py')
with open(models_path, 'r', encoding='utf-8') as f:
    models_code = f.read()

if 'def lobby_name(self):' not in models_code:
    target = '    # Relationship with in-charge CLI'
    replacement = '''    @property
    def lobby_name(self):
        return self.name

    # Relationship with in-charge CLI'''
    models_code = models_code.replace(target, replacement)
    with open(models_path, 'w', encoding='utf-8') as f:
        f.write(models_code)
    print("models.py updated with Lobby.lobby_name property.")

# 2. Update blueprints/admin.py: replace Lobby.lobby_name.asc() with Lobby.name.asc()
admin_path = os.path.join(base_dir, 'blueprints', 'admin.py')
with open(admin_path, 'r', encoding='utf-8') as f:
    admin_code = f.read()

if 'Lobby.lobby_name.asc()' in admin_code:
    admin_code = admin_code.replace('Lobby.lobby_name.asc()', 'Lobby.name.asc()')
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(admin_code)
    print("blueprints/admin.py updated with Lobby.name.asc().")

# 3. Update blueprints/officer.py: replace Lobby.lobby_name.asc() with Lobby.name.asc()
officer_path = os.path.join(base_dir, 'blueprints', 'officer.py')
with open(officer_path, 'r', encoding='utf-8') as f:
    officer_code = f.read()

if 'Lobby.lobby_name.asc()' in officer_code:
    officer_code = officer_code.replace('Lobby.lobby_name.asc()', 'Lobby.name.asc()')
    with open(officer_path, 'w', encoding='utf-8') as f:
        f.write(officer_code)
    print("blueprints/officer.py updated with Lobby.name.asc().")

# 4. Update blueprints/control.py: fix parse_date_value and Lobby.lobby_name.asc()
control_path = os.path.join(base_dir, 'blueprints', 'control.py')
with open(control_path, 'r', encoding='utf-8') as f:
    control_code = f.read()

if 'Lobby.lobby_name.asc()' in control_code:
    control_code = control_code.replace('Lobby.lobby_name.asc()', 'Lobby.name.asc()')

old_control_parse = '''def parse_date_value(val):
    if not val:
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    s = str(val).strip()
    if not s or s.upper() in ('NA', 'N/A', '-', '#N/A', 'NONE', 'NIL', 'NULL', 'UNKNOWN', '0'):
        return None
    for fmt in [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d.%m.%Y", "%d-%b-%Y", "%d-%B-%Y", "%d-%b-%y"
    ]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None'''

new_control_parse = '''def parse_date_value(val):
    if not val:
        return None
    if isinstance(val, (dt, date)):
        return val.date() if isinstance(val, dt) else val
    s = str(val).strip()
    if not s or s.upper() in ('NA', 'N/A', '-', '#N/A', 'NONE', 'NIL', 'NULL', 'UNKNOWN', '0'):
        return None
    for fmt in [
        "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d",
        "%d.%m.%Y", "%d-%b-%Y", "%d-%B-%Y", "%d-%b-%y"
    ]:
        try:
            return dt.strptime(s, fmt).date()
        except ValueError:
            pass
    return None'''

if old_control_parse in control_code:
    control_code = control_code.replace(old_control_parse, new_control_parse)
    with open(control_path, 'w', encoding='utf-8') as f:
        f.write(control_code)
    print("blueprints/control.py parse_date_value fixed.")
else:
    with open(control_path, 'w', encoding='utf-8') as f:
        f.write(control_code)
    print("blueprints/control.py saved.")

print("All fixes applied successfully.")
