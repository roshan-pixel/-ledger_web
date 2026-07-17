import sqlite3

def add_product():
    conn = sqlite3.connect('ledger.db')
    c = conn.cursor()
    c.execute("SELECT MAX(CAST(c2 AS INTEGER)) FROM inventory WHERE c2 != '' AND c3 != 'TOTAL'")
    max_sno = c.fetchone()[0] or 0
    sno = max_sno + 1
    
    prod_name = "BATHVEDA GLYCERIN NATURAL OIL BAR [235]"
    
    # Check if already exists
    c.execute("SELECT row_num FROM inventory WHERE c3 = ?", (prod_name,))
    if c.fetchone():
        print("Product already exists.")
        conn.close()
        return

    # Create empty dict for all 30 cols
    cols = [f"c{i}" for i in range(1, 31)]
    vals = [""] * 30
    
    # set values
    vals[1] = str(sno)
    vals[2] = prod_name
    vals[3] = "34011110" # c4
    vals[4] = "157.04"   # c5
    vals[6] = "12"       # c7
    
    placeholders = ",".join(["?"] * 30)
    col_str = ",".join(cols)
    
    c.execute(f"INSERT INTO inventory ({col_str}) VALUES ({placeholders})", vals)
    conn.commit()
    conn.close()
    
    print("Product added.")
    
    from app import update_inventory_formulas, update_totals_row
    from app import get_db
    conn = get_db()
    update_inventory_formulas(conn)
    update_totals_row(conn)
    conn.commit()
    conn.close()
    
if __name__ == "__main__":
    add_product()
