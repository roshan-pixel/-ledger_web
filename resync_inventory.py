import sqlite3
import json
from app import update_inventory_formulas, update_totals_row
from invoice_api import get_sold_qty_col_idx

def fix_inventory():
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Zero out all 'Sold Qty' columns in inventory
    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    all_headers = json.loads(c.fetchone()[0])
    sold_qty_cols = []
    for i, h in enumerate(all_headers):
        if str(h).startswith("Sold Qty"):
            sold_qty_cols.append(i + 1)

    for col_idx in sold_qty_cols:
        c.execute(f"UPDATE inventory SET c{col_idx} = 0")

    # 2. Iterate through all active invoices
    c.execute("SELECT * FROM invoices WHERE status != 'cancelled'")
    invoices = c.fetchall()

    for inv in invoices:
        items = json.loads(inv['items'] or '[]')
        date_created = inv['date_created']
        
        # fix missing date_created just in case
        if not date_created: 
            date_created = "2026-07-09T00:00:00"
            
        sold_qty_col_idx = get_sold_qty_col_idx(all_headers, date_created)
        
        # Fix the items json to use 'description' if it has 'name'
        needs_update = False
        for item in items:
            if 'name' in item and 'description' not in item:
                item['description'] = item['name']
                needs_update = True
        
        if needs_update:
            c.execute("UPDATE invoices SET items = ? WHERE id = ?", (json.dumps(items), inv['id']))
            
        if not sold_qty_col_idx: continue
        
        for item in items:
            desc = item.get('description', item.get('name', '')).strip()
            qty = float(item.get('qty', 0))
            
            if desc and qty > 0:
                c.execute("SELECT row_num, c{} FROM inventory WHERE c3=?".format(sold_qty_col_idx), (desc,))
                inv_row = c.fetchone()
                if inv_row:
                    row_num = inv_row['row_num']
                    current_sold = float(inv_row[1] or 0)
                    new_sold = current_sold + qty
                    c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (new_sold, row_num))

    # 3. Recalculate formulas for all rows
    c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) != 'TOTAL' AND c3 != '' AND c3 IS NOT NULL")
    rows = c.fetchall()
    for row in rows:
        update_inventory_formulas(conn, row['row_num'], all_headers)
        
    # 4. Update the TOTAL row
    update_totals_row(conn)

    conn.commit()
    conn.close()
    print("Inventory completely re-synced based on active invoices!")

if __name__ == '__main__':
    fix_inventory()
