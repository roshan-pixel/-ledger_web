import sqlite3
import json
from pathlib import Path
from invoice_api import get_sold_qty_col_idx
from app import update_inventory_formulas, update_totals_row
from init_gsheets import init_google_sheets

def sync_all_to_inventory():
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    all_headers = json.loads(c.fetchone()[0])

    # Find relevant columns
    sold_qty_cols = []
    sale_val_cols = []
    for i, h in enumerate(all_headers):
        if str(h).startswith("Sold Qty"):
            sold_qty_cols.append(i + 1)
        if str(h).startswith("Sale Value"):
            sale_val_cols.append(i + 1)

    # 1. Zero out 'Total Qty' (c7), 'Gross Value' (c8), and all 'Sold Qty' / 'Sale Value'
    print("Zeroing out inventory data (Total Qty and all Sales)...")
    for idx in [7, 8] + sold_qty_cols + sale_val_cols:
        c.execute(f"UPDATE inventory SET c{idx} = 0 WHERE UPPER(c3) != 'TOTAL'")

    # Pre-fetch inventory rows for fast matching
    c.execute("SELECT row_num, c3 FROM inventory WHERE c3 IS NOT NULL AND UPPER(c3) != 'TOTAL'")
    inv_map = {}
    inv_map_by_id = {}
    import re
    for r in c.fetchall():
        c3_val = str(r['c3'])
        name = c3_val.replace('\n', ' ').replace(' -', '').strip().upper()
        inv_map[name] = r['row_num']
        m = re.search(r'\[(\d+)\]', c3_val)
        if m:
            inv_map_by_id[m.group(1)] = r['row_num']

    # 2. Add Purchases (from purchase_orders.json) to Total Qty (c7)
    print("Applying purchase history...")
    orders_path = Path(__file__).parent / 'purchase_orders.json'
    if orders_path.exists():
        with open(orders_path, 'r', encoding='utf-8') as f:
            purchases = json.load(f)
            for order in purchases:
                for prod in order.get('products', []):
                    if len(prod) >= 5:
                        desc = str(prod[2]).replace('\n', ' ').replace(' -', '').strip().upper()
                        prod_id = str(prod[1]).strip()
                        try:
                            qty = float(str(prod[4]).replace(',', ''))
                        except:
                            qty = 0
                            
                        row_num = None
                        if prod_id in inv_map_by_id:
                            row_num = inv_map_by_id[prod_id]
                        elif desc in inv_map:
                            row_num = inv_map[desc]

                        if qty > 0 and row_num is not None:
                            # Get current c7
                            c.execute("SELECT c7 FROM inventory WHERE row_num=?", (row_num,))
                            curr_c7 = float(str(c.fetchone()[0] or 0).replace(',', ''))
                            c.execute("UPDATE inventory SET c7=? WHERE row_num=?", (curr_c7 + qty, row_num))

    # 3. Add Sales (from ledger.db -> invoices) to Sold Qty
    print("Applying sales history...")
    c.execute("SELECT * FROM invoices WHERE status != 'cancelled'")
    invoices = c.fetchall()

    for r in invoices:
        date_created = r['date_created']
        if not date_created: date_created = "2026-07-09T00:00:00"
        
        items = json.loads(r['items'] or '[]')
        sold_qty_col_idx = get_sold_qty_col_idx(all_headers, date_created)
        
        if sold_qty_col_idx:
            for item in items:
                desc = str(item.get('description') or item.get('name') or '').strip()
                try:
                    qty = float(str(item.get('qty', 0)).replace(',', ''))
                except:
                    qty = 0
                    
                if desc and qty > 0:
                    norm_desc = desc.replace('\n', ' ').replace(' -', '').strip().upper()
                    if norm_desc in inv_map:
                        row_num = inv_map[norm_desc]
                        c.execute(f"SELECT c{sold_qty_col_idx} FROM inventory WHERE row_num=?", (row_num,))
                        curr_sold = float(str(c.fetchone()[0] or 0).replace(',', ''))
                        c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (curr_sold + qty, row_num))

    # 4. Recalculate formulas for all rows
    print("Recalculating formulas...")
    for row_num in inv_map.values():
        update_inventory_formulas(conn, row_num, all_headers)

    update_totals_row(conn)
    conn.commit()
    conn.close()

    print("Sync to Google Sheets...")
    init_google_sheets()
    print("Full Sync Complete!")

if __name__ == "__main__":
    sync_all_to_inventory()
