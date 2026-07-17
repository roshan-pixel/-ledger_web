import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT date_created FROM invoices WHERE invoice_no = 'DSR/000070/26-27'")
print(c.fetchone())
conn.close()
