import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
# print(headers)

# Let's run api_kpi logic directly
c.execute("SELECT * FROM inventory WHERE c3 != 'TOTAL' AND c3 IS NOT NULL")
rows = c.fetchall()

total_skus = 0
rem_qty = 0
gross_val = 0
rem_val = 0
monthly_sales = 0
week_sales = 0

# get indexes
try:
    dp_idx = headers.index('Price/Pc (Rs.)') + 1
    tot_qty_idx = headers.index('Total Qty') + 1
    gross_val_idx = headers.index('Gross Value (Rs.)') + 1
    rem_qty_idx = headers.index('Remaining Qty') + 1
    rem_val_idx = headers.index('Remaining Value (Rs.)') + 1
    
    # week columns (c8 to c18 are the sales cols, usually it's dynamic but let's check)
except ValueError:
    dp_idx = 5
    tot_qty_idx = 7
    gross_val_idx = 8
    rem_qty_idx = 19
    rem_val_idx = 20

for row in rows:
    total_skus += 1
    try:
        r_qty = float(str(row[rem_qty_idx]).replace(',', ''))
        rem_qty += r_qty
    except: pass
    
    try:
        g_val = float(str(row[gross_val_idx]).replace(',', ''))
        gross_val += g_val
    except: pass
    
    try:
        r_val = float(str(row[rem_val_idx]).replace(',', ''))
        rem_val += r_val
    except: pass
    
    # Sum of all sale values (monthly) and last week sale values
    # Let's see what api_kpi does
    pass

c.execute("SELECT value FROM settings WHERE key='kpi_cache'")
cache = c.fetchone()
if cache:
    print("KPI CACHE:", cache[0])
    
print(f"Computed Total SKUs: {total_skus}")
print(f"Computed Rem Qty: {rem_qty}")
print(f"Computed Gross Val: {gross_val}")
print(f"Computed Rem Val: {rem_val}")

conn.close()
