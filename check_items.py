import sqlite3
conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT c3 FROM inventory WHERE c3 LIKE '%BATHVEDA%' OR c3 LIKE '%235%'")
for row in c.fetchall():
    print(row[0])
conn.close()
