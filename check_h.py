import sqlite3
import json
c = sqlite3.connect('C:/Users/sgarm/Downloads/ledger_web/ledger.db').cursor()
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
headers = json.loads(c.fetchone()[0])
print([h for h in headers if 'Sold' in h])
