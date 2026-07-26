import sqlite3
import json
import re
from pathlib import Path
from invoice_api import get_sold_qty_col_idx
from app import update_inventory_formulas, update_totals_row
from init_gsheets import init_google_sheets

def extract_code(text):
    # Try to find [123]
    m = re.search(r'\[(\d+)\]', text)
    if m: return m.group(1)
    
    # Try to find 123 at the end of the string (e.g. OMEGADOC CAPSULE     492)
    m = re.search(r'\s+(\d+)$', text.strip())
    if m: return m.group(1)
    
    return None

def sync_all_to_inventory():
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    all_headers = json.loads(c.fetchone()[0])

    sold_qty_cols = []
    sale_val_cols = []
    for i, h in enumerate(all_headers):
        if str(h).startswith("Sold Qty"):
            sold_qty_cols.append(i + 1)
        if str(h).startswith("Sale Value"):
            sale_val_cols.append(i + 1)

    print("Zeroing out inventory data (Total Qty and all Sales)...")
    for idx in [7, 8] + sold_qty_cols + sale_val_cols:
        c.execute(f"UPDATE inventory SET c{idx} = 0 WHERE UPPER(c3) != 'TOTAL'")

    c.execute("SELECT row_num, c3 FROM inventory WHERE c3 IS NOT NULL AND UPPER(c3) != 'TOTAL'")
    inv_map_by_code = {}
    inv_map_by_name = {}
    for r in c.fetchall():
        name = str(r['c3'])
        code = extract_code(name)
        norm_name = re.sub(r'\[\d+\]', '', name).replace('-', '').strip().upper()
        norm_name = re.sub(r'\s+', ' ', norm_name)
        
        if code:
            inv_map_by_code[code] = r['row_num']
        inv_map_by_name[norm_name] = r['row_num']

    print("Applying purchase history...")
    orders_path = Path(__file__).parent / 'purchase_orders.json'
    if orders_path.exists():
        with open(orders_path, 'r', encoding='utf-8') as f:
            purchases = json.load(f)
            for order in purchases:
                for prod in order.get('products', []):
                    if len(prod) >= 5:
                        code = str(prod[1]).strip()
                        raw_name = str(prod[2]).replace('\n', ' ').strip().upper()
                        norm_name = re.sub(r'\s+', ' ', raw_name)
                        try:
                            qty = float(str(prod[4]).replace(',', ''))
                        except:
                            qty = 0
                            
                        if qty > 0:
                            row_num = inv_map_by_code.get(code) or inv_map_by_name.get(norm_name)
                            if row_num:
                                c.execute("SELECT c7 FROM inventory WHERE row_num=?", (row_num,))
                                curr = float(str(c.fetchone()[0] or 0).replace(',', ''))
                                c.execute("UPDATE inventory SET c7=? WHERE row_num=?", (curr + qty, row_num))

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
                    code = extract_code(desc)
                    norm_name = re.sub(r'\[\d+\]', '', desc).replace('-', '').strip().upper()
                    norm_name = re.sub(r'\s+\d+$', '', norm_name)
                    norm_name = re.sub(r'\s+', ' ', norm_name)
                    
                    row_num = None
                    if code and code in inv_map_by_code:
                        row_num = inv_map_by_code[code]
                    elif norm_name in inv_map_by_name:
                        row_num = inv_map_by_name[norm_name]
                        
                    if row_num:
                        c.execute(f"SELECT c{sold_qty_col_idx} FROM inventory WHERE row_num=?", (row_num,))
                        curr = float(str(c.fetchone()[0] or 0).replace(',', ''))
                        c.execute(f"UPDATE inventory SET c{sold_qty_col_idx}=? WHERE row_num=?", (curr + qty, row_num))

    print("Recalculating formulas...")
    c.execute("SELECT row_num FROM inventory WHERE c3 IS NOT NULL AND UPPER(c3) != 'TOTAL'")
    for row in c.fetchall():
        update_inventory_formulas(conn, row['row_num'], all_headers)

    update_totals_row(conn)
    conn.commit()
    conn.close()

    print("Syncing to Google Sheets...")
    init_google_sheets()
    print("Robust Sync Complete!")

if __name__ == "__main__":
    sync_all_to_inventory()
