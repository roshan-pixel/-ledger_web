import sqlite3
import json
import datetime
from invoice_api import get_sold_qty_col_idx
from app import update_inventory_formulas, update_totals_row
from init_gsheets import init_google_sheets

def sync_sales_to_inventory(push_to_gsheets=False):
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    all_headers = json.loads(c.fetchone()[0])

    # 1. Zero out all Sold Qty and Sale Value columns
    sold_qty_cols = []
    sale_val_cols = []
    for i, h in enumerate(all_headers):
        if str(h).startswith("Sold Qty"):
            sold_qty_cols.append(i + 1)
        if str(h).startswith("Sale Value"):
            sale_val_cols.append(i + 1)

    print("Zeroing out old sales data...")
    for idx in sold_qty_cols + sale_val_cols:
        c.execute(f"UPDATE inventory SET c{idx} = 0 WHERE UPPER(c3) != 'TOTAL'")

    c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) != 'TOTAL'")
    for row in c.fetchall():
        update_inventory_formulas(conn, row['row_num'], all_headers)
    conn.commit()

    # 2. Iterate all active invoices and apply them
    print("Applying active invoices...")
    c.execute("SELECT * FROM invoices WHERE status != 'cancelled'")
    invoices = c.fetchall()

    for r in invoices:
        date_created = r['date_created']
        items = json.loads(r['items'] or '[]')
        sold_qty_col_idx = get_sold_qty_col_idx(all_headers, date_created)
        
        if sold_qty_col_idx:
            for item in items:
                desc = str(item.get('description') or item.get('name') or '').strip()
                qty_sold = float(item.get('qty', 0))
                
                if desc and qty_sold > 0:
                    norm_desc = desc.replace('\n', ' ').replace(' -', '').strip().upper()
                    c.execute(f"SELECT row_num, c3, c{sold_qty_col_idx} FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
                    for inv_row in c.fetchall():
                        c3_val = str(inv_row['c3']).replace('\n', ' ').replace(' -', '').strip().upper()
                        if c3_val == norm_desc:
                            row_num = inv_row['row_num']
                            current_sold = float(str(inv_row[2] or 0).replace(',', ''))
                            new_sold = current_sold + qty_sold
                            
                            c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (new_sold, row_num))
                            break

    # 3. Recalculate formulas for all rows
    print("Recalculating formulas...")
    c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) != 'TOTAL'")
    for row in c.fetchall():
        update_inventory_formulas(conn, row['row_num'], all_headers)

    update_totals_row(conn)
    conn.commit()
    conn.close()

    if push_to_gsheets:
        init_google_sheets()
    print("Sync sales to inventory done!")

if __name__ == "__main__":
    sync_sales_to_inventory(push_to_gsheets=True)
