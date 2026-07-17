import gspread

gc = gspread.service_account(filename='C:/Users/sgarm/Downloads/ledger_web/credentials.json')
sheet = gc.open('Ledger_Database')
inv_ws = sheet.worksheet('Inventory')
data = inv_ws.get_all_values()

# Find headers
headers = data[0]
qty_col_idx = headers.index('Sold Qty (Jul 8-14)')

row_to_update = None
for i, row in enumerate(data):
    if len(row) > 2 and '252' in row[2]:
        row_to_update = i
        break

if row_to_update:
    current_val = data[row_to_update][qty_col_idx]
    current_val = float(current_val) if current_val else 0.0
    new_val = current_val + 2.0
    
    # Update Google sheets (row index is 1-based in gspread)
    inv_ws.update_cell(row_to_update + 1, qty_col_idx + 1, str(new_val))
    print(f"Updated TOSHINE sold qty from {current_val} to {new_val}")
