import sys
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages")
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard")

from app import create_app

app = create_app()
client = app.test_client()

print("=== 1. Testing GET /haulage-capacity ===")
res = client.get('/haulage-capacity')
print("Status code:", res.status_code)
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
assert b"Electric Locomotive Hauling Capacity Engine" in res.data, "Header title missing"
assert b"WAG-12B" in res.data, "WAG-12B missing"
assert b"RDSO Publication RDSO/2016/EL/PUB/0002" in res.data, "RDSO reference missing"
print("[PASS] GET /haulage-capacity OK")

print("\n=== 2. Testing POST /api/haulage-calculate ===")
calc_payload = {
    'loco_code': 'WAG12B',
    'condition': 'dry',
    'curve_deg': 0.0,
    'gradient_ratio': '1/100',
    'speed_kmh': 0,
    'axle_load': '25T',
    'motor_mode': 'normal',
    'stock_type': 'BOXN'
}
res2 = client.post('/api/haulage-calculate', json=calc_payload)
print("Status code:", res2.status_code)
assert res2.status_code == 200, f"Expected 200, got {res2.status_code}"
data = res2.get_json()
assert data['success'] is True, "Calculation failed"
print("Result permissible load:", data['data']['permissible_load_tonnes'], "Tonnes")
print("Equivalent BOXN wagons:", data['data']['equivalent_stock_count'])
print("Available TE:", data['data']['tractive_effort_kN'], "kN")
assert data['data']['permissible_load_tonnes'] > 5000, "Expected >5000T for WAG12B 25T on 1/100"
print("[PASS] POST /api/haulage-calculate (WAG12B) OK")

print("\n=== 3. Testing POST /api/haulage-calculate for WAP-7 (Passenger) ===")
res3 = client.post('/api/haulage-calculate', json={
    'loco_code': 'WAP7',
    'condition': 'dry',
    'curve_deg': 0.0,
    'gradient_ratio': '1/100',
    'speed_kmh': 0,
    'stock_type': 'ICF'
})
data3 = res3.get_json()
print("WAP-7 load:", data3['data']['permissible_load_tonnes'], "Tonnes")
print("WAP-7 coaches:", data3['data']['equivalent_stock_count'], "Coaches")
assert data3['data']['equivalent_stock_count'] == 30, f"Expected 30 coaches, got {data3['data']['equivalent_stock_count']}"
print("[PASS] POST /api/haulage-calculate (WAP-7) OK")

print("\n=== 4. Testing GET /loco-info ===")
res4 = client.get('/loco-info')
assert res4.status_code == 200
assert b"Hauling Capacity Calculator (RDSO)" in res4.data
print("[PASS] GET /loco-info contains Hauling Capacity link")

print("\n=== 5. Testing GET /learning-materials ===")
res5 = client.get('/learning-materials')
assert res5.status_code == 200
assert b"Hauling Capacity &amp; Load Calculator (RDSO)" in res5.data
print("[PASS] GET /learning-materials contains Hauling Capacity link")

print("\n=== ALL FLASK ROUTE TESTS PASSED SUCCESSFULLY! ===")
