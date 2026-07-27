import sqlite3

conn = sqlite3.connect('ledger.db')
c = conn.cursor()

print('Checking current remaining stock for 503 and 510...')
c.execute("SELECT c3, c19 FROM inventory WHERE c2 IN ('503', '510') OR UPPER(c3) LIKE '%CALCIUM%' OR UPPER(c3) LIKE '%DAYLIFT%'")
for r in c.fetchall():
    print(r)

print('Checking if any item has negative remaining stock...')
c.execute("SELECT c2, c3, c19 FROM inventory")
for r in c.fetchall():
    try:
        qty = float(str(r[2]).replace(',', ''))
        if qty < 0:
            print(f"Negative stock found: {r[0]} | {r[1]} = {r[2]}")
    except:
        pass

conn.close()
