import sqlite3, json

conn = sqlite3.connect('ledger.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
sp_idx = headers.index('SP/Pc') + 1

c.execute('SELECT * FROM invoices')
invoices = c.fetchall()

for inv in invoices:
    items = json.loads(inv['items'])
    total_sp = 0.0
    for item in items:
        name = item.get('name', item.get('description', ''))
        qty = float(item.get('qty', 0))
        if name:
            # Fix: Use LIKE to match the product name even if it has a trailing dash
            c.execute(f"SELECT c{sp_idx} FROM inventory WHERE c3 LIKE ?", (name + '%',))
            row = c.fetchone()
            if row and row[0]:
                try:
                    total_sp += float(row[0]) * qty
                except:
                    pass
    print(f"Invoice {inv['invoice_no']} Total SP calculated: {total_sp}")
    if total_sp > 0:
        c.execute('UPDATE invoices SET total_sp=? WHERE id=?', (total_sp, inv['id']))

conn.commit()
conn.close()

from init_gsheets import init_google_sheets
init_google_sheets()
