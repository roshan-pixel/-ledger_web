import gspread
import os
from sync_mizoram import sync_mizoram_data

def fix_achieved_status():
    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    gc = gspread.service_account(filename=creds_path)
    sheet = gc.open('MIZORAM BRONZA - 2026')
    ws = sheet.worksheet('Sheet1')
    
    data = ws.get_all_values()
    updates = []
    
    # Iterate through rows and apply the logic
    for r_idx, row in enumerate(data):
        if r_idx == 0:
            continue # Skip header
            
        while len(row) < 15:
            row.append('')
            
        # Helper to check date
        def check_date(d):
            val = str(d).strip().upper()
            if not val or val == '—' or val == 'NONE' or 'NOT' in val or 'ACHIEVED' in val or 'ACHEIVED' in val or val == 'N/A' or val == 'NA':
                return 'NO'
            return 'YES'
            
        # Bronze: col 3 achieved, col 4 date
        bronze_date = row[4]
        new_bronze_ach = check_date(bronze_date)
        if str(row[3]).strip().upper() != new_bronze_ach:
            updates.append({'range': f'D{r_idx + 1}', 'values': [[new_bronze_ach]]})
            
        # Silver: col 6 achieved, col 7 date
        silver_date = row[7]
        new_silver_ach = check_date(silver_date)
        if str(row[6]).strip().upper() != new_silver_ach:
            updates.append({'range': f'G{r_idx + 1}', 'values': [[new_silver_ach]]})
            
        # Gold: col 9 achieved, col 10 date
        gold_date = row[10]
        new_gold_ach = check_date(gold_date)
        if str(row[9]).strip().upper() != new_gold_ach:
            updates.append({'range': f'J{r_idx + 1}', 'values': [[new_gold_ach]]})
            
        # Platinum: col 12 achieved, col 13 date
        plat_date = row[13]
        new_plat_ach = check_date(plat_date)
        if str(row[12]).strip().upper() != new_plat_ach:
            updates.append({'range': f'M{r_idx + 1}', 'values': [[new_plat_ach]]})
            
    if updates:
        print(f"Applying {len(updates)} updates to Google Sheets...")
        ws.batch_update(updates)
        print("Updates applied to Google Sheets.")
    else:
        print("No updates needed.")
        
    print("Syncing to local database...")
    sync_mizoram_data()
    print("Done!")

if __name__ == '__main__':
    fix_achieved_status()
