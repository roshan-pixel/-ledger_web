import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("PRAGMA table_info(invoices)")
print(c.fetchall())
c.execute("SELECT SUM(amount_due) FROM invoices WHERE status != 'cancelled'")
print('Total Amount:', c.fetchone()[0])
conn.close()
