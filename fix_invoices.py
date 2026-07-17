import gspread
import json
gc = gspread.service_account(filename='credentials.json')
sheet = gc.open('Ledger_Database')
inv_ws = sheet.worksheet('Invoices')
data = inv_ws.get_all_values()
if not data: exit()
headers = data[0]
rows = data[1:]
items_col_idx = headers.index('Items')
inv_no_col_idx = headers.index('Invoice No')
fixed_rows = []
count = 0
for r in rows:
    new_r = list(r)
    # Fix newline bug
    if '\n' in new_r[items_col_idx]:
        new_r[items_col_idx] = new_r[items_col_idx].replace('\n', ' ')
        count += 1
    # Fix quote accumulation
    if new_r[inv_no_col_idx].startswith("'"):
        new_r[inv_no_col_idx] = "'" + new_r[inv_no_col_idx].lstrip("'")
        count += 1
    fixed_rows.append(new_r)
if count > 0:
    inv_ws.clear()
    inv_ws.update(values=[headers] + fixed_rows, range_name='A1')
    print(f'Fixed invoices in Google Sheets')
