import sqlite3
import json

conn = sqlite3.connect('C:/Users/sgarm/Downloads/ledger_web/ledger.db')
c = conn.cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
cols = ['c'+str(i+1) for i,h in enumerate(headers) if h]
c.execute(f"SELECT {', '.join(cols)} FROM inventory WHERE c3 LIKE '%252%'")
row = c.fetchone()
print(dict(zip([h for h in headers if h], row)))

c.execute(f"SELECT {', '.join(cols)} FROM inventory WHERE c3 LIKE '%25%'")
for r in c.fetchall():
    print(r[2]) # name is c3
