import sqlite3
import json

def api_inventory():
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    all_headers = json.loads(c.fetchone()[0])
    
    headers = []
    cols_to_select = []
    for i, h in enumerate(all_headers):
        if h:  # only non-empty headers
            headers.append(h)
            cols_to_select.append(f"c{i+1}")
            
    c.execute(f"SELECT row_num, {', '.join(cols_to_select)} FROM inventory WHERE c3 LIKE '%234%'")
    data = []
    for row in c.fetchall():
        row_data = {}
        for i, header in enumerate(headers):
            row_data[header] = row[cols_to_select[i]]
        data.append(row_data)
        
    print(json.dumps(data, indent=2))

if __name__ == '__main__':
    api_inventory()
