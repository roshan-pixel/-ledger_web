import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT items, amount FROM invoices ORDER BY id DESC LIMIT 1")
row = c.fetchone()
if row:
    items = json.loads(row[0])
    print('Invoice Amount:', row[1])
    for item in items:
        print(f"{item.get('name', '')} | Qty: {item.get('qty')} | Price: {item.get('price')} | Total: {item.get('total')}")
conn.close()
