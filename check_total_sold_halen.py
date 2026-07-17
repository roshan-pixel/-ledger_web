import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

c.execute("SELECT invoice_no, items FROM invoices")
rows = c.fetchall()
total_sold = 0
for r in rows:
    items = json.loads(r[1])
    for item in items:
        if 'HALEN' in item.get('name', '').upper():
            print(f"Invoice {r[0]}: {item.get('name')} - Qty {item.get('qty')}")
            total_sold += float(item.get('qty', 0))

print(f"Total sold for HALEN: {total_sold}")
conn.close()
