import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

print('--- Settings ---')
c.execute("SELECT * FROM settings")
for r in c.fetchall():
    print(r)

print('\n--- Inventory Items with <= 0 stock ---')
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
rem_idx = next(i for i, h in enumerate(headers) if 'Remaining Qty' in h) + 1

c.execute(f"SELECT c2, c3, c7, c{rem_idx} FROM inventory WHERE c{rem_idx} != '' AND c3 != 'TOTAL'")
for r in c.fetchall():
    try:
        qty = float(r[3].replace(',', ''))
        if qty < 0:
            print(r)
    except:
        pass

conn.close()
