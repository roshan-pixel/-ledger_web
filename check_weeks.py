import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
sale_val_cols = []
for i, h in enumerate(headers):
    if str(h).startswith('Sale Value'):
        sale_val_cols.append((h, f'c{i+1}'))
for h, col in sale_val_cols:
    c.execute(f"SELECT SUM(CAST(REPLACE({col}, ',', '') AS REAL)) FROM inventory WHERE {col} != '' AND UPPER(c3) != 'TOTAL'")
    val = c.fetchone()[0]
    print(f'{h}: {val}')
