import sqlite3
import json

restock_items = {
    "LUMITOUCH COMPACT POWDER-BRIGHT LIGHT [410] -": 8,
    "VITMIN B12 TABLET [501]": 12
}

def do_restock():
    from app import get_db, update_inventory_formulas, update_totals_row
    from init_gsheets import init_google_sheets
    
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    all_headers = json.loads(c.fetchone()[0])
    try:
        tot_qty_idx = all_headers.index('Total Qty') + 1
    except:
        tot_qty_idx = 7
        
    for name, qty in restock_items.items():
        norm_name = name.replace('\n', ' ').replace(' -', '').strip().upper()
        
        c.execute(f"SELECT row_num, c3, c{tot_qty_idx} FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
        found = False
        for inv_row in c.fetchall():
            c3_val = str(inv_row['c3']).replace('\n', ' ').replace(' -', '').strip().upper()
            if c3_val == norm_name:
                row_num = inv_row['row_num']
                current_tot = float(str(inv_row[2] or 0).replace(',', ''))
                new_tot = current_tot + qty
                
                c.execute(f"UPDATE inventory SET c{tot_qty_idx}=? WHERE row_num=?", (new_tot, row_num))
                # Now recalculate formulas
                update_inventory_formulas(conn, row_num, all_headers)
                found = True
                print(f"Updated {name}: {current_tot} -> {new_tot}")
                break
        if not found:
            print(f"WARNING: Item not found in DB: {name}")
            
    update_totals_row(conn)
    conn.commit()
    conn.close()
    
    print("Triggering Google Sheets sync...")
    init_google_sheets()
    print("Done!")

if __name__ == '__main__':
    do_restock()
