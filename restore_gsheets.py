import sqlite3
import gspread
import json

def restore_from_gsheets():
    print("Restoring database from Google Sheets...")
    try:
        gc = gspread.service_account(filename='credentials.json')
        sheet = gc.open('Ledger_Database')
        
        conn = sqlite3.connect('ledger.db')
        c = conn.cursor()
        
        # 1. Customers
        try:
            cust_ws = sheet.worksheet('Customers')
            cust_data = cust_ws.get_all_values()
            if len(cust_data) > 1:
                c.execute("DELETE FROM customers")
                for row in cust_data[1:]:
                    # Pad if necessary
                    while len(row) < 8: row.append('')
                    c.execute("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?)", row)
        except Exception as e:
            print("Error restoring customers:", e)
            
        # 2. Inventory
        try:
            inv_ws = sheet.worksheet('Inventory')
            inv_data = inv_ws.get_all_values()
            if len(inv_data) > 1:
                c.execute("DELETE FROM inventory")
                headers = inv_data[0]
                for idx, row in enumerate(inv_data[1:]):
                    while len(row) < len(headers):
                        row.append('')
                    
                    cols = ', '.join([f'c{i+1}' for i in range(len(headers))])
                    placeholders = ', '.join(['?'] * len(headers))
                    
                    c.execute(f"INSERT INTO inventory (row_num, {cols}) VALUES (?, {placeholders})", [idx+1] + row)
        except Exception as e:
            print("Error restoring inventory:", e)
            
        # 3. KPIs
        try:
            kpi_ws = sheet.worksheet('KPIs')
            kpi_data = kpi_ws.get_all_values()
            if len(kpi_data) > 1:
                c.execute("DELETE FROM kpis")
                for row in kpi_data[1:]:
                    while len(row) < 2: row.append('')
                    c.execute("INSERT INTO kpis VALUES (?,?)", row)
        except Exception as e:
            print("Error restoring KPIs:", e)
            
        conn.commit()
        conn.close()
        print("Restore complete!")
    except Exception as e:
        print("Fatal error in restore:", e)

if __name__ == "__main__":
    restore_from_gsheets()
