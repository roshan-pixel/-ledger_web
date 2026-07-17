import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT SUM(total_amount) FROM invoices WHERE status != 'cancelled'")
print('Total Invoices:', c.fetchone()[0])
conn.close()
