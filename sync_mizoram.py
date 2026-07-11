import gspread
import sqlite3

def sync_mizoram_data():
    try:
        gc = gspread.service_account(filename='credentials.json')
        sheet = gc.open('MIZORAM BRONZA - 2026')
        ws = sheet.worksheet('Sheet1')
        data = ws.get_all_values()
        
        if len(data) <= 1:
            return
            
        conn = sqlite3.connect('C:/Users/sgarm/Downloads/ledger_web/ledger.db')
        c = conn.cursor()
        
        c.execute('DELETE FROM mizoram_bronze')
        
        for row in data[1:]: # Skip header
            # We need the first 15 columns
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
    except Exception as e:
        print(f"Error syncing Mizoram data: {e}")

if __name__ == '__main__':
    sync_mizoram_data()
