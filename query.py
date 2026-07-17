import sqlite3, json
c = sqlite3.connect('ledger.db').cursor()
headers = json.loads(c.execute("SELECT value FROM settings WHERE key='inventory_headers'").fetchone()[0])
print(headers[:19])
