import sqlite3
import json

conn = sqlite3.connect('ledger.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM inventory WHERE UPPER(c3) LIKE '%BATHVEDA GLYCERIN%'")
rows = c.fetchall()
if not rows:
    print("Not found.")
else:
    for row in rows:
        print(dict(row))
conn.close()
