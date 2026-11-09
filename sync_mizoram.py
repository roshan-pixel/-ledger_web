import gspread
import sqlite3
import json
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
            phone_no TEXT,
            emerald_commission TEXT DEFAULT "",
            emerald_achieved TEXT DEFAULT "",
            emerald_update_date TEXT DEFAULT ""
        )''')
        # Migrate existing tables that predate Emerald columns
        for col in ('emerald_commission', 'emerald_achieved', 'emerald_update_date'):
            try:
                c.execute(f'ALTER TABLE mizoram_bronze ADD COLUMN {col} TEXT DEFAULT ""')
            except Exception:
                pass
        
        # Clear existing data
        c.execute('DELETE FROM mizoram_bronze')
        
        # Insert new data
        for row in data[1:]: # Skip header
            while len(row) < 15:
                row.append('')
            clean_row = [str(x).strip() for x in row[:15]]
            if not clean_row[0] and not clean_row[1]:
                continue # Skip blank placeholder rows
            
            c.execute('''INSERT INTO mizoram_bronze 
                (ds_id, ds_name, bronze_commission, bronze_achieved, mizoram_bronze_date, 
                 silver_commission, silver_achieved, silver_update_date, gold_commission, 
                 gold_achieved, gold_update_date, platinum_commission, platinum_achieved, 
                 platinum_update_date, phone_no) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', clean_row)
                 
        conn.commit()

        # Apply manual overrides that must survive Sheet syncs
        overrides_path = os.path.join(os.path.dirname(__file__), 'data', 'mizoram_overrides.json')
        if os.path.exists(overrides_path):
            with open(overrides_path, encoding='utf-8') as f:
                overrides = json.load(f)

            # Update existing rows
            for upd in overrides.get('updates', []):
                af = upd['achieved_field']
                df = upd['date_field']
                # Only update if the field value hasn't been manually changed to something newer
                c.execute(
                    f'UPDATE mizoram_bronze SET {af}=?, {df}=? WHERE ds_id=?',
                    ('YES', upd['date'], upd['ds_id'].upper())
                )

            # Insert new members not in the Sheet
            for ins in overrides.get('inserts', []):
                ds_id = ins.get('ds_id', '').upper()
                c.execute('SELECT id FROM mizoram_bronze WHERE ds_id=?', (ds_id,))
                if not c.fetchone():
                    c.execute('''INSERT INTO mizoram_bronze
                        (ds_id, ds_name, bronze_commission, bronze_achieved, mizoram_bronze_date,
                         silver_commission, silver_achieved, silver_update_date, gold_commission,
                         gold_achieved, gold_update_date, platinum_commission, platinum_achieved,
                         platinum_update_date, phone_no, emerald_commission, emerald_achieved, emerald_update_date)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (ds_id, ins.get('ds_name',''), ins.get('bronze_commission','1399'),
                         ins.get('bronze_achieved','YES'), ins.get('mizoram_bronze_date',''),
                         '','','','','','','','','','',
                         ins.get('emerald_commission',''), ins.get('emerald_achieved',''), ins.get('emerald_update_date','')))

            conn.commit()
            print(f"Applied {len(overrides.get('updates',[]))} updates and {len(overrides.get('inserts',[]))} inserts from mizoram_overrides.json")

        conn.close()
        print(f"Successfully synced {len(data)-1} rows from MIZORAM BRONZA - 2026.")
        return True
    except Exception as e:
        print(f"Error syncing Mizoram data: {e}")
        return False

if __name__ == '__main__':
    sync_mizoram_data()
