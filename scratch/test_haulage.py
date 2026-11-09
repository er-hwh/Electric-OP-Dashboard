import sys
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard")

from blueprints.haulage_helper import (
    calculate_haulage, LOCO_CATALOG, GRADIENTS, CURVATURES,
    RDSO_STANDARD_MATRIX, WAG12B_MOMENTUM_TABLE
)

print("=== TESTING HAULAGE CALCULATOR ENGINE ===")

# Test 1: WAG-12B on 1/100, Dry, 0 deg curve
r1 = calculate_haulage('WAG12B', condition='dry', curve_deg=0.0, gradient_ratio='1/100', speed_kmh=0, axle_load='25T', motor_mode='normal')
print(f"WAG-12B (25T Normal) on 1/100 Dry: Load = {r1['permissible_load_tonnes']} T, BOXN = {r1['equivalent_stock_count']}, TE = {r1['tractive_effort_kN']} kN")

# Test 2: WAG-12B on 1/100, Wet, 2 deg curve
r2 = calculate_haulage('WAG12B', condition='wet', curve_deg=2.0, gradient_ratio='1/100', speed_kmh=0, axle_load='25T', motor_mode='normal')
print(f"WAG-12B (25T Normal) on 1/100 Wet + 2° curve: Load = {r2['permissible_load_tonnes']} T, BOXN = {r2['equivalent_stock_count']}, Comp Grad = {r2['compensated_gradient']}")

# Test 3: WAG-9H on 1/100, Dry, 0 deg curve
r3 = calculate_haulage('WAG9H', condition='dry', curve_deg=0.0, gradient_ratio='1/100', speed_kmh=0)
print(f"WAG-9H on 1/100 Dry: Load = {r3['permissible_load_tonnes']} T, BOXN = {r3['equivalent_stock_count']}, TE = {r3['tractive_effort_kN']} kN")

# Test 4: WAG-7 on 1/150, Dry, 1 deg curve
r4 = calculate_haulage('WAG7', condition='dry', curve_deg=1.0, gradient_ratio='1/150', speed_kmh=0)
print(f"WAG-7 on 1/150 Dry + 1° curve: Load = {r4['permissible_load_tonnes']} T, BOXN = {r4['equivalent_stock_count']}")

# Test 5: WAP-7 on 1/100, Dry, 0 deg curve (Passenger)
r5 = calculate_haulage('WAP7', condition='dry', curve_deg=0.0, gradient_ratio='1/100', speed_kmh=0)
print(f"WAP-7 on 1/100 Dry: Load = {r5['permissible_load_tonnes']} T, ICF Coaches = {r5['equivalent_stock_count']}, TE = {r5['tractive_effort_kN']} kN")

# Test 6: Running speed test (WAG-9H at 60 km/h on 1/200)
r6 = calculate_haulage('WAG9H', condition='dry', curve_deg=0.0, gradient_ratio='1/200', speed_kmh=60)
print(f"WAG-9H at 60 km/h on 1/200: Load = {r6['permissible_load_tonnes']} T, Running TE = {r6['tractive_effort_kN']} kN")

print("\nAll 6 test cases executed successfully!")
