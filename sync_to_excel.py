import urllib.request
import json
import win32com.client
import pythoncom
import os

# Once you deploy your app to Render, you will change this to your Render URL.
# For now, it points to your local server for testing.
CLOUD_API_URL = "http://localhost:5000"
EXCEL_PATH = r"C:\Users\sgarm\Downloads\Asclepius_Wellness_PROFESSIONAL.xlsm"

def sync_to_excel():
    print(f"Connecting to Cloud Server at {CLOUD_API_URL}...")
    
    try:
        # Fetch Inventory
        req = urllib.request.Request(f"{CLOUD_API_URL}/api/inventory_master")
        with urllib.request.urlopen(req) as response:
            inventory_data = json.loads(response.read().decode())['data']
            
        # Fetch KPIs
        req = urllib.request.Request(f"{CLOUD_API_URL}/api/kpi")
        with urllib.request.urlopen(req) as response:
            kpi_data = json.loads(response.read().decode())
            
        print("Successfully downloaded latest data from cloud.")
        
        # Open Excel using Windows COM
        pythoncom.CoInitialize()
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = True # Show Excel so user can see it updating
        
        print("Opening Excel file...")
        wb = excel.Workbooks.Open(EXCEL_PATH)
        
        # 1. Update Inventory Master
        print("Syncing Inventory data into Excel...")
        ws_inv = wb.Sheets('Inventory_Master')
        
        # Create a dictionary to easily find rows by Product Name
        inv_dict = {}
        for row in inventory_data:
            # c3 is Product Name in SQLite
            name = row.get('Product Name')
            if name:
                inv_dict[str(name).strip()] = row
                
        # Read Excel rows to find matches and update
        excel_data = ws_inv.Range(ws_inv.Cells(5, 1), ws_inv.Cells(300, 30)).Value
        
        for i, row in enumerate(excel_data):
            name = str(row[2] or "").strip()
            if not name:
                continue
                
            cloud_row = inv_dict.get(name)
            if cloud_row:
                row_idx = i + 5
                
                # Update Sold Qty columns (We can just update the first one: Jul 1-7, which is column 9)
                sold_qty = cloud_row.get('Sold Qty (Jul 1-7)')
                if sold_qty is not None:
                    ws_inv.Cells(row_idx, 9).Value = sold_qty
                    
                # You can extend this to update other columns like DP if needed
        
        # 2. Refresh Dashboard and KPIs
        print("Refreshing Dashboard...")
        # If your Excel has a Refresh macro, we can call it:
        try:
            excel.Application.Run("RefreshDashboard")
        except:
            print("Notice: Could not run RefreshDashboard macro, but data is synced.")
            
        # Save Excel
        wb.Save()
        print("\n✅ SYNC COMPLETE! Your local Excel file is now up to date with the cloud server!")
        
    except Exception as e:
        print(f"\n❌ Error during sync: {str(e)}")
        
    finally:
        try:
            wb.Close(False)
            excel.Quit()
        except:
            pass

if __name__ == "__main__":
    print("====================================")
    print("☁️  NEXUS CLOUD -> EXCEL SYNC TOOL")
    print("====================================")
    sync_to_excel()
    input("\nPress ENTER to close...")
