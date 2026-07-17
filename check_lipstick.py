import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
import json
headers = json.loads(c.fetchone()[0])
print(f"Headers: {headers}")

c.execute("SELECT * FROM inventory WHERE c3 LIKE '%LUXE MATTE LIQUID LIPSTICK%HALEN%' OR c3 LIKE '%HALEN%'")
rows = c.fetchall()

if not rows:
    print("Product not found.")
else:
    for row in rows:
        print(f"Row {row[0]}:")
        for i, val in enumerate(row):
            if i > 0 and i-1 < len(headers):
                print(f"  {headers[i-1]}: {val}")
            else:
                print(f"  c{i}: {val}")
conn.close()
