import sqlite3
import json
import datetime
import gspread

def update_inventory_formulas(conn, row_num, headers):
    """Recalculate formulas for a row."""
    c = conn.cursor()
    c.execute("SELECT * FROM inventory WHERE row_num=?", (row_num,))
    row = c.fetchone()
    if not row or str(row['c3']).upper() == 'TOTAL':
        return
        
    try:
        try:
            dp_idx = headers.index('Price/Pc (Rs.)') + 1
            tot_qty_idx = headers.index('Total Qty') + 1
            gross_val_idx = headers.index('Gross Value (Rs.)') + 1
            rem_qty_idx = headers.index('Remaining Qty') + 1
            rem_val_idx = headers.index('Remaining Value (Rs.)') + 1
        except ValueError:
            dp_idx = 5
            tot_qty_idx = 7
            gross_val_idx = 8
            rem_qty_idx = 19
            rem_val_idx = 20
            
        dp = float(str(row[f'c{dp_idx}']).replace(',', '') or 0)
        avail_stock = float(str(row[f'c{tot_qty_idx}']).replace(',', '') or 0)
        
        # update Gross Value
        gross_val = avail_stock * dp
        c.execute(f"UPDATE inventory SET c{gross_val_idx}=? WHERE row_num=?", (gross_val, row_num))
            
        # sum sold qtys and update sale values
        total_sold = 0
        for i, h in enumerate(headers):
            if str(h).startswith("Sold Qty"):
                qty_col = f"c{i+1}"
                val_col = f"c{i+2}"
                qty = float(str(row[qty_col]).replace(',', '') or 0)
                total_sold += qty
                sale_val = qty * dp
                c.execute(f"UPDATE inventory SET c{i+2}=? WHERE row_num=?", (sale_val, row_num))
                
        rem_qty = avail_stock - total_sold
        rem_val = rem_qty * dp
        
        # Calculate Total SP
        try:
            sp_pc_idx = headers.index('SP/Pc') + 1
            tot_sp_idx = headers.index('Total SP') + 1
            sp_val = row[f'c{sp_pc_idx}']
            sp_pc = float(str(sp_val).replace(',', '') if sp_val not in (None, '', 'None') else 0)
            tot_sp = sp_pc * rem_qty
        except ValueError:
            # If headers not found, fallback to c27 and c28
            sp_val = row['c27']
            sp_pc = float(str(sp_val).replace(',', '') if sp_val not in (None, '', 'None') else 0)
            tot_sp = sp_pc * rem_qty
            tot_sp_idx = 28
            
        c.execute(f"UPDATE inventory SET c{rem_qty_idx}=?, c{rem_val_idx}=?, c{tot_sp_idx}=? WHERE row_num=?",
                  (rem_qty, rem_val, tot_sp, row_num))
    except Exception as e:
        print("Error updating formulas:", e)

def update_totals_row(conn):
    """Recalculate the TOTAL row at the bottom."""
    try:
        c = conn.cursor()
        c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) = 'TOTAL'")
        total_row = c.fetchone()
        if not total_row:
            return
        
        row_id = total_row['row_num']
        
        # Sum columns 6 through 20, and 28 (Total SP)
        sums = {}
        cols_to_sum = list(range(6, 21)) + [28]
        for col_idx in cols_to_sum:
            c.execute(f"SELECT SUM(CAST(REPLACE(c{col_idx}, ',', '') AS REAL)) FROM inventory WHERE UPPER(c3) != 'TOTAL' AND c{col_idx} != ''")
            s = c.fetchone()[0] or 0
            sums[f"c{col_idx}"] = s
            
        # Update the total row
        updates = ", ".join([f"{k}=?" for k in sums.keys()])
        values = list(sums.values()) + [row_id]
        c.execute(f"UPDATE inventory SET {updates} WHERE row_num=?", values)
    except Exception as e:
        print("Error updating totals row:", e)


# 1. Connect to local DB and get invoices
import os
db_path = os.path.join(os.path.dirname(__file__), 'ledger.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT date_created, items, status FROM invoices WHERE status != 'cancelled'")
invoices = c.fetchall()

# 2. Get headers to find Sold Qty columns
c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
all_headers = json.loads(c.fetchone()[0])
sold_cols = []
for i, h in enumerate(all_headers):
    if str(h).startswith("Sold Qty"):
        sold_cols.append(i + 1)

# Initialize sales map
sales_map = {} # product_name -> {col_idx: qty}

for inv in invoices:
    date_str = inv[0]
    items = json.loads(inv[1] or '[]')
    
    # Parse date
    try:
        # Special one-time exemption for 30/06/2026
        if date_str and date_str.startswith('30/06/2026'):
            day = 1
        elif 'T' in date_str:
            dt = datetime.datetime.fromisoformat(date_str)
            day = dt.day
        elif '/' in date_str:
            dt = datetime.datetime.strptime(date_str[:10], '%d/%m/%Y')
            day = dt.day
        else:
            dt = datetime.datetime.strptime(date_str[:10], '%Y-%m-%d')
            day = dt.day
    except:
        day = datetime.datetime.now().day
        
    if day <= 7: week_idx = 0
    elif day <= 14: week_idx = 1
    elif day <= 21: week_idx = 2
    elif day <= 28: week_idx = 3
    else: week_idx = 4
    
    col_idx = sold_cols[week_idx] if week_idx < len(sold_cols) else sold_cols[-1]
    
    for item in items:
        desc = str(item.get('description') or item.get('name') or '').replace(' -', '').strip().upper()
        qty = float(item.get('qty', 0))
        if desc and qty > 0:
            if desc not in sales_map:
                sales_map[desc] = {}
            sales_map[desc][col_idx] = sales_map[desc].get(col_idx, 0.0) + qty

# 3. Update SQLite Database
c.execute("SELECT row_num, c3 FROM inventory WHERE c3 IS NOT NULL AND c3 != ''")
inventory = c.fetchall()

for row_num, c3 in inventory:
    name = c3.replace(' -', '').strip().upper()
    
    # Zero out all sold cols first
    for col_idx in sold_cols:
        c.execute(f"UPDATE inventory SET c{col_idx}=0.0 WHERE row_num=?", (row_num,))
        
    # Update with new values
    if name in sales_map:
        for col_idx, qty in sales_map[name].items():
            c.execute(f"UPDATE inventory SET c{col_idx}=? WHERE row_num=?", (qty, row_num))

# Update formulas for all rows
for row_num, _ in inventory:
    update_inventory_formulas(conn, row_num, all_headers)

# Update Totals Row
update_totals_row(conn)
conn.commit()
print("Local database updated successfully!")

# 4. Push Inventory changes to Google Sheets
creds_path = '/etc/secrets/credentials.json' if os.path.exists('/etc/secrets/credentials.json') else os.path.join(os.path.dirname(__file__), 'credentials.json')
if not os.path.exists(creds_path):
    print("No credentials.json found, skipping Sheets update.")
else:
    gc = gspread.service_account(filename=creds_path)
    sheet = gc.open('Ledger_Database')
inv_ws = sheet.worksheet('Inventory')

# Fetch all inventory to push (must use fresh cursor to avoid Row objects messing up the list)
conn.row_factory = None
c2 = conn.cursor()
c2.execute("SELECT * FROM inventory ORDER BY row_num ASC")
local_inv = c2.fetchall()

# Reconstruct grid
grid = []
grid.append(all_headers)
for row in local_inv:
    # Google sheets update requires strings/floats, replace None with empty string
    safe_row = [val if val is not None else '' for val in row[1:]]
    grid.append(safe_row)

    inv_ws.clear()
    inv_ws.update(values=grid, range_name='A1')
    print("Google Sheets updated successfully!")
