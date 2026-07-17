import sqlite3
conn = sqlite3.connect('C:/Users/sgarm/Downloads/ledger_web/ledger.db')
c = conn.cursor()
c.execute("SELECT c3, c5, c24 FROM inventory WHERE c5 LIKE '685.04%'")
for r in c.fetchall():
    print(r)
