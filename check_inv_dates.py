import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT date_created, amount FROM invoices WHERE status != 'cancelled' ORDER BY id")
for r in c.fetchall():
    print(r)
conn.close()
