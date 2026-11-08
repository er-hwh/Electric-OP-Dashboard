import os

admin_path = r'C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard\blueprints\admin.py'
with open(admin_path, 'r', encoding='utf-8') as f:
    c = f.read()

target = 'send_file, session, jsonify'
replacement = 'send_file, session, jsonify, Response'

if target in c:
    c = c.replace(target, replacement)
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("blueprints/admin.py updated with Response import.")
else:
    print("target not found in admin.py")
