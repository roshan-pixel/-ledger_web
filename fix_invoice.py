import gspread
import json

gc = gspread.service_account(filename='C:/Users/sgarm/Downloads/ledger_web/credentials.json')
sheet = gc.open('Ledger_Database')
inv_ws = sheet.worksheet('Invoices')
data = inv_ws.get_all_values()

# Find row 14
row_idx = None
for i, row in enumerate(data):
    if row[0] == '14':
        row_idx = i + 1  # 1-based index for Google Sheets
        target_row = row
        break

if target_row:
    items = json.loads(target_row[6])
    new_total = 0.0
    new_total_sp = 0.0
    
    for item in items:
        if 'TOSHINE WINTERWEAR' in item['description']:
            item['price'] = "190.00"
            item['unit_sp'] = "0.25"
            item['total_sp'] = "0.50"
            item['total'] = "380.00"
        
        new_total += float(item['total'])
        new_total_sp += float(item['total_sp'])
        
    print(f"Old Amount: {target_row[4]}, New Amount: {new_total:.2f}")
    print(f"Old Total SP: {target_row[8]}, New Total SP: {new_total_sp:.2f}")
    
    # Update the row locally in script to verify
    target_row[6] = json.dumps(items)
    target_row[4] = f"{new_total:.2f}"
    target_row[8] = f"{new_total_sp:.2f}"
    
    # Update Google Sheets
    inv_ws.update(values=[target_row], range_name=f'A{row_idx}:I{row_idx}')
    print("Google Sheets updated successfully!")
