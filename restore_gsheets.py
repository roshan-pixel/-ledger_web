import sqlite3
import gspread
import json
import os

def restore_from_gsheets():
    print("Restoring database from Google Sheets...")
    try:
        creds_path = '/etc/secrets/credentials.json' if os.path.exists('/etc/secrets/credentials.json') else 'credentials.json'
        gc = gspread.service_account(filename=creds_path)
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
            
        # 4. Invoices
        try:
            inv_ws = sheet.worksheet('Invoices')
            inv_data = inv_ws.get_all_values()
            if len(inv_data) > 1:
                c.execute("DELETE FROM invoices")
                for row in inv_data[1:]:
                    # ID, Invoice No, DS Code, Customer Name, Amount, Date Created, Items, Status, Total SP
                    while len(row) < 9: row.append('')
                    
                    # Strip leading quote if it was added to prevent formula execution in sheets
                    if row[1] and str(row[1]).startswith("'"):
                        row[1] = str(row[1]).lstrip("'")
                        
                    c.execute("INSERT INTO invoices (id, invoice_no, ds_code, customer_name, amount, date_created, items, status, total_sp) VALUES (?,?,?,?,?,?,?,?,?)", row)
        except Exception as e:
            print("Error restoring Invoices:", e)
            
        conn.commit()
        conn.close()
        print("Restore complete!")
    except Exception as e:
        print("Fatal error in restore:", e)

if __name__ == "__main__":
    restore_from_gsheets()
