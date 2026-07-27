import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

c.execute("SELECT invoice_number, items FROM invoices ORDER BY id DESC LIMIT 50")
for r in c.fetchall():
    try:
        items = json.loads(r[1] or '[]')
        for i in items:
            desc = i.get('description', '') or i.get('name', '')
            if '503' in desc or '510' in desc:
                qty = str(i.get('qty', 0))
                if qty.startswith('-'):
                    print(f"Found negative qty in invoice {r[0]}: {desc} = {qty}")
                elif qty in ('-1', '-2'):
                    print(f"Found negative qty in invoice {r[0]}: {desc} = {qty}")
                else:
                    pass
    except Exception as e:
        pass

conn.close()
