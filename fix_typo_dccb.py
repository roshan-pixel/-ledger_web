import gspread
import os

def fix_and_fetch():
    creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
    gc = gspread.service_account(filename=creds_path)
    sheet = gc.open('MIZORAM BRONZA - 2026')
    ws = sheet.worksheet('Sheet1')
    data = ws.get_all_values()

    updates = []
    for i, row in enumerate(data[1:], start=2):
        while len(row) < 15:
            row.append('')
        ds_id = str(row[0]).strip()
        # Fix typo: DCCB8COE -> DCCB8C0E (letter O -> digit 0)
        if ds_id == 'DCCB8COE':
            print(f"Row {i}: Fixing typo DCCB8COE -> DCCB8C0E")
            updates.append({'range': f'A{i}', 'values': [['DCCB8C0E']]})
            row[0] = 'DCCB8C0E'
            ds_id = 'DCCB8C0E'

        if ds_id == 'DCCB8C0E':
            ds_name = str(row[1]).strip()
            phone_no = str(row[14]).strip()
            if not ds_name or not phone_no or ds_name == '-':
                print(f"Fetching details for {ds_id}...")
                try:
                    from ds_lookup_api import fetch_ds_from_portal
                    portal_data = fetch_ds_from_portal(ds_id)
                    if portal_data:
                        print(f"  Name: {portal_data['ds_name']}, Phone: {portal_data['mobile']}")
                        if not ds_name or ds_name == '-':
                            updates.append({'range': f'B{i}', 'values': [[portal_data['ds_name']]]})
                        if not phone_no:
                            updates.append({'range': f'O{i}', 'values': [[portal_data['mobile']]]})
                    else:
                        print(f"  No data found for {ds_id} in portal.")
                except Exception as e:
                    print(f"  Error: {e}")

    if updates:
        ws.batch_update(updates)
        print(f"Updated {len(updates)} cells in Google Sheets.")
    else:
        print("No updates needed.")

if __name__ == '__main__':
    fix_and_fetch()
