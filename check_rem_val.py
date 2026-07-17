import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])

rem_qty_idx = next((i+1 for i, h in enumerate(headers) if 'Remaining Qty' in str(h)), 19)
rem_val_idx = next((i+1 for i, h in enumerate(headers) if 'Remaining Value' in str(h)), 20)
price_idx = next((i+1 for i, h in enumerate(headers) if 'Price/Pc' in str(h)), 5)

c.execute(f"SELECT SUM(CAST(REPLACE(c{rem_val_idx}, ',', '') AS REAL)) FROM inventory WHERE c{rem_val_idx} != '' AND UPPER(c3) != 'TOTAL'")
db_rem_val = c.fetchone()[0] or 0

print('Sum of c20 (Remaining Value Rs):', db_rem_val)

c.execute(f"SELECT c3, c{rem_qty_idx}, c{price_idx}, c{rem_val_idx} FROM inventory WHERE c3 != '' AND UPPER(c3) != 'TOTAL'")
calc_val = 0
for row in c.fetchall():
    try:
        qty = float(str(row[1]).replace(',', '')) if row[1] else 0
        price = float(str(row[2]).replace(',', '')) if row[2] else 0
        expected = qty * price
        actual = float(str(row[3]).replace(',', '')) if row[3] else 0
        if abs(expected - actual) > 1:
            print(f"Mismatch in {row[0]}: expected {expected}, got {actual}")
        calc_val += expected
    except Exception as e:
        print("Error on row:", row, e)

print('Calculated Remaining Value (Qty * Price):', calc_val)
conn.close()
