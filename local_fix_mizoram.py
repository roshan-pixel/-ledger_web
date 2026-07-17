import gspread
import sqlite3
import os

def get_ds_details(conn, ds_code):
    c = conn.cursor()
    c.execute('SELECT ds_name, mobile FROM customers WHERE ds_code = ?', (ds_code,))
    row = c.fetchone()
    if row:
        return {'ds_name': row[0], 'mobile': row[1]}
    
    # Try portal
    try:
        from ds_lookup_api import fetch_ds_from_portal
        portal_data = fetch_ds_from_portal(ds_code)
        if portal_data:
            c.execute('''INSERT INTO customers 
                         (ds_code, ds_name, mobile, address, shipping_address, shipping_mobile, shipping_pincode, last_invoice) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (portal_data['ds_code'], portal_data['ds_name'], portal_data['mobile'], portal_data['address'], 
                       portal_data['shipping_address'], portal_data['shipping_mobile'], portal_data['shipping_pincode'], portal_data['last_invoice']))
            conn.commit()
            return portal_data
    except Exception as e:
        print(f"Error fetching from portal for {ds_code}: {e}")
    return None

def fix_sheet():
    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    gc = gspread.service_account(filename=creds_path)
    sheet = gc.open('MIZORAM BRONZA - 2026')
    ws = sheet.worksheet('Sheet1')
    data = ws.get_all_values()
    
    db_path = os.path.join(os.path.dirname(__file__), 'ledger.db')
    conn = sqlite3.connect(db_path)
    
    sheet_updates = []
    
    for i, row in enumerate(data[1:], start=2): # Skip header
        while len(row) < 15:
            row.append('')
        
        ds_id = str(row[0]).strip()
        ds_name = str(row[1]).strip()
        phone_no = str(row[14]).strip()
        
        if ds_id and (not ds_name or not phone_no or ds_name == '-'):
            print(f"Missing name/phone for {ds_id}, fetching...")
            details = get_ds_details(conn, ds_id)
            if details:
                if not ds_name or ds_name == '-':
                    sheet_updates.append({'range': f'B{i}', 'values': [[details.get('ds_name', ds_name)]] })
                if not phone_no:
                    sheet_updates.append({'range': f'O{i}', 'values': [[details.get('mobile', phone_no)]] })
                    
    if sheet_updates:
        try:
            ws.batch_update(sheet_updates)
            print(f"Updated {len(sheet_updates)} cells in Google Sheets with missing details.")
        except Exception as e:
            print(f"Failed to update Google Sheets: {e}")
    else:
        print("No missing data found.")
        
    conn.close()

if __name__ == '__main__':
    fix_sheet()
