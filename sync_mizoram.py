import gspread
import sqlite3
import os

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
        
        # Create table if not exists
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
        
        # Clear existing data
        c.execute('DELETE FROM mizoram_bronze')
        
        # Insert new data
        for row in data[1:]: # Skip header
            while len(row) < 15:
                row.append('')
            clean_row = row[:15]
            
            c.execute('''INSERT INTO mizoram_bronze 
                (ds_id, ds_name, bronze_commission, bronze_achieved, mizoram_bronze_date, 
                 silver_commission, silver_achieved, silver_update_date, gold_commission, 
                 gold_achieved, gold_update_date, platinum_commission, platinum_achieved, 
                 platinum_update_date, phone_no) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', clean_row)
                 
        conn.commit()
        conn.close()
        print(f"Successfully synced {len(data)-1} rows from MIZORAM BRONZA - 2026.")
        return True
    except Exception as e:
        print(f"Error syncing Mizoram data: {e}")
        return False

if __name__ == '__main__':
    sync_mizoram_data()
