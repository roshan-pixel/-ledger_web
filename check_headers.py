import sqlite3, json
c = sqlite3.connect('ledger.db').cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
print(json.loads(c.fetchone()[0]))
