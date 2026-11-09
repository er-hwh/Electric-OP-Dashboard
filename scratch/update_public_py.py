import re

with open(r'blueprints\public.py', 'r', encoding='utf-8') as f:
    content = f.read()

import_target = 'from flask import Blueprint, render_template, request, current_app, send_from_directory, flash, redirect, url_for, session'
import_repl = '''from flask import Blueprint, render_template, request, current_app, send_from_directory, flash, redirect, url_for, session, jsonify
from blueprints.haulage_helper import (
    calculate_haulage, LOCO_CATALOG, GRADIENTS, CURVATURES,
    RDSO_STANDARD_MATRIX, WAG12B_MOMENTUM_TABLE, get_loco_summary_list
)'''

assert import_target in content, "import_target not found"
content = content.replace(import_target, import_repl, 1)

routes_code = '''

@public_bp.route('/haulage-capacity', methods=['GET'])
def haulage_capacity():
    """Interactive Electric Locomotive Hauling Capacity & Load Table System."""
    locos = get_loco_summary_list()
    default_calc = calculate_haulage('WAG12B', condition='dry', curve_deg=0.0, gradient_ratio='1/100', speed_kmh=0, axle_load='25T', motor_mode='normal')
    return render_template(
        'public/haulage_calculator.html',
        locos=locos,
        loco_catalog=LOCO_CATALOG,
        gradients=GRADIENTS,
        curvatures=CURVATURES,
        rdso_matrix=RDSO_STANDARD_MATRIX,
        momentum_table=WAG12B_MOMENTUM_TABLE,
        default_calc=default_calc
    )


@public_bp.route('/api/haulage-calculate', methods=['POST'])
def api_haulage_calculate():
    """AJAX JSON endpoint for dynamic instant load and tractive effort calculation."""
    try:
        data = request.get_json() or {}
        loco_code = data.get('loco_code', 'WAG12B')
        condition = data.get('condition', 'dry')
        curve_deg = float(data.get('curve_deg', 0.0))
        gradient_ratio = data.get('gradient_ratio', '1/100')
        speed_kmh = float(data.get('speed_kmh', 0.0))
        axle_load = data.get('axle_load', '25T')
        motor_mode = data.get('motor_mode', 'normal')
        stock_type = data.get('stock_type')

        result = calculate_haulage(
            loco_code=loco_code,
            condition=condition,
            curve_deg=curve_deg,
            gradient_ratio=gradient_ratio,
            speed_kmh=speed_kmh,
            axle_load=axle_load,
            motor_mode=motor_mode,
            stock_type=stock_type
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
'''

loco_info_target = """@public_bp.route('/loco-info')
def loco_info():
    \"\"\"Public portal: Loco Information for Electric & Diesel Locomotives.\"\"\"
    return render_template('public/loco_info.html')"""

assert loco_info_target in content, "loco_info_target not found"
content = content.replace(loco_info_target, loco_info_target + routes_code, 1)

with open(r'blueprints\public.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("[OK] blueprints/public.py successfully updated!")
