import sqlite3
import json

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

print('Checking invoice items JSON for these items:')
c.execute("SELECT id, invoice_number, status, items FROM invoices")
sold_503 = 0
sold_510 = 0

for r in c.fetchall():
    inv_id, inv_num, status, items_json = r
    if status == 'cancelled':
        continue
    try:
        items = json.loads(items_json or '[]')
        for i in items:
            desc = i.get('description', '') or i.get('name', '')
            if '[503]' in desc:
                sold_503 += float(str(i.get('qty', 0)).replace(',', ''))
            if '[510]' in desc:
                sold_510 += float(str(i.get('qty', 0)).replace(',', ''))
    except Exception as e:
        pass

print(f'Total sold from invoices table JSON - 503: {sold_503}')
print(f'Total sold from invoices table JSON - 510: {sold_510}')

conn.close()
