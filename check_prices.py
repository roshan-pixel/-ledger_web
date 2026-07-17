import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT c3, c5, c27 FROM inventory WHERE c5 LIKE '%4765%' OR c27 LIKE '%4765%'")
for r in c.fetchall():
    print(r)
conn.close()
