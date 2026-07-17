import sqlite3
import json
conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
for i, h in enumerate(headers):
    print(f"c{i+1}: {h}")
conn.close()
