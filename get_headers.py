import sqlite3, json
conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
print(json.loads(c.fetchone()[0]))
