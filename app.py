import os
import pythoncom
import win32com.client
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
EXCEL_PATH = r'C:\Users\sgarm\Downloads\Asclepius_Wellness_PROFESSIONAL.xlsm'

def get_excel():
    pythoncom.CoInitialize()
    try:
        excel = win32com.client.GetActiveObject("Excel.Application")
    except:
        excel = win32com.client.Dispatch("Excel.Application")
    
    wb = None
    for open_wb in excel.Workbooks:
        if open_wb.Name == 'Asclepius_Wellness_PROFESSIONAL.xlsm':
            wb = open_wb
            break
            
    if not wb:
        wb = excel.Workbooks.Open(EXCEL_PATH)
        
    return excel, wb

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/kpi')
def api_kpi():
    excel, wb = get_excel()
    try:
        ws = wb.Sheets('_KPI_Data')
        kpis = {}
        for r in range(2, 17):
            key = ws.Cells(r, 1).Value
            val = ws.Cells(r, 2).Value
            if key:
                kpis[str(key)] = val
        
        ws_dash = wb.Sheets('Dashboard')
        period = ws_dash.Cells(2, 8).Value
        kpis['Reporting Period'] = str(period)
        
        return jsonify(kpis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pythoncom.CoUninitialize()

@app.route('/api/inventory')
def api_inventory():
    excel, wb = get_excel()
    try:
        ws = wb.Sheets('Inventory_Master')
        
        headers = []
        for c in range(1, 20):
            h = ws.Cells(4, c).Value
            headers.append(str(h) if h else f"Col_{c}")
            
        data = []
        for r in range(5, 220):
            name = ws.Cells(r, 3).Value
            if not name:
                continue
            row_data = {}
            for c in range(1, 20):
                val = ws.Cells(r, c).Value
                if val is None:
                    val = ""
                # Convert datetime or objects to string if needed
                row_data[headers[c-1]] = val
            row_data['__row'] = r
            data.append(row_data)
            
        return jsonify({"headers": headers, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pythoncom.CoUninitialize()

@app.route('/api/update', methods=['POST'])
def api_update():
    updates = request.json.get('updates', [])
    excel, wb = get_excel()
    try:
        ws = wb.Sheets('Inventory_Master')
        
        headers = {}
        for c in range(1, 20):
            h = ws.Cells(4, c).Value
            h_str = str(h) if h else f"Col_{c}"
            headers[h_str] = c
            
        for update in updates:
            r = update['row']
            for k, v in update['changes'].items():
                if k in headers:
                    c = headers[k]
                    ws.Cells(r, c).Value = v
                    
        excel.Run('Asclepius_Wellness_PROFESSIONAL.xlsm!RefreshDashboard')
        wb.Save()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        pythoncom.CoUninitialize()

if __name__ == '__main__':
    app.run(port=5000, debug=True)
