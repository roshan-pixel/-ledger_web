import sqlite3
import json
conn = sqlite3.connect('C:/Users/sgarm/Downloads/ledger_web/ledger.db')
c = conn.cursor()
c.execute("SELECT id, invoice_no, date_created, items, amount, total_sp FROM invoices ORDER BY id DESC LIMIT 5")
for r in c.fetchall():
    print(r)
