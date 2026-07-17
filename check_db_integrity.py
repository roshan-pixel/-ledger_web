import sqlite3
import json

conn = sqlite3.connect('ledger.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM inventory WHERE c3 LIKE '%TOTAL%'")
row = c.fetchone()
if row:
    print("TOTAL Row:")
    for k in row.keys():
        if row[k]:
            print(f"{k}: {row[k]}")

# Fix invoice item names (standardize 'description' to 'name')
c.execute("SELECT id, items FROM invoices")
invoices = c.fetchall()
for r in invoices:
    items = json.loads(r['items'] or '[]')
    changed = False
    for item in items:
        if 'description' in item and 'name' not in item:
            item['name'] = item['description']
            del item['description']
            changed = True
    if changed:
        c.execute("UPDATE invoices SET items = ? WHERE id = ?", (json.dumps(items), r['id']))

# Enable WAL mode
c.execute("PRAGMA journal_mode=WAL")

conn.commit()
conn.close()
print("DB Integrity check complete.")
