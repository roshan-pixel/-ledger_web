import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

c.execute("SELECT invoice_no, items FROM invoices WHERE items LIKE '%HALEN%' OR items LIKE '%451%'")
rows = c.fetchall()
found = False
for r in rows:
    found = True
    print(f"Invoice {r[0]}:")
    items = json.loads(r[1])
    for item in items:
        if 'HALEN' in item.get('name', '').upper() or '451' in item.get('name', ''):
            print(f"  {item.get('name')}: Qty {item.get('qty')}")

if not found:
    print("Not found in any invoices.")
conn.close()
