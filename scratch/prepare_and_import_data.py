import sys
import os
import re
import csv
from datetime import datetime, date

sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\backup\hwh-division-operation-dashboard\hwh-division-operation-dashboard\venv\Lib\site-packages")
sys.path.insert(0, r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard")

import openpyxl

base_dir = r"C:\Users\Indian Railway\Desktop\PCNL General Shift\WebApp\Electric-OP-Dashboard"
supp_dir = os.path.join(base_dir, "supporting data")
os.makedirs(supp_dir, exist_ok=True)

# The transcript or script can write the CSV files
print("Script environment ready.")
