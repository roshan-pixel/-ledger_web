import sqlite3

def add_product():
    conn = sqlite3.connect('ledger.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Find the TOTAL row
    c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) = 'TOTAL'")
    total_row = c.fetchone()
    if total_row:
        total_row_num = total_row['row_num']
    else:
        total_row_num = 219 # Fallback
        
    # 2. Shift TOTAL row down by 1
    new_total_row_num = total_row_num + 1
    c.execute("UPDATE inventory SET row_num = ? WHERE row_num = ?", (new_total_row_num, total_row_num))
    
    # 3. Insert the new product at the old total_row_num
    # c1 to c30
    c1 = ''
    c2 = str(total_row_num)
    c3 = 'BATHVEDA GLYCERIN NATURAL OIL BAR [235] -'
    c4 = '34011110'
    c5 = '157.04'
    c6 = '1'
    c7 = '12.0'
    c8 = str(12.0 * 157.04) # 1884.48
    c9 = '0.0'
    c10 = '0.0'
    c11 = '0.0'
    c12 = '0.0'
    c13 = '0.0'
    c14 = '0.0'
    c15 = '0.0'
    c16 = '0.0'
    c17 = '0.0'
    c18 = '0.0'
    c19 = '12.0'
    c20 = c8
    c21 = ''
    c22 = ''
    c23 = ''
    c24 = ''
    c25 = ''
    c26 = ''
    c27 = '157.04' # SP/Pc (guessing same as DP or close)
    c28 = c8
    c29 = None
    c30 = None
    
    c.execute('''
        INSERT INTO inventory 
        (row_num, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (total_row_num, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11, c12, c13, c14, c15, c16, c17, c18, c19, c20, c21, c22, c23, c24, c25, c26, c27, c28, c29, c30))
    
    conn.commit()
    
    # 4. Update the TOTAL row values
    from app import update_totals_row
    update_totals_row(conn)
    conn.commit()
    conn.close()
    
    # 5. Sync to GSheets
    from init_gsheets import init_google_sheets
    init_google_sheets()
    print("Added new product successfully!")

if __name__ == "__main__":
    add_product()
