import gspread

gc = gspread.service_account(filename='C:/Users/sgarm/Downloads/ledger_web/credentials.json')
sheet = gc.open('Ledger_Database')
inv_ws = sheet.worksheet('Inventory')
data = inv_ws.get_all_values()

headers = data[0]
header_map = {h: i for i, h in enumerate(headers) if h}

for i, row in enumerate(data):
    if i == 0: continue
    if len(row) > 2 and '252' in row[2]:
        price = float(row[header_map['Price/Pc (Rs.)']] or 0)
        sp_pc = float(row[header_map['SP/Pc']] or 0)
        total_qty = float(row[header_map['Total Qty']] or 0)
        
        sold_1_7 = float(row[header_map['Sold Qty (Jul 1-7)']] or 0)
        sold_8_14 = float(row[header_map['Sold Qty (Jul 8-14)']] or 0)
        sold_15_21 = float(row[header_map['Sold Qty (Jul 15-21)']] or 0)
        sold_22_28 = float(row[header_map['Sold Qty (Jul 22-28)']] or 0)
        sold_29_31 = float(row[header_map['Sold Qty (Jul 29-31)']] or 0)
        
        # Calculate sale values
        row[header_map['Sale Value (Jul 1-7)']] = str(sold_1_7 * price)
        row[header_map['Sale Value (Jul 8-14)']] = str(sold_8_14 * price)
        row[header_map['Sale Value (Jul 15-21)']] = str(sold_15_21 * price)
        row[header_map['Sale Value (Jul 22-28)']] = str(sold_22_28 * price)
        row[header_map['Sale Value (Jul 29-31)']] = str(sold_29_31 * price)
        
        # Remaining Qty & Value
        rem_qty = total_qty - (sold_1_7 + sold_8_14 + sold_15_21 + sold_22_28 + sold_29_31)
        row[header_map['Remaining Qty']] = str(rem_qty)
        row[header_map['Remaining Value (Rs.)']] = str(rem_qty * price)
        
        # Gross Value
        row[header_map['Gross Value (Rs.)']] = str(total_qty * price)
        
        # Sales %
        sales_pct = (total_qty - rem_qty) / total_qty if total_qty > 0 else 0
        row[header_map['Sales %']] = str(sales_pct)
        
        # Total SP
        row[header_map['Total SP']] = str(rem_qty * sp_pc)
        
        # Update row in Google Sheets
        inv_ws.update(values=[row], range_name=f'A{i+1}:AD{i+1}')
        print(f"Updated calculations for TOSHINE: Remaining Qty = {rem_qty}")
        break
