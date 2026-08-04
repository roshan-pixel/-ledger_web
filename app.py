import os
import sqlite3
import json
import threading
import time
import re
from pathlib import Path
from flask import Flask, jsonify, request, render_template
import inventory_engine
import monthly_rollover

# Import Google Sheets Sync functions
from restore_gsheets import restore_from_gsheets
from init_gsheets import init_google_sheets

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False   # send Unicode as real UTF-8, not \uXXXX escapes

@app.errorhandler(500)
def internal_error(error):
    import traceback
    return jsonify({
        "success": False,
        "error": "500 Internal Server Error",
        "traceback": traceback.format_exc(),
        "error_msg": str(error)
    }), 500

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        "success": False,
        "error": "404 Not Found",
        "error_msg": str(error)
    }), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    return jsonify({
        "success": False,
        "error": "405 Method Not Allowed",
        "error_msg": str(error)
    }), 405

from invoice_api import invoice_api
app.register_blueprint(invoice_api)


DB_PATH = str(Path(__file__).parent / 'ledger.db')

# ---------------------------------------------------------------------------
# Disease Guide – in-memory cache
# ---------------------------------------------------------------------------
_DISEASE_CACHE = None          # list of dicts (flattened, all fields)
_DISEASE_CACHE_LOCK = threading.Lock()

# Fields returned in the list endpoint (heavy ingredient lists excluded)
_LIST_FIELDS = {
    'id', 'disease_name', 'category_name',
    'final_recommended_products', 'recommended_wellness_products',
    'diet', 'exercise', 'ayurvedic_tip', 'things_to_avoid', 'disclaimer',
}

DISEASE_JSON_PATH = Path(__file__).parent / 'static' / 'master_review_data_perfected.json'


def _load_disease_cache():
    """Load and flatten the disease JSON into the module-level cache.
    Thread-safe; reads the file only once per process lifetime."""
    global _DISEASE_CACHE
    with _DISEASE_CACHE_LOCK:
        if _DISEASE_CACHE is not None:
            return _DISEASE_CACHE
        with open(DISEASE_JSON_PATH, 'r', encoding='utf-8') as fh:
            raw = json.load(fh)
        flat = []
        for category_name, diseases in raw.items():
            for disease in diseases:
                entry = dict(disease)          # shallow copy
                entry['category_name'] = category_name
                entry['id'] = len(flat)        # Store backend index permanently
                flat.append(entry)
        _DISEASE_CACHE = flat
        return _DISEASE_CACHE


@app.route('/api/disease_guide')
def api_disease_guide():
    """Return a lightweight list of diseases, optionally filtered.

    Query params:
      ?q=<term>         – case-insensitive search on disease_name
      ?category=<name>  – exact-match (case-insensitive) on category_name
    """
    try:
        diseases = _load_disease_cache()

        q        = (request.args.get('q', '') or '').strip().lower()
        category = (request.args.get('category', '') or '').strip().lower()

        results = diseases
        if q:
            results = [d for d in results
                       if q in (d.get('disease_name') or '').lower()]
        if category:
            results = [d for d in results
                       if (d.get('category_name') or '').lower() == category]

        # Strip heavy fields – return only _LIST_FIELDS
        slim = [{k: v for k, v in d.items() if k in _LIST_FIELDS}
                for d in results]

        categories = sorted({d.get('category_name', '') for d in diseases})

        return jsonify({'categories': categories, 'diseases': slim, 'total': len(slim)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/disease_guide/<int:idx>')
def api_disease_guide_detail(idx):
    """Return the full record for a single disease by its 0-based index
    in the flattened list (stable within a process lifetime)."""
    try:
        diseases = _load_disease_cache()
        if idx < 0 or idx >= len(diseases):
            return jsonify({'error': 'Index out of range'}), 404
        return jsonify(diseases[idx])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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

@app.route('/invoice_history')
def invoice_history():
    return render_template('invoice_history.html')

@app.route('/old_index')
def index():
    return render_template('index.html')

@app.route('/inventory_master')
def inventory_master():
    return render_template('inventory_master.html')

@app.route('/portal_sync')
def portal_sync_page():
    return render_template('portal_sync.html')

@app.route('/disease_guide')
def disease_guide():
    return render_template('disease_guide.html')

@app.route('/mizoram_bronze')
def mizoram_bronze():
    return render_template('mizoram_bronze.html')

@app.route('/api/mizoram_bronze')
def api_mizoram_bronze():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM mizoram_bronze')
        data = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify(data)
    except Exception as e:
        # If table doesn't exist, we can just return empty array so frontend doesn't crash
        if "no such table" in str(e).lower():
            return jsonify([])
        return jsonify({"error": str(e)}), 500

import subprocess
@app.route('/api/fix_historical_buckets', methods=['POST'])
def api_fix_historical_buckets():
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'fix_buckets.py')
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        return jsonify({"success": True, "output": result.stdout, "error": result.stderr})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/mizoram_bronze/update', methods=['POST'])
def api_mizoram_bronze_update():
    try:
        data = request.get_json()
        row_id = data.get('id')
        field  = data.get('field')
        value  = data.get('value', '').strip()
        allowed = ['ds_name','mizoram_bronze_date','bronze_achieved','silver_achieved',
                   'silver_update_date','gold_achieved','gold_update_date',
                   'platinum_achieved','platinum_update_date','phone_no']
        if field not in allowed:
            return jsonify({'error': 'Field not allowed'}), 400
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE mizoram_bronze SET {}=? WHERE id=?'.format(field), (value, row_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

from sync_mizoram import sync_mizoram_data

@app.route('/api/sync_mizoram_now', methods=['POST'])
def api_sync_mizoram_now():
    success = sync_mizoram_data()
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Sync failed, check server logs"}), 500

@app.route('/api/inventory/restock', methods=['POST'])
def api_inventory_restock():
    try:
        data = request.get_json()
        product_name = data.get('product_name')
        qty_to_add = float(data.get('qty_to_add', 0))
        
        if not product_name or qty_to_add <= 0:
            return jsonify({'error': 'Invalid input'}), 400
            
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT c7 FROM inventory WHERE UPPER(c3) = ?", (product_name.upper(),))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'Product not found'}), 404
            
        current_qty = float(str(row[0]).replace(',', '') or 0)
        new_qty = current_qty + qty_to_add
        
        c.execute("UPDATE inventory SET c7 = ? WHERE UPPER(c3) = ?", (new_qty, product_name.upper()))
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) != 'TOTAL'")
        for r in c.fetchall():
            update_inventory_formulas(conn, r['row_num'], all_headers)
        
        update_totals_row(conn)
        conn.commit()
        conn.close()
        
        # Trigger background sync to Google Sheets
        try:
            import threading
            from init_gsheets import init_google_sheets
            t = threading.Thread(target=init_google_sheets)
            t.daemon = True
            t.start()
        except Exception as e:
            print("Failed to start gsheets sync:", e)
            
        return jsonify({'success': True, 'new_total_qty': new_qty})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/add_product', methods=['POST'])
def api_inventory_add_product():
    try:
        data = request.get_json()
        prod_name = data.get('product_name')
        hsn = data.get('hsn_code', '')
        price = data.get('price', 0)
        qty = data.get('total_qty', 0)
        
        if not prod_name:
            return jsonify({'error': 'Product name required'}), 400
            
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) = ?", (prod_name.upper(),))
        if c.fetchone():
            conn.close()
            return jsonify({'error': 'Product already exists'}), 400
            
        c.execute("SELECT MAX(CAST(c2 AS INTEGER)) FROM inventory WHERE c2 != '' AND UPPER(c3) != 'TOTAL'")
        max_sno = c.fetchone()[0] or 0
        sno = max_sno + 1
        
        cols = [f"c{i}" for i in range(1, 31)]
        vals = [""] * 30
        vals[1] = str(sno)
        vals[2] = prod_name
        vals[3] = str(hsn)
        vals[4] = str(price)
        vals[6] = str(qty)
        
        placeholders = ",".join(["?"] * 30)
        col_str = ",".join(cols)
        
        c.execute(f"INSERT INTO inventory ({col_str}) VALUES ({placeholders})", vals)
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) != 'TOTAL'")
        for r in c.fetchall():
            update_inventory_formulas(conn, r['row_num'], all_headers)
            
        update_totals_row(conn)
        conn.commit()
        conn.close()
        
        # Trigger background sync to Google Sheets
        try:
            import threading
            from init_gsheets import init_google_sheets
            t = threading.Thread(target=init_google_sheets)
            t.daemon = True
            t.start()
        except Exception as e:
            print("Failed to start gsheets sync:", e)
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/api/kpi')
def api_kpi():
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Total SKUs
        c.execute("SELECT COUNT(*) FROM inventory WHERE c3 != '' AND c3 IS NOT NULL AND UPPER(c3) != 'TOTAL'")
        total_skus = c.fetchone()[0]
        
        # We need to know which columns are what based on headers
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        headers = json.loads(c.fetchone()[0])
        
        # Find indices (1-based)
        dp_idx = None
        rem_qty_idx = None
        rem_val_idx = None
        tot_qty_idx = None
        for i, h in enumerate(headers):
            if h == 'Price/Pc (Rs.)': dp_idx = i + 1
            elif h == 'Remaining Qty': rem_qty_idx = i + 1
            elif h == 'Remaining Value (Rs.)': rem_val_idx = i + 1
            elif h == 'Total Qty': tot_qty_idx = i + 1
            
        if not rem_qty_idx: rem_qty_idx = 19
        if not rem_val_idx: rem_val_idx = 20
        if not tot_qty_idx: tot_qty_idx = 7
        
        c.execute(f"SELECT SUM(CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL)) FROM inventory WHERE c{rem_qty_idx} != '' AND UPPER(c3) != 'TOTAL'")
        rem_qty = round(c.fetchone()[0] or 0, 2)
        
        c.execute(f"SELECT SUM(CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) * CAST(REPLACE(c{dp_idx}, ',', '') AS REAL)) FROM inventory WHERE c{rem_qty_idx} != '' AND c{dp_idx} != '' AND UPPER(c3) != 'TOTAL'")
        rem_val = round(c.fetchone()[0] or 0, 2)
        
        # ── Ledger-based KPIs ────────────────────────────────────────
        # Read from ledger_report.json which is synced from Asclepius portal.
        # The first Cr entry = initial capital deposit.
        # All subsequent Cr entries = sales revenue being credited back by AWPL.
        import json as _json
        from pathlib import Path
        LEDGER_FILE = str(Path(__file__).parent / 'ledger_report.json')
        total_invested   = 0.0   # sum of all Dr entries (money spent on stock orders)
        initial_capital  = 0.0   # first Cr entry (owner's own money put in)
        sales_recycled   = 0.0   # subsequent Cr entries (sales revenue coming back)
        wallet_balance   = 0.0   # current closing balance
        first_cr_seen    = False
        try:
            with open(LEDGER_FILE, 'r', encoding='utf-8') as _f:
                _ledger = _json.load(_f)
            wallet_balance = float(_ledger.get('closing_balance', 0.0))
            for entry in _ledger.get('entries', []):
                tx_type = (entry.get('Transaction Type') or '').strip().upper()
                tx_amt  = float((entry.get('Transaction Amount') or '0').replace(',', ''))
                if tx_type == 'DR':
                    total_invested += tx_amt
                elif tx_type == 'CR':
                    if not first_cr_seen:
                        initial_capital = tx_amt   # e.g. Rs.20,00,000
                        first_cr_seen   = True
                    else:
                        sales_recycled += tx_amt   # money from your sales coming back
        except Exception:
            pass

        # Gross stock value = actual money spent purchasing from AWPL
        gross_val = round(total_invested, 2)
        
        c.execute(f"SELECT COUNT(*) FROM inventory WHERE CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) <= 10 AND CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) > 0 AND c{rem_qty_idx} != '' AND UPPER(c3) != 'TOTAL'")
        low_stock = c.fetchone()[0] or 0
        
        c.execute(f"SELECT COUNT(*) FROM inventory WHERE CAST(REPLACE(c{rem_qty_idx}, ',', '') AS REAL) <= 0 AND c{rem_qty_idx} != '' AND UPPER(c3) != 'TOTAL'")
        out_of_stock = c.fetchone()[0] or 0
        
        # Calculate Monthly Sales Value, Week Sales Value, Total Invoices directly from the invoices table
        c.execute("SELECT date_created, amount FROM invoices WHERE status != 'cancelled'")
        monthly_sales = 0
        week_sales = 0
        total_invoices = 0
        total_invoice_value = 0
        import datetime
        now = datetime.datetime.now()
        
        for r in c.fetchall():
            d_str = r[0]
            amt = float(r[1] or 0)
            
            try:
                if 'T' in d_str:
                    dt = datetime.datetime.fromisoformat(d_str)
                elif '/' in d_str:
                    dt = datetime.datetime.strptime(d_str[:10], '%d/%m/%Y')
                else:
                    dt = datetime.datetime.strptime(d_str[:10], '%Y-%m-%d')
                    
                total_invoices += 1
                total_invoice_value += amt
                
                # Check current month
                if dt.year == now.year and dt.month == now.month:
                    monthly_sales += amt
                    
                # Check past 7 days
                if (now - dt).days <= 7:
                    week_sales += amt
            except Exception:
                pass
                
        monthly_sales = round(monthly_sales, 2)
        week_sales = round(week_sales, 2)
        total_invoice_value = round(total_invoice_value, 2)
        
        # Read other static KPIs from DB
        c.execute("SELECT key, value FROM kpis")
        kpis = {row['key']: row['value'] for row in c.fetchall()}
        
        # Overwrite dynamic ones
        kpis['Total SKUs'] = str(total_skus)
        kpis['Remaining Qty'] = f"{rem_qty:g}"
        kpis['Remaining Value'] = str(rem_val)
        kpis['Gross Stock Value'] = str(gross_val)          # = total Dr (stock orders)
        kpis['Wallet Balance']   = str(round(wallet_balance, 2))
        kpis['Initial Capital']  = str(round(initial_capital, 2))   # first Cr = owner's money
        kpis['Sales Recycled']   = str(round(sales_recycled, 2))    # subsequent Cr = from sales
        kpis['Low Stock Count'] = str(low_stock)
        kpis['Out of Stock Count'] = str(out_of_stock)
        kpis['Monthly Sales Value'] = str(monthly_sales)
        kpis['Week Sales Value'] = str(week_sales)
        kpis['Total Invoices'] = str(total_invoices)
        kpis['Total Invoice Value'] = str(total_invoice_value)
        kpis['Reporting Period'] = "Live (Syncing from GSheets + Local)"
        
        conn.close()
        return jsonify(kpis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/force_sync')
def api_force_sync():
    try:
        from restore_gsheets import restore_from_gsheets
        restore_from_gsheets()
        return jsonify({"status": "success", "message": "Live data successfully fetched from Google Sheets!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/inventory')
def api_inventory():
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        headers_json = c.fetchone()
        if not headers_json:
            return jsonify({"error": "Headers not found"}), 500
            
        all_headers = json.loads(headers_json[0])
        
        headers = []
        cols_to_select = []
        for i, h in enumerate(all_headers):
            if h:  # only non-empty headers
                headers.append(h)
                cols_to_select.append(f"c{i+1}")
                
        c.execute(f"SELECT row_num, {', '.join(cols_to_select)} FROM inventory ORDER BY row_num")
        
        data = []
        for row in c.fetchall():
            prod_name = str(row['c3']).strip().upper() if row['c3'] else ''
            if not prod_name or prod_name == 'TOTAL':
                continue
            row_data = {}
            for h, col in zip(headers, cols_to_select):
                val = row[col]
                if isinstance(val, str) and h in ['Product Name', 'Item Name', 'Product']:
                    val = val.replace('\n', ' ')
                row_data[h] = val
            row_data['__row'] = row['row_num']
            data.append(row_data)
            
        conn.close()
        return jsonify({"headers": headers, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def update_inventory_formulas(conn, row_num, headers):
    """Recalculate formulas for a row."""
    c = conn.cursor()
    c.execute("SELECT * FROM inventory WHERE row_num=?", (row_num,))
    row = c.fetchone()
    if not row or str(row['c3']).upper() == 'TOTAL':
        return
        
    try:
        try:
            dp_idx = headers.index('Price/Pc (Rs.)') + 1
            tot_qty_idx = headers.index('Total Qty') + 1
            gross_val_idx = headers.index('Gross Value (Rs.)') + 1
            rem_qty_idx = headers.index('Remaining Qty') + 1
            rem_val_idx = headers.index('Remaining Value (Rs.)') + 1
        except ValueError:
            dp_idx = 5
            tot_qty_idx = 7
            gross_val_idx = 8
            rem_qty_idx = 19
            rem_val_idx = 20
            
        dp = float(str(row[f'c{dp_idx}']).replace(',', '') or 0)
        avail_stock = float(str(row[f'c{tot_qty_idx}']).replace(',', '') or 0)
        
        # update Gross Value
        gross_val = avail_stock * dp
        c.execute(f"UPDATE inventory SET c{gross_val_idx}=? WHERE row_num=?", (gross_val, row_num))
            
        # sum sold qtys and update sale values
        total_sold = 0
        for i, h in enumerate(headers):
            if str(h).startswith("Sold Qty"):
                qty_col = f"c{i+1}"
                val_col = f"c{i+2}"
                qty = float(str(row[qty_col]).replace(',', '') or 0)
                total_sold += qty
                sale_val = qty * dp
                c.execute(f"UPDATE inventory SET c{i+2}=? WHERE row_num=?", (sale_val, row_num))
                
        rem_qty = avail_stock - total_sold
        rem_val = rem_qty * dp
        
        # Calculate Total SP
        try:
            sp_pc_idx = headers.index('SP/Pc') + 1
            tot_sp_idx = headers.index('Total SP') + 1
            sp_val = row[f'c{sp_pc_idx}']
            sp_pc = float(str(sp_val).replace(',', '') if sp_val not in (None, '', 'None') else 0)
            tot_sp = sp_pc * rem_qty
        except ValueError:
            # If headers not found, fallback to c27 and c28
            sp_val = row['c27']
            sp_pc = float(str(sp_val).replace(',', '') if sp_val not in (None, '', 'None') else 0)
            tot_sp = sp_pc * rem_qty
            tot_sp_idx = 28
            
        c.execute(f"UPDATE inventory SET c{rem_qty_idx}=?, c{rem_val_idx}=?, c{tot_sp_idx}=? WHERE row_num=?",
                  (rem_qty, rem_val, tot_sp, row_num))
    except Exception as e:
        print("Error updating formulas:", e)

def update_totals_row(conn):
    """Recalculate the TOTAL row at the bottom."""
    try:
        c = conn.cursor()
        c.execute("SELECT row_num FROM inventory WHERE UPPER(c3) = 'TOTAL'")
        total_row = c.fetchone()
        if not total_row:
            return
        
        row_id = total_row['row_num']
        
        # Sum columns 6 through 20, and 28 (Total SP)
        sums = {}
        cols_to_sum = list(range(6, 21)) + [28]
        for col_idx in cols_to_sum:
            c.execute(f"SELECT SUM(CAST(REPLACE(c{col_idx}, ',', '') AS REAL)) FROM inventory WHERE UPPER(c3) != 'TOTAL' AND c{col_idx} != ''")
            s = c.fetchone()[0] or 0
            sums[f"c{col_idx}"] = s
            
        # Update the total row
        updates = ", ".join([f"{k}=?" for k in sums.keys()])
        values = list(sums.values()) + [row_id]
        c.execute(f"UPDATE inventory SET {updates} WHERE row_num=?", values)
    except Exception as e:
        print("Error updating totals row:", e)


@app.route('/api/stock_point_inventory', methods=['GET'])
def get_stock_point_inventory():
    from pathlib import Path
    import json
    
    SCRAPED_PATH = str(Path(__file__).parent / 'scraped_products.json')
    products = []
    
    try:
        with open(SCRAPED_PATH, 'r', encoding='utf-8') as f:
            scraped = json.load(f)
            
        for pid, pdata in scraped.items():
            name = pdata.get('name', '').strip()
            if name:
                products.append({
                    'id': pid,
                    'name': name,
                    'box_size': pdata.get('box_size', 1),
                    'rate': pdata.get('rate', 0.0)
                })
                
        # Sort alphabetically for better UX
        products.sort(key=lambda x: x['name'])
    except Exception as e:
        print("Error loading scraped_products.json:", e)

    return jsonify({'products': products})



@app.route('/api/submit_order', methods=['POST'])
def api_update():
    updates = request.json.get('updates', [])
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        header_map = {str(h) if h else f"Col_{i+1}": i+1 for i, h in enumerate(all_headers[:19])}
        
        for update in updates:
            row_num = update['row']
            for k, v in update['changes'].items():
                if k in header_map:
                    col_idx = header_map[k]
                    c.execute(f"UPDATE inventory SET c{col_idx}=? WHERE row_num=?", (str(v), row_num))
            
            update_inventory_formulas(conn, row_num, all_headers)
            
        update_totals_row(conn)
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/portal_sync', methods=['POST'])
def api_portal_sync():
    """Run the portal sync directly to SQLite!"""
    payload   = request.json or {}
    from_date = payload.get('from_date', '')
    to_date   = payload.get('to_date', '')
    if not from_date or not to_date:
        from datetime import datetime
        today     = datetime.now().strftime('%d/%m/%Y')
        from_date = today
        to_date   = today
    try:
        # We need to adapt portal_sync to write to SQLite instead of Excel!
        # For now, if we use the old script it will fail since we moved to SQLite.
        # Let's import the new SQLite version of portal_sync.
        # To save time, we will rewrite the sync endpoint in app_sqlite directly or create portal_sync_sqlite.py
        return jsonify({'error': 'Portal Sync is currently disabled during Cloud Migration.'}), 501
    except Exception as e:
        return jsonify({'error': str(e), 'updated': 0}), 500


@app.route('/api/inventory_master/months')
def api_inventory_master_months():
    try:
        conn = get_db()
        months = inventory_engine.get_available_months(conn)
        conn.close()
        return jsonify({'months': months})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory_master')
def api_inventory_master():
    month = request.args.get('month')
    try:
        conn = get_db()
        result = inventory_engine.calculate_inventory(conn, month)
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/product/purchases')
def api_product_purchases():
    import datetime
    import calendar
    product_name = request.args.get('product_name', '').strip()
    month_val = request.args.get('month', '').strip() # e.g. "2026-08"
    if not product_name:
        return jsonify({'purchases': [], 'error': 'product_name is required'})
    
    target_code = inventory_engine.extract_code(product_name)
    target_norm_name = re.sub(r'\[\d+\]', '', product_name).replace('-', '').strip().upper()
    target_norm_name = re.sub(r'\s+', ' ', target_norm_name)
    target_norm_name = re.sub(r'\s*\-\s*$', '', target_norm_name).strip()

    end_date = None
    if month_val:
        try:
            year, month = map(int, month_val.split('-'))
            last_day = calendar.monthrange(year, month)[1]
            end_date = datetime.date(year, month, last_day)
        except Exception as ex:
            print("Error parsing month in purchases:", ex)

    purchases_path = Path(__file__).parent / 'purchase_orders.json'
    results = []
    if purchases_path.exists():
        try:
            with open(purchases_path, 'r', encoding='utf-8') as f:
                orders = json.load(f)
                for order in orders:
                    o_date = order.get('date', '')
                    parsed_o_date = inventory_engine.parse_date(o_date)
                    if end_date and parsed_o_date and parsed_o_date > end_date:
                        continue

                    bill_no = order.get('bill_no', '')
                    party = order.get('party', '')
                    for prod in order.get('products', []):
                        if len(prod) >= 5:
                            code = str(prod[1]).strip()
                            raw_name = str(prod[2]).replace('\n', ' ').strip().upper()
                            norm_name = re.sub(r'\s+', ' ', raw_name)
                            norm_name = re.sub(r'\s*\-\s*$', '', norm_name).strip()
                            
                            qty = 0
                            try:
                                qty = float(str(prod[4]).replace(',', ''))
                            except:
                                pass
                                
                            rate = 0.0
                            try:
                                rate = float(str(prod[3]).replace(',', ''))
                            except:
                                pass
                                
                            total_val = 0.0
                            try:
                                total_val = float(str(prod[5]).replace(',', ''))
                            except:
                                pass

                            matched = False
                            if target_code and code == target_code:
                                matched = True
                            elif norm_name == target_norm_name:
                                matched = True
                            elif re.sub(r'[^A-Z0-9]', '', norm_name) == re.sub(r'[^A-Z0-9]', '', target_norm_name):
                                matched = True

                            if matched and qty > 0:
                                results.append({
                                    'date': o_date,
                                    'bill_no': bill_no,
                                    'party': party,
                                    'qty': qty,
                                    'rate': rate,
                                    'total': total_val
                                })
        except Exception as e:
            return jsonify({'purchases': [], 'error': str(e)}), 500
            
    results.sort(key=lambda x: inventory_engine.parse_date(x['date']) or datetime.date.min, reverse=True)
    return jsonify({'purchases': results})


@app.route('/api/product/sales')
def api_product_sales():
    import datetime
    import calendar
    product_name = request.args.get('product_name', '').strip()
    month_val = request.args.get('month', '').strip() # e.g. "2026-08"
    column_header = request.args.get('column_header', '').strip() # e.g. "Sold Qty (Aug 1-7)"
    
    if not product_name:
        return jsonify({'sales': [], 'error': 'product_name is required'})
        
    target_code = inventory_engine.extract_code(product_name)
    target_norm_name = re.sub(r'\[\d+\]', '', product_name).replace('-', '').strip().upper()
    target_norm_name = re.sub(r'\s+', ' ', target_norm_name)
    target_norm_name = re.sub(r'\s*\-\s*$', '', target_norm_name).strip()

    start_date = None
    end_date = None
    
    if month_val:
        try:
            year, month = map(int, month_val.split('-'))
            last_day = calendar.monthrange(year, month)[1]
            start_date = datetime.date(year, month, 1)
            end_date = datetime.date(year, month, last_day)
            
            if column_header:
                # Find matching range like: "Sold Qty (Aug 1-7)" or "Sold Qty (Jul 8-14)"
                m = re.search(r'Sold Qty \(([A-Za-z]{3})\s+(\d+)\-(\d+)\)', column_header)
                if m:
                    day_start = int(m.group(2))
                    day_end = int(m.group(3))
                    start_date = datetime.date(year, month, day_start)
                    end_date = datetime.date(year, month, day_end)
        except Exception as ex:
            print("Error parsing date range filtering:", ex)

    results = []
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM invoices WHERE status != 'cancelled'")
        invoices = c.fetchall()
        conn.close()
        
        for r in invoices:
            date_created = r['date_created']
            inv_date = inventory_engine.parse_date(date_created)
            if not inv_date:
                continue
            if start_date and inv_date < start_date:
                continue
            if end_date and inv_date > end_date:
                continue

            inv_no = r['invoice_no']
            cust_name = r['customer_name']
            ds_code = r['ds_code']
            
            try:
                items = json.loads(r['items'] or '[]')
            except:
                items = []
                
            for item in items:
                desc = str(item.get('description') or item.get('name') or '').strip()
                qty = 0
                try:
                    qty = float(str(item.get('qty', 0)).replace(',', ''))
                except:
                    pass
                    
                rate = 0.0
                try:
                    rate = float(str(item.get('rate') or item.get('price', 0)).replace(',', ''))
                except:
                    pass
                    
                total_val = 0.0
                try:
                    total_val = float(str(item.get('total') or (qty * rate)).replace(',', ''))
                except:
                    pass
                    
                if desc and qty > 0:
                    code = inventory_engine.extract_code(desc)
                    norm_name = re.sub(r'\[\d+\]', '', desc).replace('-', '').strip().upper()
                    norm_name = re.sub(r'\s+\d+$', '', norm_name)
                    norm_name = re.sub(r'\s+', ' ', norm_name)
                    norm_name = re.sub(r'\s*\-\s*$', '', norm_name).strip()
                    
                    matched = False
                    if target_code and code == target_code:
                        matched = True
                    elif norm_name == target_norm_name:
                        matched = True
                    elif re.sub(r'[^A-Z0-9]', '', norm_name) == re.sub(r'[^A-Z0-9]', '', target_norm_name):
                        matched = True
                        
                    if matched:
                        date_created = date_created or ''
                        formatted_date = date_created
                        if date_created and 'T' in date_created:
                            try:
                                formatted_date = datetime.datetime.fromisoformat(date_created).strftime('%d/%m/%Y')
                            except:
                                pass
                        results.append({
                            'date': formatted_date,
                            'invoice_no': inv_no,
                            'customer_name': cust_name or '—',
                            'ds_code': ds_code or '—',
                            'qty': qty,
                            'rate': rate,
                            'total': total_val
                        })
    except Exception as e:
        return jsonify({'sales': [], 'error': str(e)}), 500
        
    results.sort(key=lambda x: inventory_engine.parse_date(x['date']) or datetime.date.min, reverse=True)
    return jsonify({'sales': results})



@app.route('/api/inventory_master/update', methods=['POST'])
def api_inventory_master_update():
    payload = request.json
    row_num  = payload.get('row')
    col_name = payload.get('col')
    value    = payload.get('value')
    if not row_num or not col_name:
        return jsonify({'error': 'row and col are required'}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
        all_headers = json.loads(c.fetchone()[0])
        
        def normalize_header(h_str):
            if not h_str:
                return ""
            return re.sub(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s*', '', h_str)

        col_idx = None
        norm_col_name = normalize_header(col_name)
        for i, h in enumerate(all_headers[:30]):
            if normalize_header(str(h)) == norm_col_name or (not h and col_name == f"Col_{i+1}"):
                col_idx = i + 1
                break
                
        if not col_idx:
            return jsonify({'error': f'Column "{col_name}" not found'}), 404
            
        c.execute(f"UPDATE inventory SET c{col_idx}=? WHERE row_num=?", (str(value), row_num))
        update_inventory_formulas(conn, row_num, all_headers)
        
        update_totals_row(conn)
        conn.commit()
        conn.close()

        # Trigger background sync to Google Sheets
        try:
            import threading
            from init_gsheets import init_google_sheets
            t = threading.Thread(target=init_google_sheets)
            t.daemon = True
            t.start()
        except Exception as e:
            print("Failed to start gsheets sync:", e)

        return jsonify({'success': True, 'row': row_num, 'col': col_name, 'value': value})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/customer')
def api_customer():
    ds_code = request.args.get('ds_code', '').strip().upper()
    if not ds_code:
        return jsonify({'error': 'ds_code is required'}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM customers WHERE ds_code=?", (ds_code,))
        row = c.fetchone()
        conn.close()
        
        if row:
            return jsonify({
                'ds_code':          row['ds_code'],
                'ds_name':          row['ds_name'],
                'mobile':           row['mobile'],
                'address':          row['address'],
                'shipping_address': row['shipping_address'],
                'shipping_mobile':  row['shipping_mobile'],
                'shipping_pincode': row['shipping_pincode'],
                'last_invoice':     row['last_invoice'],
            })
            
        # Not found in DB, look up live in portal
        try:
            from ds_lookup_api import fetch_ds_from_portal
            portal_data = fetch_ds_from_portal(ds_code)
            if portal_data:
                # Add to DB
                conn = get_db()
                c = conn.cursor()
                c.execute('''INSERT INTO customers 
                             (ds_code, ds_name, mobile, address, shipping_address, shipping_mobile, shipping_pincode, last_invoice) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                          (portal_data['ds_code'], portal_data['ds_name'], portal_data['mobile'], portal_data['address'], 
                           portal_data['shipping_address'], portal_data['shipping_mobile'], portal_data['shipping_pincode'], portal_data['last_invoice']))
                conn.commit()
                conn.close()
                return jsonify(portal_data)
        except Exception as ex:
            print("Portal lookup error:", ex)
            
        return jsonify({'error': 'DS Code not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run sync on startup (only if credentials exist, e.g. on Render or local with key)
@app.route('/purchase_history')
def purchase_history():
    return render_template('purchase_history.html')

@app.route('/api/purchase_orders')
def api_purchase_orders():
    ORDERS_PATH = str(Path(__file__).parent / 'purchase_orders.json')
    try:
        with open(ORDERS_PATH, 'r', encoding='utf-8') as f:
            orders = json.load(f)
        return jsonify({'orders': orders})
    except FileNotFoundError:
        return jsonify({'orders': [], 'error': 'purchase_orders.json not found'})
    except Exception as e:
        return jsonify({'orders': [], 'error': str(e)}), 500

# ── Ledger Report ──────────────────────────────────────────────────────────

@app.route('/ledger_report')
def ledger_report():
    return render_template('ledger_report.html')


@app.route('/api/ledger_report')
def api_ledger_report():
    """Return cached ledger entries from ledger_report.json (fast, no scrape)."""
    import json as _json
    LEDGER_FILE = str(Path(__file__).parent / 'ledger_report.json')
    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({'success': False, 'error': 'No ledger data yet. Please sync first.', 'entries': [], 'closing_balance': 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'entries': [], 'closing_balance': 0}), 500


@app.route('/api/ledger_wallet_balance')
def api_ledger_wallet_balance():
    """Return just the closing balance for the stock-point-order wallet sync."""
    import json as _json
    LEDGER_FILE = str(Path(__file__).parent / 'ledger_report.json')
    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
            data = _json.load(f)
        closing = data.get('closing_balance', 0) or data.get('wallet_balance', 0)
        scraped_at = data.get('scraped_at', '')
        return jsonify({'success': True, 'closing_balance': closing, 'scraped_at': scraped_at})
    except FileNotFoundError:
        return jsonify({'success': False, 'closing_balance': 0, 'error': 'Not synced yet'})
    except Exception as e:
        return jsonify({'success': False, 'closing_balance': 0, 'error': str(e)}), 500


SCRAPER_PROCESS = None

@app.route('/api/sync_ledger', methods=['POST'])
def api_sync_ledger():
    global SCRAPER_PROCESS
    import subprocess
    import sys
    import json as _json
    script_path = os.path.join(os.path.dirname(__file__), 'fetch_ledger_report.py')
    
    if SCRAPER_PROCESS is not None and SCRAPER_PROCESS.poll() is None:
        return jsonify({"success": True, "status": "already_syncing"})
        
    try:
        SCRAPER_PROCESS = subprocess.Popen(
            [sys.executable, script_path, 'AAZFD8117G', 'ABC@1234']
        )
        return jsonify({'success': True, 'status': 'started'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sync_status', methods=['GET'])
def api_sync_status():
    global SCRAPER_PROCESS
    if SCRAPER_PROCESS is None:
        return jsonify({"status": "idle"})
    
    retcode = SCRAPER_PROCESS.poll()
    if retcode is None:
        return jsonify({"status": "syncing"})
    
    if retcode == 0:
        return jsonify({"status": "done"})
    else:
        return jsonify({"status": "error", "message": f"Scraper exited with code {retcode}"})


@app.route('/api/ledger_manual_entry', methods=['POST'])
def api_ledger_manual_entry():
    """Add a manual entry to the ledger_report.json file."""
    import json as _json
    from datetime import datetime
    
    data = request.json
    date_str = data.get('date', datetime.now().strftime("%d/%m/%Y"))
    particulars = data.get('particulars', '')
    amount = float(data.get('amount', 0))
    entry_type = data.get('type', 'credit').lower()
    
    LEDGER_FILE = str(Path(__file__).parent / 'ledger_report.json')
    try:
        with open(LEDGER_FILE, 'r', encoding='utf-8') as f:
            ledger = _json.load(f)
    except Exception:
        ledger = {"entries": [], "closing_balance": 0.0, "row_count": 0}
        
    current_balance = float(ledger.get('closing_balance', 0.0))
    if entry_type == 'credit':
        new_balance = current_balance + amount
    else:
        new_balance = current_balance - amount
        
    new_entry = {
        "Transaction Date": date_str,
        "Transaction Details": f"{particulars} (Manual Entry)",
        "Transaction Amount": str(amount),
        "Transaction Type": "Cr" if entry_type == 'credit' else "Dr",
        "Balance": str(new_balance)
    }
    
    ledger.setdefault('entries', []).append(new_entry)
    ledger['closing_balance'] = new_balance
    ledger['row_count'] = len(ledger['entries'])
    # Don't change scraped_at so we still know when the real portal was last scraped
    
    try:
        with open(LEDGER_FILE, 'w', encoding='utf-8') as f:
            _json.dump(ledger, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True, "closing_balance": new_balance})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/stock_point_order')
def stock_point_order():
    return render_template('stock_point_order.html')


@app.route('/api/place_stock_order', methods=['POST'])
def api_place_stock_order():
    """
    Places a franchise stock point order on the Asclepius portal.
    Expects JSON body: { "items": [{"name": "...", "qty": 10, "portal_id": "41"}, ...] }
    Runs submit_stock_order.py as a subprocess (handles Playwright in Gunicorn).
    """
    import subprocess
    import sys as _sys
    import json as _json

    data = request.json or {}
    items = data.get('items', [])

    if not items:
        return jsonify({'success': False, 'error': 'No items provided'}), 400

    script_path = os.path.join(os.path.dirname(__file__), 'submit_stock_order.py')
    items_json = _json.dumps(items, ensure_ascii=False)

    try:
        res = subprocess.run(
            [_sys.executable, script_path, items_json],
            capture_output=True, text=True, timeout=180  # 3 min max
        )
        output = res.stdout.strip()
        if not output:
            return jsonify({
                'success': False,
                'error': f'Portal script produced no output. Stderr: {res.stderr[:500]}'
            })
        return jsonify(_json.loads(output))
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Portal submission timed out (3 min). The portal may be slow.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sp_order_data')
def api_sp_order_data():
    import subprocess
    import sys
    import json
    
    script_path = os.path.join(os.path.dirname(__file__), 'fetch_order_data.py')
    try:
        # Using the provided credentials with a 25-second timeout to prevent gunicorn worker hanging
        res = subprocess.run([sys.executable, script_path, "AAZFD8117G", "ABC@1234"], capture_output=True, text=True, timeout=25)
        
        # If output is empty, it means the script crashed without printing json
        if not res.stdout.strip():
            return jsonify({"success": False, "error": f"Scraper crashed silently. Stderr: {res.stderr}"})
            
        return jsonify(json.loads(res.stdout))
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Scraping script timed out after 25 seconds. The Asclepius portal might be slow, or the cloud provider blocked the connection."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-SYNC SCHEDULER
# Runs once at startup, then loops forever in a background daemon thread:
#   • Every day  → check if month changed and roll headers automatically
#   • Every hour → push local DB → Google Sheets
# ─────────────────────────────────────────────────────────────────────────────
def _auto_sync_loop():
    import datetime

    # Track last GSheets push and last rollover-check day
    last_push_hour   = -1
    last_rollover_day = -1

    print("[AutoSync] Background scheduler started.")

    while True:
        try:
            now = datetime.datetime.now()

            # ── Monthly rollover: run once per calendar day ───────────────
            if now.day != last_rollover_day:
                try:
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row
                    rolled = monthly_rollover.check_and_rollover(conn, verbose=True)
                    conn.close()
                    if rolled:
                        # Immediately push the new headers to GSheets after rollover
                        print("[AutoSync] Rollover done — pushing fresh headers to GSheets.")
                        init_google_sheets()
                except Exception as e:
                    print(f"[AutoSync] Rollover check failed: {e}")
                last_rollover_day = now.day

            # ── Hourly GSheets push ───────────────────────────────────────
            if now.hour != last_push_hour:
                try:
                    print(f"[AutoSync] Hourly push to Google Sheets ({now.strftime('%H:%M')})...")
                    init_google_sheets()
                    print("[AutoSync] ✓ GSheets push complete.")
                except Exception as e:
                    print(f"[AutoSync] GSheets push failed: {e}")
                last_push_hour = now.hour

        except Exception as e:
            print(f"[AutoSync] Scheduler error: {e}")

        # Sleep 5 minutes between checks (light on resources)
        time.sleep(300)


# ── Startup sequence ─────────────────────────────────────────────────────────
_creds_exist = (
    os.path.exists('credentials.json') or
    os.path.exists('/etc/secrets/credentials.json')
)

if _creds_exist:
    # 1. Pull latest data FROM Google Sheets into local DB on every startup
    print("[Startup] Restoring from Google Sheets...")
    try:
        restore_from_gsheets()
        print("[Startup] ✓ Restored from GSheets.")
    except Exception as e:
        print(f"[Startup] GSheets restore failed: {e}")

# 2. Check if headers need to roll over (e.g. new month since last deploy)
try:
    _conn = sqlite3.connect(DB_PATH)
    _conn.row_factory = sqlite3.Row
    monthly_rollover.check_and_rollover(_conn, verbose=True)
    _conn.close()
except Exception as e:
    print(f"[Startup] Rollover check failed: {e}")

# 3. Start the perpetual background sync scheduler
_scheduler_thread = threading.Thread(target=_auto_sync_loop, daemon=True, name="AutoSyncScheduler")
_scheduler_thread.start()
print("[Startup] ✓ Auto-sync scheduler running (hourly GSheets push + daily rollover).")


@app.route('/api/fix_sync')
def api_fix_sync():
    import robust_sync
    try:
        robust_sync.sync_all_to_inventory()
        return "Fixed!"
    except Exception as e:
        return str(e)


@app.route('/api/sync_now', methods=['POST', 'GET'])
def api_sync_now():
    """Manual trigger: pull from GSheets → check rollover → push back."""
    log = []
    try:
        if _creds_exist:
            restore_from_gsheets()
            log.append("✓ Pulled from Google Sheets")
    except Exception as e:
        log.append(f"✗ Pull failed: {e}")
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rolled = monthly_rollover.check_and_rollover(conn, verbose=False)
        conn.close()
        log.append(f"{'✓ Headers rolled over to new month' if rolled else '✓ Headers already current'}")
    except Exception as e:
        log.append(f"✗ Rollover check failed: {e}")
    try:
        if _creds_exist:
            init_google_sheets()
            log.append("✓ Pushed to Google Sheets")
    except Exception as e:
        log.append(f"✗ Push failed: {e}")
    return jsonify({"success": True, "log": log})


if __name__ == '__main__':
    # Cloud-ready configuration
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
