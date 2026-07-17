import sqlite3
import json

conn = sqlite3.connect('ledger.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT invoice_no, items FROM invoices WHERE status != 'cancelled'")
for r in c.fetchall():
    items = json.loads(r['items'] or '[]')
    for item in items:
        desc = str(item.get('description') or item.get('name') or '').strip()
        qty = float(item.get('qty', 0))
        if desc and qty > 0:
            norm_desc = desc.replace('\n', ' ').replace(' -', '').strip().upper()
            if norm_desc == 'LUXE MATTE LIQUID LIPSTICK- HALEN [451]':
                print(f"Invoice {r['invoice_no']} added {qty} of {desc}")
