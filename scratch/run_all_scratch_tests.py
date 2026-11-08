import sys
import subprocess

test_scripts = [
    "scratch/test_phase3.py",
    "scratch/test_phase4.py",
    "scratch/test_phase5.py",
    "scratch/test_phase6.py",
    "scratch/test_phase7.py",
    "scratch/test_upgrades.py"
]

python_exe = r"C:\Users\Indian Railway\AppData\Local\Programs\Python\Python315\python.exe"
base_dir = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard"

all_passed = True
for script in test_scripts:
    full_path = f"{base_dir}\\{script}"
    print(f"\n================ Running {script} ================")
    res = subprocess.run([python_exe, full_path], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(f"FAILED with return code {res.returncode}")
        print(res.stderr)
        all_passed = False
    else:
        print(f"PASSED {script}")

if not all_passed:
    sys.exit(1)
print("\n>>> ALL REGRESSION & UPGRADE TEST SUITES PASSED CLEANLY! <<<")
