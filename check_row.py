import sqlite3
import json
conn = sqlite3.connect('ledger.db')
c = conn.cursor()
c.execute("SELECT * FROM inventory WHERE row_num IN (197, 203)")
cols = [d[0] for d in c.description]
for r in c.fetchall():
    d = dict(zip(cols, r))
    for k,v in d.items():
        if v and v != '0' and v != 0 and str(v).strip() != '':
            print(f'{k}: {v}')
    print('-'*20)
