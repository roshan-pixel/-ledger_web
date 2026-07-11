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

def sync_mizoram_data():
    try:
        # Load credentials
        creds_path = '/etc/secrets/credentials.json' if os.path.exists('/etc/secrets/credentials.json') else os.path.join(os.path.dirname(__file__), 'credentials.json')
        if not os.path.exists(creds_path):
            print("No credentials.json found.")
            return False
            
        gc = gspread.service_account(filename=creds_path)
        sheet = gc.open('MIZORAM BRONZA - 2026')
        ws = sheet.worksheet('Sheet1')
        data = ws.get_all_values()
        
        if len(data) <= 1:
            print("No data in sheet.")
            return False
            
        db_path = os.path.join(os.path.dirname(__file__), 'ledger.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS mizoram_bronze (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ds_id TEXT,
            ds_name TEXT,
            bronze_commission TEXT,
            bronze_achieved TEXT,
            mizoram_bronze_date TEXT,
            silver_commission TEXT,
            silver_achieved TEXT,
            silver_update_date TEXT,
            gold_commission TEXT,
            gold_achieved TEXT,
            gold_update_date TEXT,
            platinum_commission TEXT,
            platinum_achieved TEXT,
            platinum_update_date TEXT,
            phone_no TEXT
        )''')
        
        c.execute('DELETE FROM mizoram_bronze')
        
        sheet_updates = []
        
        # Insert new data
        for i, row in enumerate(data[1:], start=2): # Skip header
            while len(row) < 15:
                row.append('')
            clean_row = row[:15]
            
            ds_id = str(clean_row[0]).strip()
            ds_name = str(clean_row[1]).strip()
            phone_no = str(clean_row[14]).strip()
            
            if ds_id and (not ds_name or not phone_no or ds_name == '-'):
                print(f"Missing name/phone for {ds_id}, fetching...")
                details = get_ds_details(conn, ds_id)
                if details:
                    if not ds_name or ds_name == '-':
                        clean_row[1] = details.get('ds_name', ds_name)
                    if not phone_no:
                        clean_row[14] = details.get('mobile', phone_no)
                        
                    # Update google sheets via batch later
                    sheet_updates.append({'range': f'B{i}', 'values': [[clean_row[1]]] })
                    sheet_updates.append({'range': f'O{i}', 'values': [[clean_row[14]]] })
            
            c.execute('''INSERT INTO mizoram_bronze 
                (ds_id, ds_name, bronze_commission, bronze_achieved, mizoram_bronze_date, 
                 silver_commission, silver_achieved, silver_update_date, gold_commission, 
                 gold_achieved, gold_update_date, platinum_commission, platinum_achieved, 
                 platinum_update_date, phone_no) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', clean_row)
                 
        conn.commit()
        conn.close()
        
        # Batch update google sheets if any missing data was found
        if sheet_updates:
            try:
                ws.batch_update(sheet_updates)
                print(f"Updated {len(sheet_updates)} cells in Google Sheets with missing details.")
            except Exception as e:
                print(f"Failed to update Google Sheets: {e}")
                
        print(f"Successfully synced {len(data)-1} rows from MIZORAM BRONZA - 2026.")
        return True
    except Exception as e:
        print(f"Error syncing Mizoram data: {e}")
        return False

if __name__ == '__main__':
    sync_mizoram_data()
