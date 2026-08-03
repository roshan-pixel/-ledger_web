"""
inventory_engine.py
Dynamic inventory calculator for monthly rollover.
Replaces the static July-based caching with dynamic purchase and sales calculations.
"""
import sqlite3
import json
import datetime
import re
from pathlib import Path

def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    try:
        if 'T' in date_str:
            return datetime.datetime.fromisoformat(date_str).date()
        if '/' in date_str:
            return datetime.datetime.strptime(date_str[:10], '%d/%m/%Y').date()
        return datetime.datetime.strptime(date_str[:10], '%Y-%m-%d').date()
    except Exception:
        return None

def extract_code(text):
    m = re.search(r'\[(\d+)\]', text)
    if m: return m.group(1)
    m = re.search(r'\((\d+)\)', text)
    if m: return m.group(1)
    m = re.search(r'\s+(\d+)$', text.strip())
    if m: return m.group(1)
    return None

def get_days_in_month(year, month):
    if month == 12:
        next_month = datetime.date(year + 1, 1, 1)
    else:
        next_month = datetime.date(year, month + 1, 1)
    return (next_month - datetime.date(year, month, 1)).days

def get_available_months(conn):
    """Scan database invoices and purchase orders to find all unique months."""
    months = set()
    c = conn.cursor()
    
    # 1. Scan invoices
    c.execute("SELECT date_created FROM invoices WHERE date_created IS NOT NULL AND status != 'cancelled'")
    for r in c.fetchall():
        dt = parse_date(r[0])
        if dt:
            months.add((dt.year, dt.month))
            
    # 2. Scan purchase orders
    orders_path = Path(__file__).parent / 'purchase_orders.json'
    if orders_path.exists():
        try:
            with open(orders_path, 'r', encoding='utf-8') as f:
                purchases = json.load(f)
                for order in purchases:
                    dt = parse_date(order.get('date'))
                    if dt:
                        months.add((dt.year, dt.month))
        except Exception:
            pass
            
    # 3. Always include current month
    now = datetime.datetime.now()
    months.add((now.year, now.month))
    
    # Sort months descending
    sorted_months = sorted(list(months), reverse=True)
    
    result = []
    for y, m in sorted_months:
        d = datetime.date(y, m, 1)
        val = f"{y:04d}-{m:02d}"
        label = d.strftime("%B %Y")
        result.append({"value": val, "label": label})
        
    return result

def calculate_inventory(conn, target_month_str=None):
    """
    Dynamically computes headers and inventory quantities/values for target_month_str (format: YYYY-MM).
    If target_month_str is None, defaults to the latest month of data or current month.
    """
    c = conn.cursor()
    
    # Resolve target month if not specified
    if not target_month_str:
        months = get_available_months(conn)
        if months:
            target_month_str = months[0]['value'] # latest month
        else:
            target_month_str = datetime.datetime.now().strftime('%Y-%m')
            
    year, month = map(int, target_month_str.split('-'))
    start_date = datetime.date(year, month, 1)
    days_in_month = get_days_in_month(year, month)
    end_date = datetime.date(year, month, days_in_month)
    month_name_short = start_date.strftime('%b')
    
    # 1. Fetch base headers from settings
    c.execute("SELECT value FROM settings WHERE key='inventory_headers'")
    base_headers_json = c.fetchone()
    if base_headers_json:
        base_headers = json.loads(base_headers_json[0])
    else:
        base_headers = ["", "S.No", "Product Name", "HSN Code", "Price/Pc (Rs.)", "Box", "Total Qty", "Gross Value (Rs.)",
                        "Sold Qty", "Sale Value", "Sold Qty", "Sale Value", "Sold Qty", "Sale Value",
                        "Sold Qty", "Sale Value", "Sold Qty", "Sale Value",
                        "Remaining Qty", "Remaining Value (Rs.)", "Stock Status", "Sales %", "Remarks",
                        "Tie-Breaker Sold Qty", "Tie-Breaker Sale Value", "Low Stock Index", "SP/Pc", "Total SP", "", ""]

    # 2. Build dynamic month headers
    headers = []
    week_ranges = ["1-7", "8-14", "15-21", "22-28", f"29-{days_in_month}"]
    week_qty_headers = [f"Sold Qty ({month_name_short} {r})" for r in week_ranges]
    week_val_headers = [f"Sale Value ({month_name_short} {r})" for r in week_ranges]
    
    week_qty_idx = 0
    week_val_idx = 0
    
    for h in base_headers:
        if not h:
            headers.append("")
            continue
        if str(h).startswith("Sold Qty ("):
            headers.append(week_qty_headers[week_qty_idx])
            week_qty_idx = min(week_qty_idx + 1, 4)
        elif str(h).startswith("Sale Value ("):
            headers.append(week_val_headers[week_val_idx])
            week_val_idx = min(week_val_idx + 1, 4)
        else:
            headers.append(h)
            
    # 3. Load product rows from DB
    c.execute("SELECT * FROM inventory ORDER BY row_num")
    db_rows = c.fetchall()
    
    inv_map_by_code = {}
    inv_map_by_name = {}
    products = []
    
    for r in db_rows:
        name = str(r['c3']).strip()
        if not name or name.upper() == 'TOTAL':
            continue
        code = extract_code(name)
        norm_name = re.sub(r'\[\d+\]', '', name).replace('-', '').strip().upper()
        norm_name = re.sub(r'\s+', ' ', norm_name)
        
        # Load values from DB or defaults
        try:
            price = float(str(r['c5']).replace(',', '') or 0)
        except:
            price = 0.0
            
        try:
            sp_pc = float(str(r['c27']).replace(',', '') if r['c27'] not in (None, '', 'None') else 0)
        except:
            sp_pc = 0.0
            
        prod_data = {
            'row_num': r['row_num'],
            'S.No': r['c2'],
            'Product Name': name,
            'HSN Code': r['c4'],
            'Price/Pc (Rs.)': price,
            'Box': r['c6'],
            'SP/Pc': sp_pc,
            'Remarks': r['c23'] or '',
            'total_purchased': 0.0,
            'sales_this_month': [0.0] * 5, # 5 weeks
            'cumulative_sales': 0.0,
        }
        products.append(prod_data)
        if code:
            inv_map_by_code[code] = prod_data
        inv_map_by_name[norm_name] = prod_data

    # 4. Load purchases up to end of selected month (Total Stock IN)
    orders_path = Path(__file__).parent / 'purchase_orders.json'
    if orders_path.exists():
        try:
            with open(orders_path, 'r', encoding='utf-8') as f:
                purchases = json.load(f)
                for order in purchases:
                    o_date = parse_date(order.get('date'))
                    if o_date and o_date <= end_date:
                        for prod in order.get('products', []):
                            if len(prod) >= 5:
                                code = str(prod[1]).strip()
                                raw_name = str(prod[2]).replace('\n', ' ').strip().upper()
                                norm_name = re.sub(r'\s+', ' ', raw_name)
                                try:
                                    qty = float(str(prod[4]).replace(',', ''))
                                except:
                                    qty = 0
                                
                                if qty > 0:
                                    prod_data = inv_map_by_code.get(code) or inv_map_by_name.get(norm_name)
                                    if prod_data:
                                        prod_data['total_purchased'] += qty
        except Exception as e:
            print("Error parsing purchases in engine:", e)

    # 5. Load sales up to end of selected month (Total Stock OUT)
    c.execute("SELECT * FROM invoices WHERE status != 'cancelled'")
    invoices = c.fetchall()
    
    for r in invoices:
        date_created = r['date_created']
        inv_date = parse_date(date_created)
        if not inv_date:
            continue
            
        items = json.loads(r['items'] or '[]')
        
        # Cumulative sales up to end of selected month
        if inv_date <= end_date:
            for item in items:
                desc = str(item.get('description') or item.get('name') or '').strip()
                try:
                    qty = float(str(item.get('qty', 0)).replace(',', ''))
                except:
                    qty = 0
                if desc and qty > 0:
                    code = extract_code(desc)
                    norm_name = re.sub(r'\[\d+\]', '', desc).replace('-', '').strip().upper()
                    norm_name = re.sub(r'\s+\d+$', '', norm_name)
                    norm_name = re.sub(r'\s+', ' ', norm_name)
                    
                    prod_data = None
                    if code and code in inv_map_by_code:
                        prod_data = inv_map_by_code[code]
                    elif norm_name in inv_map_by_name:
                        prod_data = inv_map_by_name[norm_name]
                        
                    if prod_data:
                        prod_data['cumulative_sales'] += qty
                        
                        # Sales specifically in target month (split by week)
                        if inv_date.year == year and inv_date.month == month:
                            day = inv_date.day
                            if day <= 7: week_idx = 0
                            elif day <= 14: week_idx = 1
                            elif day <= 21: week_idx = 2
                            elif day <= 28: week_idx = 3
                            else: week_idx = 4
                            prod_data['sales_this_month'][week_idx] += qty

    # 6. Map to the dynamic headers format and calculate totals
    rows_data = []
    
    # Totals collectors
    total_gross_val = 0.0
    total_total_qty = 0.0
    total_sold_qty_weeks = [0.0] * 5
    total_sale_val_weeks = [0.0] * 5
    total_rem_qty = 0.0
    total_rem_val = 0.0
    total_sp = 0.0
    
    for p in products:
        dp = p['Price/Pc (Rs.)']
        sp_pc = p['SP/Pc']
        total_purchased = p['total_purchased']
        
        # Current month sales
        weeks_sold = p['sales_this_month']
        weeks_val = [w * dp for w in weeks_sold]
        
        # Remaining calculations
        rem_qty = total_purchased - p['cumulative_sales']
        rem_val = rem_qty * dp
        tot_sp = rem_qty * sp_pc
        gross_val = total_purchased * dp
        
        # Sales percentage based on current month's sales over total available stock
        sum_month_sold = sum(weeks_sold)
        sales_pct = (sum_month_sold / total_purchased) if total_purchased > 0 else 0.0
        
        # Determine stock status
        if rem_qty <= 0:
            status = "OUT OF STOCK"
        elif rem_qty <= 10:
            status = "LOW STOCK"
        else:
            status = "IN STOCK"
            
        # Collect totals
        total_total_qty += total_purchased
        total_gross_val += gross_val
        for i in range(5):
            total_sold_qty_weeks[i] += weeks_sold[i]
            total_sale_val_weeks[i] += weeks_val[i]
        total_rem_qty += rem_qty
        total_rem_val += rem_val
        total_sp += tot_sp
        
        # Build row dictionary matching dynamic headers list
        r_dict = {
            '__row': p['row_num'],
            'S.No': p['S.No'],
            'Product Name': p['Product Name'],
            'HSN Code': p['HSN Code'],
            'Price/Pc (Rs.)': dp,
            'Box': p['Box'],
            'Total Qty': total_purchased,
            'Gross Value (Rs.)': gross_val,
            'Remaining Qty': rem_qty,
            'Remaining Value (Rs.)': rem_val,
            'Stock Status': status,
            'Sales %': sales_pct,
            'Remarks': p['Remarks'],
            'Tie-Breaker Sold Qty': sum_month_sold, # or current month sum
            'Tie-Breaker Sale Value': sum_month_sold * dp,
            'Low Stock Index': 1 if rem_qty <= 10 else 0,
            'SP/Pc': sp_pc,
            'Total SP': tot_sp
        }
        
        # Add weekly sales and values dynamically
        for i in range(5):
            r_dict[week_qty_headers[i]] = weeks_sold[i]
            r_dict[week_val_headers[i]] = weeks_val[i]
            
        rows_data.append(r_dict)
        
    # Create the TOTAL row dictionary
    totals_row = {
        '__row': 9999, # high dummy row num
        'S.No': '',
        'Product Name': 'TOTAL',
        'HSN Code': '',
        'Price/Pc (Rs.)': '',
        'Box': '',
        'Total Qty': total_total_qty,
        'Gross Value (Rs.)': total_gross_val,
        'Remaining Qty': total_rem_qty,
        'Remaining Value (Rs.)': total_rem_val,
        'Stock Status': '',
        'Sales %': (sum(total_sold_qty_weeks) / total_total_qty) if total_total_qty > 0 else 0.0,
        'Remarks': '',
        'Tie-Breaker Sold Qty': sum(total_sold_qty_weeks),
        'Tie-Breaker Sale Value': sum(total_sale_val_weeks),
        'Low Stock Index': '',
        'SP/Pc': '',
        'Total SP': total_sp
    }
    for i in range(5):
        totals_row[week_qty_headers[i]] = total_sold_qty_weeks[i]
        totals_row[week_val_headers[i]] = total_sale_val_weeks[i]
        
    rows_data.append(totals_row)
    
    return {
        'headers': [h for h in headers if h], # filter out empty strings
        'data': rows_data,
        'target_month': target_month_str
    }
