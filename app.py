import os
import math
import pythoncom
import win32com.client
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
from invoice_api import invoice_api
app.register_blueprint(invoice_api)
EXCEL_PATH = r'C:\Users\sgarm\Downloads\Asclepius_Wellness_PROFESSIONAL.xlsm'

# Global Excel COM objects - single-threaded access (threaded=False)
_excel = None
_wb = None

def get_excel():
    global _excel, _wb
    pythoncom.CoInitialize()
    
    # Try to reuse existing connection
    if _excel is not None and _wb is not None:
        try:
            _ = _wb.Name  # Test if connection is alive
            return _excel, _wb
        except Exception:
            _excel = None
            _wb = None
    
    # Create new connection
    try:
        _excel = win32com.client.GetActiveObject("Excel.Application")
    except Exception:
        _excel = win32com.client.Dispatch("Excel.Application")
    
    _wb = None
    for open_wb in _excel.Workbooks:
        if open_wb.Name == 'Asclepius_Wellness_PROFESSIONAL.xlsm':
            _wb = open_wb
            break
    
    if not _wb:
        _wb = _excel.Workbooks.Open(EXCEL_PATH)
    
    return _excel, _wb


def clean_excel_val(val):
    if val is None:
        return ""
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return ""
    if type(val).__name__ == 'time':
        return str(val)
    if hasattr(val, 'Format'):
        return str(val)
    return val


@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/inventory')
def inventory():
    return render_template('inventory.html')

@app.route('/invoice')
def invoice():
    return render_template('invoice.html')

@app.route('/old_index')
def index():
    return render_template('index.html')

@app.route('/inventory_master')
def inventory_master():
    return render_template('inventory_master.html')

@app.route('/portal_sync')
def portal_sync_page():
    return render_template('portal_sync.html')

@app.route('/api/kpi')
def api_kpi():
    try:
        excel, wb = get_excel()
        ws = wb.Sheets('_KPI_Data')
        kpis = {}
        
        # Bulk read KPIs in one call
        kpi_vals = ws.Range(ws.Cells(2, 1), ws.Cells(16, 2)).Value
        for row in kpi_vals:
            key = row[0]
            val = row[1]
            if key:
                kpis[str(key)] = clean_excel_val(val)
        
        ws_dash = wb.Sheets('Dashboard')
        period = ws_dash.Cells(2, 8).Value
        kpis['Reporting Period'] = str(clean_excel_val(period))
        
        return jsonify(kpis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/inventory')
def api_inventory():
    try:
        excel, wb = get_excel()
        ws = wb.Sheets('Inventory_Master')
        
        # Bulk read headers in one call
        header_vals = ws.Range(ws.Cells(4, 1), ws.Cells(4, 19)).Value[0]
        headers = [str(h) if h else f"Col_{i+1}" for i, h in enumerate(header_vals)]
        
        # Bulk read all data in one call
        data_vals = ws.Range(ws.Cells(5, 1), ws.Cells(220, 19)).Value
        
        data = []
        for r_idx, row in enumerate(data_vals):
            name = row[2]  # Column C is Product Name
            if not name:
                continue
            row_data = {}
            for c_idx, val in enumerate(row):
                row_data[headers[c_idx]] = clean_excel_val(val)
            row_data['__row'] = r_idx + 5
            data.append(row_data)
        
        return jsonify({"headers": headers, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/update', methods=['POST'])
def api_update():
    updates = request.json.get('updates', [])
    try:
        excel, wb = get_excel()
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


@app.route('/api/portal_sync', methods=['POST'])
def api_portal_sync():
    """Run the portal → Excel sync. Accepts {from_date, to_date} as DD/MM/YYYY."""
    payload   = request.json or {}
    from_date = payload.get('from_date', '')
    to_date   = payload.get('to_date', '')
    if not from_date or not to_date:
        from datetime import datetime
        today     = datetime.now().strftime('%d/%m/%Y')
        from_date = today
        to_date   = today
    try:
        from portal_sync import run_sync
        result = run_sync(from_date, to_date)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'updated': 0}), 500


@app.route('/api/inventory_master')
def api_inventory_master():
    """Return ALL columns from Inventory_Master with row numbers for editing."""
    try:
        excel, wb = get_excel()
        ws = wb.Sheets('Inventory_Master')
        # Read headers (row 4, cols B-W = 2-23)
        header_row = ws.Range(ws.Cells(4, 2), ws.Cells(4, 23)).Value[0]
        headers = [str(h) if h else f'Col_{i+2}' for i, h in enumerate(header_row)]
        # Read data (rows 5-220)
        data_range = ws.Range(ws.Cells(5, 2), ws.Cells(220, 23)).Value
        rows = []
        for r_idx, row in enumerate(data_range):
            if not row[1]:  # Skip if Product Name (col 3 = index 1) is empty
                continue
            row_data = {'__row': r_idx + 5}
            for c_idx, val in enumerate(row):
                row_data[headers[c_idx]] = clean_excel_val(val)
            rows.append(row_data)
        return jsonify({'headers': headers, 'data': rows})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory_master/update', methods=['POST'])
def api_inventory_master_update():
    """Write edited cell values back to Inventory_Master and save."""
    payload = request.json
    row_num  = payload.get('row')        # Excel row number (1-indexed)
    col_name = payload.get('col')        # Header name
    value    = payload.get('value')      # New value
    if not row_num or not col_name:
        return jsonify({'error': 'row and col are required'}), 400
    try:
        excel, wb = get_excel()
        ws = wb.Sheets('Inventory_Master')
        # Find column index by matching header name
        header_row = ws.Range(ws.Cells(4, 2), ws.Cells(4, 23)).Value[0]
        col_idx = None
        for i, h in enumerate(header_row):
            if str(h) == col_name:
                col_idx = i + 2  # offset: headers start at col B = 2
                break
        if col_idx is None:
            return jsonify({'error': f'Column "{col_name}" not found'}), 404
        # Write value
        try:
            numeric = float(value)
            ws.Cells(row_num, col_idx).Value = numeric
        except (ValueError, TypeError):
            ws.Cells(row_num, col_idx).Value = value
        wb.Save()
        return jsonify({'success': True, 'row': row_num, 'col': col_name, 'value': value})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/customer')
def api_customer():
    ds_code = request.args.get('ds_code', '').strip().upper()
    if not ds_code:
        return jsonify({'error': 'ds_code is required'}), 400
    try:
        excel, wb = get_excel()
        ws = wb.Sheets('Customer_Profile')
        # Bulk read up to 500 rows
        data = ws.Range(ws.Cells(2, 1), ws.Cells(500, 9)).Value
        for row in data:
            code = str(row[0]).strip().upper() if row[0] else ''
            if code == ds_code:
                return jsonify({
                    'ds_code':          str(row[0]) if row[0] else '',
                    'ds_name':          str(row[1]) if row[1] else '',
                    'mobile':           str(row[2]) if row[2] else '',
                    'address':          str(row[3]) if row[3] else '',
                    'shipping_address': str(row[4]) if row[4] else '',
                    'shipping_mobile':  str(row[5]) if row[5] else '',
                    'shipping_pincode': str(row[6]) if row[6] else '',
                    'last_invoice':     str(row[7]) if row[7] else '',
                })
        
        # Not found in Excel, look up live in portal
        try:
            from ds_lookup_api import fetch_ds_from_portal
            portal_data = fetch_ds_from_portal(ds_code)
            if portal_data:
                # Optionally add it to the Excel sheet here?
                return jsonify(portal_data)
        except Exception as ex:
            print("Portal lookup error:", ex)
            
        return jsonify({'error': 'DS Code not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # threaded=False = single-threaded, no lock needed, no COM deadlocks
    app.run(port=5000, debug=True, threaded=False, use_reloader=False)
