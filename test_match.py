import sqlite3, json, re
from invoice_api import get_sold_qty_col_idx
conn = sqlite3.connect('ledger.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
c.execute('SELECT * FROM invoices WHERE id=124')
row = c.fetchone()
sold_idx = get_sold_qty_col_idx(headers, row['date_created'])
print('sold_idx:', sold_idx)
