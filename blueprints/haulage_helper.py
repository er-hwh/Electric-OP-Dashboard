"""
Hauling Capacity & Load Table Helper Module for Electric Locomotives.
Based on official technical publications:
1. RDSO Publication RDSO/2016/EL/PUB/0002 Rev. '0' (Electrical Loco Directorate, June 2016)
   - Locomotives: WAG-9, WAG-9H, WAG-7, WAG-5A, WAG-5H, WAM-4, WAP-7, WAP-5, WAP-4
   - Conditions: Dry vs Wet Rail (20% adhesion loss as per TFC-77 standard)
   - Gradients: Level, 1/500, 1/200, 1/150, 1/100, 1/50
   - Curvatures: 0 deg (Tangent) to 5 deg
   - Stock: Loaded BOXN (5400 T max, 59 wagons) & ICF All-Coil coaches (1650 T max, 30 coaches)
2. ALSTOM / Madhepura Electric Locomotive Project (WAG-12B)
   - Ref: NHD0000266360 Rev 5, May 2023
   - WAG-12B: 12,000 HP Twin Bo-Bo, 200T (25T/axle) & 180T (22.5T/axle)
   - Normal (8 TMs) vs Degraded (6 TMs), 785 kN / 706 kN starting TE
   - Heavy haul trailing loads up to 6000T, 7040T, 7600T, and momentum speed tables
"""

import math

# ==============================================================================
# 1. LOCOMOTIVE TECHNICAL DATA CATALOGUE
# ==============================================================================
LOCO_CATALOG = {
    'WAG12B': {
        'code': 'WAG12B',
        'name': 'WAG-12B (ALSTOM Twin Section)',
        'type': 'Freight',
        'hp': 12000,
        'kw': 9000,
        'wheel_arr': 'Twin Bo-Bo (8 Axles)',
        'max_speed': 120,
        'weight_options': {
            '25T': {
                'weight': 200.0,
                'axle_load': 25.0,
                'te_normal_dry': 785.0,     # kN (40% adhesion)
                'te_normal_wet': 628.0,     # kN (32% adhesion - 20% reduction)
                'te_degraded_dry': 588.0,   # kN (6 TMs working)
                'te_degraded_wet': 470.0,   # kN
            },
            '22.5T': {
                'weight': 180.0,
                'axle_load': 22.5,
                'te_normal_dry': 706.0,     # kN (40% adhesion)
                'te_normal_wet': 565.0,     # kN (32% adhesion)
                'te_degraded_dry': 529.0,   # kN
                'te_degraded_wet': 423.0,   # kN
            }
        },
        'default_weight': 200.0,
        'default_te_start': 785.0,
        'brake_effort_max': 510.0,  # kN regenerative brake
        'stock_type': 'BOXN',
        'doc_ref': 'ALSTOM Madhepura NHD0000266360 Rev 5 (2023)'
    },
    'WAG9H': {
        'code': 'WAG9H',
        'name': 'WAG-9H (Heavy Freight 3-Phase)',
        'type': 'Freight',
        'hp': 6120,
        'kw': 4500,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 132.0,
        'axle_load': 22.0,
        'max_speed': 100,
        'te_start_dry': 500.0,  # kN
        'te_start_wet': 400.0,  # kN (20% reduction)
        'stock_type': 'BOXN',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAG9': {
        'code': 'WAG9',
        'name': 'WAG-9 (Standard Freight 3-Phase)',
        'type': 'Freight',
        'hp': 6000,
        'kw': 4500,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 123.0,
        'axle_load': 20.5,
        'max_speed': 100,
        'te_start_dry': 460.0,  # kN
        'te_start_wet': 368.0,  # kN
        'stock_type': 'BOXN',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAG7': {
        'code': 'WAG7',
        'name': 'WAG-7 (High Adhesion DC Traction)',
        'type': 'Freight',
        'hp': 5000,
        'kw': 3730,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 123.0,
        'axle_load': 20.5,
        'max_speed': 100,
        'te_start_dry': 402.0,  # kN (~41.0 Tonnes)
        'te_start_wet': 321.6,  # kN
        'stock_type': 'BOXN',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAG5H': {
        'code': 'WAG5H',
        'name': 'WAG-5H / WAG-5HA (Hitachi TMs)',
        'type': 'Freight',
        'hp': 4150,
        'kw': 3100,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 123.0,
        'axle_load': 20.5,
        'max_speed': 105,
        'te_start_dry': 365.0,  # kN (~37.2 Tonnes)
        'te_start_wet': 292.0,  # kN
        'stock_type': 'BOXN',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAG5A': {
        'code': 'WAG5A',
        'name': 'WAG-5A (Alstom TMs)',
        'type': 'Freight',
        'hp': 3850,
        'kw': 2870,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 118.8,
        'axle_load': 19.8,
        'max_speed': 80,
        'te_start_dry': 335.0,  # kN (~34.2 Tonnes)
        'te_start_wet': 268.0,  # kN
        'stock_type': 'BOXN',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAP7': {
        'code': 'WAP7',
        'name': 'WAP-7 (Heavy Passenger 3-Phase)',
        'type': 'Passenger',
        'hp': 6120,
        'kw': 4500,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 123.0,
        'axle_load': 20.5,
        'max_speed': 140,
        'te_start_dry': 322.6,  # kN (~32.9 Tonnes)
        'te_start_wet': 258.1,  # kN
        'stock_type': 'ICF',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAP5': {
        'code': 'WAP5',
        'name': 'WAP-5 (High Speed Bo-Bo 3-Phase)',
        'type': 'Passenger',
        'hp': 5450,
        'kw': 4000,
        'wheel_arr': 'Bo-Bo (4 Axles)',
        'weight': 78.0,
        'axle_load': 19.5,
        'max_speed': 160,
        'te_start_dry': 258.0,  # kN (~26.3 Tonnes)
        'te_start_wet': 206.4,  # kN
        'stock_type': 'ICF',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAP4': {
        'code': 'WAP4',
        'name': 'WAP-4 (Standard Passenger DC Traction)',
        'type': 'Passenger',
        'hp': 5000,
        'kw': 3730,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 112.8,
        'axle_load': 18.8,
        'max_speed': 140,
        'te_start_dry': 308.0,  # kN (~31.4 Tonnes)
        'te_start_wet': 246.4,  # kN
        'stock_type': 'ICF',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    },
    'WAM4': {
        'code': 'WAM4',
        'name': 'WAM-4 (Mixed Traffic DC Traction)',
        'type': 'Passenger',
        'hp': 3850,
        'kw': 2870,
        'wheel_arr': 'Co-Co (6 Axles)',
        'weight': 112.8,
        'axle_load': 18.8,
        'max_speed': 110,
        'te_start_dry': 335.0,  # kN (~34.2 Tonnes)
        'te_start_wet': 268.0,  # kN
        'stock_type': 'ICF',
        'doc_ref': "RDSO/2016/EL/PUB/0002 Rev. '0'"
    }
}

# ==============================================================================
# 2. STANDARD GRADIENTS & CURVATURES
# ==============================================================================
GRADIENTS = [
    {'code': 'LEVEL', 'name': 'Level (Tangent)', 'val': 0.0, 'ratio': 'Level'},
    {'code': '1_500', 'name': '1 in 500 (0.20%)', 'val': 1.0 / 500.0, 'ratio': '1/500'},
    {'code': '1_300', 'name': '1 in 300 (0.33%)', 'val': 1.0 / 300.0, 'ratio': '1/300'},
    {'code': '1_200', 'name': '1 in 200 (0.50%)', 'val': 1.0 / 200.0, 'ratio': '1/200'},
    {'code': '1_150', 'name': '1 in 150 (0.67%)', 'val': 1.0 / 150.0, 'ratio': '1/150'},
    {'code': '1_100', 'name': '1 in 100 (1.00%)', 'val': 1.0 / 100.0, 'ratio': '1/100'},
    {'code': '1_75',  'name': '1 in 75  (1.33%)', 'val': 1.0 / 75.0,  'ratio': '1/75'},
    {'code': '1_50',  'name': '1 in 50  (2.00% Ghat)', 'val': 1.0 / 50.0,  'ratio': '1/50'},
    {'code': '1_40',  'name': '1 in 40  (2.50% Heavy Ghat)', 'val': 1.0 / 40.0,  'ratio': '1/40'}
]

CURVATURES = [
    {'deg': 0.0, 'name': '0° (Tangent Track)'},
    {'deg': 1.0, 'name': '1° Curve (R = 1750 m)'},
    {'deg': 2.0, 'name': '2° Curve (R = 875 m)'},
    {'deg': 3.0, 'name': '3° Curve (R = 583 m)'},
    {'deg': 4.0, 'name': '4° Curve (R = 438 m)'},
    {'deg': 5.0, 'name': '5° Curve (R = 350 m)'}
]

# Standard Wagon Weights for Loaded Stock
WEIGHT_PER_BOXN = 91.5   # Tonnes per loaded BOXN (Gross, 22.5T axle load)
WEIGHT_PER_ICF_COACH = 55.0  # Tonnes per ICF passenger coach

# ==============================================================================
# 3. RDSO & ALSTOM RESISTANCE FORMULAE
# ==============================================================================
def get_compensated_gradient(gradient_val, curve_deg):
    """
    Computes compensated gradient taking curve resistance into account.
    According to RDSO: Equivalent Grade = 1/G + (0.4 * Curve_Degree / 1000)
    Returns: compensated decimal slope, e.g. 0.0108 for 1/100 + 2 deg
    """
    curve_grade_equiv = (0.4 * curve_deg) / 1000.0
    return gradient_val + curve_grade_equiv


def get_loco_resistance(loco_type, speed_kmh):
    """
    Specific resistance of locomotive in kg/tonne (RDSO formula).
    At start (speed=0): 6.0 kg/tonne.
    """
    if speed_kmh <= 0:
        return 6.0  # Starting resistance in kg/tonne
    
    V = float(speed_kmh)
    if loco_type in ('WAG12B', 'WAG9', 'WAG9H', 'WAP7'):
        # 3-Phase / Modern Bo-Bo & Co-Co
        return 2.27 + (0.00378 * V) + (0.000155 * (V ** 2))
    elif loco_type in ('WAP5',):
        return 2.05 + (0.00350 * V) + (0.000140 * (V ** 2))
    else:
        # DC Traction: WAG7, WAG5A, WAG5H, WAP4, WAM4
        return 2.47 + (0.00410 * V) + (0.000170 * (V ** 2))


def get_stock_resistance(stock_type, speed_kmh):
    """
    Specific resistance of rolling stock in kg/tonne (RDSO formula).
    BOXN: Loaded freight stock (max 5400 tonnes, 59 wagons)
    ICF: All-coil SG passenger coaches (max 1650 tonnes, 30 coaches)
    """
    if speed_kmh <= 0:
        if stock_type == 'BOXN':
            return 4.0  # 4.0 kg/tonne starting resistance
        else:
            return 4.5  # 4.5 kg/tonne starting resistance for coaches
            
    V = float(speed_kmh)
    if stock_type == 'BOXN':
        # RDSO formula for Loaded BOXN wagons
        return 0.64387 + (0.010472 * V) + (0.00007323 * (V ** 2))
    else:
        # RDSO formula for ICF Passenger coaches
        return 1.347 + (0.00385 * V) + (0.000148 * (V ** 2))


def get_loco_tractive_effort(loco_code, speed_kmh, condition='dry', axle_load='25T', motor_mode='normal'):
    """
    Returns available tractive effort (in kN) for the loco at given speed and condition.
    Includes constant power envelope decay at higher speeds.
    """
    cfg = LOCO_CATALOG[loco_code]
    is_wet = (condition.lower() == 'wet')
    
    # 1. Starting TE determination
    if loco_code == 'WAG12B':
        w_cfg = cfg['weight_options'].get(axle_load, cfg['weight_options']['25T'])
        if motor_mode.lower() == 'degraded':
            te_start = w_cfg['te_degraded_wet'] if is_wet else w_cfg['te_degraded_dry']
            kw_avail = cfg['kw'] * 0.75  # 6 out of 8 motors
        else:
            te_start = w_cfg['te_normal_wet'] if is_wet else w_cfg['te_normal_dry']
            kw_avail = cfg['kw']
    else:
        te_start = cfg['te_start_wet'] if is_wet else cfg['te_start_dry']
        kw_avail = cfg['kw']

    if speed_kmh <= 1.0:
        return te_start

    # 2. Running TE from Power curve: TE (kN) = (kW * 3.6 * Efficiency) / Speed (km/h)
    # Electrical transmission efficiency ~0.88 - 0.92
    eff = 0.90 if 'WAG' in loco_code or 'WAP' in loco_code else 0.85
    power_te = (kw_avail * 3.6 * eff) / speed_kmh
    
    # TE cannot exceed starting TE boundary (adhesion limit)
    te = min(te_start, power_te)
    return round(te, 1)


# ==============================================================================
# 4. HAULING CAPACITY CALCULATION ENGINE
# ==============================================================================
def calculate_haulage(loco_code, condition='dry', curve_deg=0.0, gradient_ratio='1/100', 
                      speed_kmh=0, axle_load='25T', motor_mode='normal', stock_type=None):
    """
    Computes exact permissible trailing load in tonnes, equivalent wagons/coaches,
    starting and running tractive effort, adhesion demand, and safety margin.
    """
    if loco_code not in LOCO_CATALOG:
        loco_code = 'WAG9H'
    loco = LOCO_CATALOG[loco_code]
    
    # Determine default stock type if not given
    if not stock_type:
        stock_type = loco.get('stock_type', 'BOXN')
        
    # Loco Weight
    if loco_code == 'WAG12B':
        w_cfg = loco['weight_options'].get(axle_load, loco['weight_options']['25T'])
        loco_weight = w_cfg['weight']
    else:
        loco_weight = loco['weight']

    # Convert gradient ratio to decimal slope
    grad_val = 0.0
    if gradient_ratio and gradient_ratio.upper() != 'LEVEL':
        try:
            parts = gradient_ratio.split('/')
            if len(parts) == 2:
                grad_val = 1.0 / float(parts[1])
            else:
                grad_val = float(gradient_ratio)
        except Exception:
            grad_val = 0.01  # default 1/100

    # Compensated Gradient (incorporating curve resistance: 0.4 kg/tonne/deg)
    comp_grad = get_compensated_gradient(grad_val, curve_deg)
    
    # Available Tractive Effort (kN)
    te_kN = get_loco_tractive_effort(loco_code, speed_kmh, condition, axle_load, motor_mode)
    te_kg = (te_kN * 1000.0) / 9.80665  # Convert kN to kg force
    
    # Resistances in kg/tonne
    # Grade resistance = G * 1000 kg/tonne
    r_grade = comp_grad * 1000.0
    r_loco = get_loco_resistance(loco_code, speed_kmh) + r_grade
    r_stock = get_stock_resistance(stock_type, speed_kmh) + r_grade
    
    # Total Loco Resistance (kg force)
    total_loco_res_kg = loco_weight * r_loco
    
    # Available Drawbar Pull (kg force)
    drawbar_pull_kg = te_kg - total_loco_res_kg
    
    if drawbar_pull_kg <= 0 or r_stock <= 0:
        trailing_load_tonnes = 0.0
    else:
        trailing_load_tonnes = drawbar_pull_kg / r_stock

    # Apply Maximum Stock Limit caps as per RDSO / Alstom regulations
    if stock_type == 'BOXN':
        if loco_code == 'WAG12B':
            max_cap = 7600.0  # Alstom WAG-12B maximum heavy haul test limit
        else:
            max_cap = 5400.0  # Standard RDSO freight limit (58-59 loaded BOXN)
    else:
        max_cap = 1650.0      # RDSO passenger maximum (30 ICF coaches)
        
    permissible_load = min(trailing_load_tonnes, max_cap)
    permissible_load = max(0.0, round(permissible_load, 0))
    
    # Equivalent stock count
    if stock_type == 'BOXN':
        wagons = math.floor(permissible_load / WEIGHT_PER_BOXN)
        stock_unit_name = 'BOXN Loaded Wagons'
        full_rake_note = f"{wagons} / 58 Wagons ({round((wagons / 58.0) * 100)}% Full Rake)"
    else:
        wagons = math.floor(permissible_load / WEIGHT_PER_ICF_COACH)
        stock_unit_name = 'ICF Coaches'
        full_rake_note = f"{wagons} / 24 Coaches ({round((wagons / 24.0) * 100)}% Standard Rake)"

    # Adhesion percentage utilized
    normal_force_kN = loco_weight * 9.80665
    adhesion_pct = round((te_kN / normal_force_kN) * 100.0, 1)

    # Gradient display string
    if grad_val <= 0.0:
        grad_disp = "Level Track"
    else:
        grad_disp = f"1 in {int(round(1.0 / grad_val))}"
        
    comp_ratio = int(round(1.0 / comp_grad)) if comp_grad > 0.0 else 0
    comp_grad_disp = f"1 in {comp_ratio}" if comp_ratio > 0 else "Level"

    return {
        'loco_code': loco_code,
        'loco_name': loco['name'],
        'loco_weight': loco_weight,
        'stock_type': stock_type,
        'stock_unit_name': stock_unit_name,
        'condition': condition.upper(),
        'curve_deg': curve_deg,
        'gradient_ratio': grad_disp,
        'compensated_gradient': comp_grad_disp,
        'compensated_slope_pct': round(comp_grad * 100.0, 3),
        'speed_kmh': speed_kmh,
        'axle_load': axle_load,
        'motor_mode': motor_mode,
        'tractive_effort_kN': te_kN,
        'drawbar_pull_kN': round((drawbar_pull_kg * 9.80665) / 1000.0, 1),
        'adhesion_pct': adhesion_pct,
        'permissible_load_tonnes': int(permissible_load),
        'max_capacity_tonnes': int(max_cap),
        'equivalent_stock_count': wagons,
        'full_rake_note': full_rake_note,
        'loco_specific_resistance': round(r_loco, 2),
        'stock_specific_resistance': round(r_stock, 2),
        'doc_ref': loco['doc_ref']
    }


# ==============================================================================
# 5. OFFICIAL RDSO & ALSTOM STANDARD LOAD MATRICES
# ==============================================================================
# Standard lookup matrices directly compiled from RDSO/2016/EL/PUB/0002 Rev. '0'
# and Alstom WAG12B Rev 5 documents (Loaded BOXN 5400T max, ICF 1650T max)
RDSO_STANDARD_MATRIX = {
    'WAG12B_25T': {
        'name': 'WAG-12B (25T Axle Load, Normal 8 TMs)',
        'type': 'Freight (Loaded BOXN)',
        'dry': {
            'Level': {'0deg': 7600, '1deg': 7600, '2deg': 7600, '3deg': 7600, '4deg': 7600, '5deg': 7600},
            '1/500': {'0deg': 7600, '1deg': 7600, '2deg': 7600, '3deg': 7450, '4deg': 7200, '5deg': 6950},
            '1/200': {'0deg': 7600, '1deg': 7350, '2deg': 6950, '3deg': 6600, '4deg': 6300, '5deg': 6000},
            '1/150': {'0deg': 6850, '1deg': 6500, '2deg': 6200, '3deg': 5900, '4deg': 5650, '5deg': 5400},
            '1/100': {'0deg': 5400, '1deg': 5150, '2deg': 4950, '3deg': 4750, '4deg': 4550, '5deg': 4380},
            '1/75':  {'0deg': 4450, '1deg': 4280, '2deg': 4120, '3deg': 3980, '4deg': 3840, '5deg': 3710},
            '1/50':  {'0deg': 3240, '1deg': 3130, '2deg': 3030, '3deg': 2940, '4deg': 2850, '5deg': 2770},
            '1/40':  {'0deg': 2670, '1deg': 2590, '2deg': 2510, '3deg': 2440, '4deg': 2380, '5deg': 2310}
        },
        'wet': {
            'Level': {'0deg': 7600, '1deg': 7600, '2deg': 7600, '3deg': 7600, '4deg': 7600, '5deg': 7600},
            '1/500': {'0deg': 7600, '1deg': 7400, '2deg': 7100, '3deg': 6800, '4deg': 6550, '5deg': 6300},
            '1/200': {'0deg': 6600, '1deg': 6250, '2deg': 5950, '3deg': 5650, '4deg': 5400, '5deg': 5150},
            '1/150': {'0deg': 5650, '1deg': 5380, '2deg': 5120, '3deg': 4900, '4deg': 4680, '5deg': 4480},
            '1/100': {'0deg': 4400, '1deg': 4220, '2deg': 4050, '3deg': 3900, '4deg': 3750, '5deg': 3610},
            '1/75':  {'0deg': 3620, '1deg': 3490, '2deg': 3360, '3deg': 3240, '4deg': 3130, '5deg': 3020},
            '1/50':  {'0deg': 2640, '1deg': 2550, '2deg': 2470, '3deg': 2400, '4deg': 2330, '5deg': 2260},
            '1/40':  {'0deg': 2180, '1deg': 2110, '2deg': 2050, '3deg': 1990, '4deg': 1940, '5deg': 1890}
        }
    },
    'WAG9H': {
        'name': 'WAG-9H (132T Heavy Freight Co-Co)',
        'type': 'Freight (Loaded BOXN)',
        'dry': {
            'Level': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5400, '4deg': 5400, '5deg': 5400},
            '1/500': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5400, '4deg': 5400, '5deg': 5400},
            '1/200': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5120, '4deg': 4870, '5deg': 4640},
            '1/150': {'0deg': 5100, '1deg': 4840, '2deg': 4600, '3deg': 4390, '4deg': 4190, '5deg': 4010},
            '1/100': {'0deg': 3820, '1deg': 3660, '2deg': 3510, '3deg': 3370, '4deg': 3240, '5deg': 3120},
            '1/50':  {'0deg': 2160, '1deg': 2090, '2deg': 2020, '3deg': 1960, '4deg': 1900, '5deg': 1850}
        },
        'wet': {
            'Level': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5400, '4deg': 5400, '5deg': 5400},
            '1/500': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5230, '4deg': 4960, '5deg': 4720},
            '1/200': {'0deg': 4750, '1deg': 4510, '2deg': 4300, '3deg': 4100, '4deg': 3920, '5deg': 3750},
            '1/150': {'0deg': 4030, '1deg': 3840, '2deg': 3670, '3deg': 3510, '4deg': 3360, '5deg': 3220},
            '1/100': {'0deg': 3040, '1deg': 2920, '2deg': 2800, '3deg': 2700, '4deg': 2600, '5deg': 2510},
            '1/50':  {'0deg': 1730, '1deg': 1670, '2deg': 1620, '3deg': 1570, '4deg': 1530, '5deg': 1480}
        }
    },
    'WAG7': {
        'name': 'WAG-7 (123T DC Traction)',
        'type': 'Freight (Loaded BOXN)',
        'dry': {
            'Level': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5400, '4deg': 5400, '5deg': 5400},
            '1/500': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5400, '4deg': 5150, '5deg': 4900},
            '1/200': {'0deg': 4850, '1deg': 4610, '2deg': 4390, '3deg': 4190, '4deg': 4000, '5deg': 3830},
            '1/150': {'0deg': 4120, '1deg': 3930, '2deg': 3750, '3deg': 3590, '4deg': 3440, '5deg': 3300},
            '1/100': {'0deg': 3100, '1deg': 2970, '2deg': 2850, '3deg': 2740, '4deg': 2640, '5deg': 2540},
            '1/50':  {'0deg': 1760, '1deg': 1700, '2deg': 1650, '3deg': 1600, '4deg': 1560, '5deg': 1510}
        },
        'wet': {
            'Level': {'0deg': 5400, '1deg': 5400, '2deg': 5400, '3deg': 5000, '4deg': 4750, '5deg': 4520},
            '1/500': {'0deg': 5200, '1deg': 4930, '2deg': 4690, '3deg': 4470, '4deg': 4270, '5deg': 4080},
            '1/200': {'0deg': 3820, '1deg': 3640, '2deg': 3480, '3deg': 3330, '4deg': 3190, '5deg': 3060},
            '1/150': {'0deg': 3260, '1deg': 3120, '2deg': 2980, '3deg': 2860, '4deg': 2740, '5deg': 2640},
            '1/100': {'0deg': 2470, '1deg': 2370, '2deg': 2280, '3deg': 2200, '4deg': 2120, '5deg': 2050},
            '1/50':  {'0deg': 1410, '1deg': 1370, '2deg': 1330, '3deg': 1290, '4deg': 1250, '5deg': 1220}
        }
    },
    'WAP7': {
        'name': 'WAP-7 (123T Passenger Co-Co)',
        'type': 'Passenger (ICF Coaches)',
        'dry': {
            'Level': {'0deg': 1650, '1deg': 1650, '2deg': 1650, '3deg': 1650, '4deg': 1650, '5deg': 1650},
            '1/500': {'0deg': 1650, '1deg': 1650, '2deg': 1650, '3deg': 1650, '4deg': 1650, '5deg': 1650},
            '1/200': {'0deg': 1650, '1deg': 1650, '2deg': 1650, '3deg': 1650, '4deg': 1650, '5deg': 1650},
            '1/150': {'0deg': 1650, '1deg': 1650, '2deg': 1650, '3deg': 1650, '4deg': 1650, '5deg': 1580},
            '1/100': {'0deg': 1650, '1deg': 1650, '2deg': 1590, '3deg': 1530, '4deg': 1470, '5deg': 1420},
            '1/50':  {'0deg': 1180, '1deg': 1140, '2deg': 1100, '3deg': 1070, '4deg': 1040, '5deg': 1010}
        },
        'wet': {
            'Level': {'0deg': 1650, '1deg': 1650, '2deg': 1650, '3deg': 1650, '4deg': 1650, '5deg': 1650},
            '1/500': {'0deg': 1650, '1deg': 1650, '2deg': 1650, '3deg': 1650, '4deg': 1650, '5deg': 1650},
            '1/200': {'0deg': 1650, '1deg': 1650, '2deg': 1650, '3deg': 1650, '4deg': 1610, '5deg': 1540},
            '1/150': {'0deg': 1650, '1deg': 1650, '2deg': 1570, '3deg': 1500, '4deg': 1440, '5deg': 1380},
            '1/100': {'0deg': 1340, '1deg': 1290, '2deg': 1240, '3deg': 1200, '4deg': 1160, '5deg': 1120},
            '1/50':  {'0deg': 940,  '1deg': 910,  '2deg': 880,  '3deg': 860,  '4deg': 830,  '5deg': 810}
        }
    }
}

# ==============================================================================
# 6. ALSTOM WAG-12B ENTRY-EXIT MOMENTUM SPEED TABLE
# ==============================================================================
# From ALSTOM Document NHD0000266360 Rev 5 (Section 4: Gradient Negotiation)
WAG12B_MOMENTUM_TABLE = [
    {
        'gradient': '1 in 100 Compensated',
        'load_tonnes': 6000,
        'curve': 'Tangent to 2°',
        'entry_speed': 75,
        'exit_speed': 45,
        'min_run_length_km': 2.0,
        'status': 'Permissible with full momentum'
    },
    {
        'gradient': '1 in 100 Compensated',
        'load_tonnes': 6600,
        'curve': 'Tangent to 2°',
        'entry_speed': 80,
        'exit_speed': 40,
        'min_run_length_km': 2.5,
        'status': 'Permissible (Speed strictly monitored)'
    },
    {
        'gradient': '1 in 100 Compensated',
        'load_tonnes': 7040,
        'curve': 'Tangent to 1°',
        'entry_speed': 85,
        'exit_speed': 35,
        'min_run_length_km': 3.0,
        'status': 'Requires TLC permission (Clear block ahead)'
    },
    {
        'gradient': '1 in 150 Compensated',
        'load_tonnes': 6000,
        'curve': 'Tangent to 3°',
        'entry_speed': 65,
        'exit_speed': 55,
        'min_run_length_km': 1.5,
        'status': 'Normal working'
    },
    {
        'gradient': '1 in 150 Compensated',
        'load_tonnes': 7040,
        'curve': 'Tangent to 2°',
        'entry_speed': 75,
        'exit_speed': 50,
        'min_run_length_km': 2.0,
        'status': 'Permissible'
    },
    {
        'gradient': '1 in 150 Compensated',
        'load_tonnes': 7600,
        'curve': 'Tangent track',
        'entry_speed': 85,
        'exit_speed': 45,
        'min_run_length_km': 2.5,
        'status': 'Heavy-Haul Trial Standard'
    },
    {
        'gradient': '1 in 200 Compensated',
        'load_tonnes': 7600,
        'curve': 'Tangent to 2°',
        'entry_speed': 70,
        'exit_speed': 60,
        'min_run_length_km': 1.5,
        'status': 'Sustained Heavy Haul'
    }
]

def get_loco_summary_list():
    """Returns sorted summary of all supported electric locomotives."""
    items = []
    for code, info in LOCO_CATALOG.items():
        items.append({
            'code': code,
            'name': info['name'],
            'type': info['type'],
            'hp': info['hp'],
            'kw': info['kw'],
            'weight': info.get('weight', info.get('default_weight')),
            'max_speed': info['max_speed'],
            'stock_type': info['stock_type']
        })
    return items
