"""
portal_sync.py — Asclepius C&F Portal → Excel Inventory Sync Engine
────────────────────────────────────────────────────────────────────
Fetches DS Sale Report (product-level qty per invoice) and writes
sold quantities back to the correct weekly column in Inventory_Master.
"""
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import json, sys, re

PORTAL_URL   = 'https://asclepiuswellness.com'
LOGIN_URL    = f'{PORTAL_URL}/login.aspx?webid=1'
SALE_REPORT  = f'{PORTAL_URL}/shoppingpoint/spDSSaleReport.aspx'
USERNAME     = 'AAZFD8117G'
PASSWORD     = 'ABC@1234'


def login_and_get_data(from_date: str, to_date: str) -> list[dict]:
    """
    Login to portal, fetch DS Sale Report for date range.
    Returns list of {product_name, qty, sale_value, date, invoice_no, ds_code}
    Date format: DD/MM/YYYY
    """
    results = []
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context()
    page = ctx.new_page()

    try:
        # ── Login ────────────────────────────────────────────
        page.goto(LOGIN_URL, wait_until='networkidle', timeout=30000)
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', USERNAME)
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', PASSWORD)
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle', timeout=20000)

        # ── Go to DS Sale Report ──────────────────────────────
        page.goto(SALE_REPORT, wait_until='networkidle', timeout=20000)
        page.fill('#ctl00_ContentPlaceHolder1_txtFrom', from_date)
        page.fill('#ctl00_ContentPlaceHolder1_txtTo',   to_date)
        page.click('#ctl00_ContentPlaceHolder1_btnshow')
        page.wait_for_load_state('networkidle', timeout=20000)
        page.wait_for_timeout(1500)

        # ── Parse the table ───────────────────────────────────
        table = page.query_selector('table')
        if not table:
            print('[SYNC] No table found on DS Sale Report page')
            return results

        rows = table.query_selector_all('tr')
        headers = []
        for i, row in enumerate(rows):
            cells = row.query_selector_all('th, td')
            cell_texts = [c.inner_text().strip() for c in cells]
            if i == 0:
                headers = cell_texts
                print('[SYNC] Headers:', headers)
                continue
            if not any(cell_texts):
                continue

            # Map cells to headers
            row_data = {}
            for j, h in enumerate(headers):
                row_data[h] = cell_texts[j] if j < len(cell_texts) else ''

            results.append(row_data)

        print(f'[SYNC] Fetched {len(results)} rows from portal')
        if results:
            print('[SYNC] Sample row:', results[0])

    except Exception as e:
        print(f'[SYNC] Error fetching portal data: {e}')
    finally:
        browser.close()
        p.stop()

    return results


def get_week_column(sale_date: datetime, excel_headers: list[str]) -> str | None:
    """
    Find which 'Sold Qty (Mon DD-DD)' column the sale_date falls into.
    Headers look like: 'Sold Qty (Jun 1-7)', 'Sold Qty (Jun 29-30)', etc.
    """
    month_name = sale_date.strftime('%b')  # e.g. 'Jun'
    day = sale_date.day

    for h in excel_headers:
        if not h.startswith('Sold Qty'):
            continue
        # Extract e.g. "Jun 29-30"
        m = re.search(r'\((\w+)\s+(\d+)-(\d+)\)', h)
        if not m:
            continue
        col_month, start_day, end_day = m.group(1), int(m.group(2)), int(m.group(3))
        if col_month == month_name and start_day <= day <= end_day:
            return h
    return None


def sync_to_excel(portal_rows: list[dict], product_col_key='Product Name',
                   qty_col_key='Qty', date_col_key='Date'):
    """
    Write portal sale quantities into the Excel Inventory_Master sheet.
    Matches products by fuzzy name, updates the correct week Sold Qty column.
    """
    import win32com.client, pythoncom, math
    pythoncom.CoInitialize()

    EXCEL_PATH = r'C:\Users\sgarm\Downloads\Asclepius_Wellness_PROFESSIONAL.xlsm'

    try:
        excel = win32com.client.GetActiveObject('Excel.Application')
    except Exception:
        excel = win32com.client.Dispatch('Excel.Application')
        excel.Visible = False

    wb = None
    for open_wb in excel.Workbooks:
        if 'Asclepius_Wellness_PROFESSIONAL' in open_wb.Name:
            wb = open_wb
            break
    if not wb:
        wb = excel.Workbooks.Open(EXCEL_PATH)

    ws = wb.Sheets('Inventory_Master')

    # ── Read headers (row 4, cols B-W) ───────────────────────
    header_row = ws.Range(ws.Cells(4, 2), ws.Cells(4, 25)).Value[0]
    headers = [str(h) if h else '' for h in header_row]

    # Build header → col-index map (1-indexed, offset from col B=2)
    header_to_col = {}
    for i, h in enumerate(headers):
        if h:
            header_to_col[h] = i + 2  # col B is index 2

    # ── Read product names (col C = col 3) ───────────────────
    products_range = ws.Range(ws.Cells(5, 3), ws.Cells(220, 3)).Value
    inv_products = {}  # lowercase_name → excel_row
    for r_idx, cell in enumerate(products_range):
        name = str(cell[0]).strip() if cell[0] else ''
        if name:
            inv_products[name.lower()] = r_idx + 5

    print(f'[SYNC] Inventory has {len(inv_products)} products')

    # ── Process each portal row ───────────────────────────────
    updated = 0
    skipped = 0
    not_found = []

    for row in portal_rows:
        # Get product name from portal
        portal_name = ''
        for key in [product_col_key, 'Product', 'ProductName', 'Item', 'Product Name']:
            portal_name = row.get(key, '').strip()
            if portal_name:
                break
        if not portal_name:
            skipped += 1
            continue

        # Get quantity
        qty_str = ''
        for key in [qty_col_key, 'Qty', 'Quantity', 'Sold Qty']:
            qty_str = str(row.get(key, '')).strip()
            if qty_str and qty_str not in ('', '0', '0.0'):
                break
        try:
            qty = float(qty_str) if qty_str else 0.0
        except ValueError:
            qty = 0.0
        if qty <= 0:
            skipped += 1
            continue

        # Get date
        date_str = ''
        for key in [date_col_key, 'Date', 'InvoiceDate', 'Sale Date']:
            date_str = str(row.get(key, '')).strip()
            if date_str:
                break
        try:
            sale_date = datetime.strptime(date_str, '%d/%m/%Y')
        except Exception:
            try:
                sale_date = datetime.strptime(date_str, '%Y-%m-%d')
            except Exception:
                sale_date = datetime.now()

        # Find the correct week column
        week_col_name = get_week_column(sale_date, headers)
        if not week_col_name:
            print(f'[SYNC] No week column for date {date_str} — skipping {portal_name}')
            skipped += 1
            continue

        week_col_idx = header_to_col.get(week_col_name)
        if not week_col_idx:
            skipped += 1
            continue

        # Match product by name (fuzzy: check if portal name is substring of inv name or vice versa)
        excel_row = None
        portal_lower = portal_name.lower()
        for inv_name, row_num in inv_products.items():
            if portal_lower in inv_name or inv_name in portal_lower:
                excel_row = row_num
                break
            # Also try first 10 chars match
            if portal_lower[:10] == inv_name[:10]:
                excel_row = row_num
                break

        if not excel_row:
            not_found.append(portal_name)
            skipped += 1
            continue

        # Read existing value and add qty (accumulate, don't overwrite)
        current = ws.Cells(excel_row, week_col_idx).Value
        try:
            current_qty = float(current) if current else 0.0
        except Exception:
            current_qty = 0.0

        new_qty = current_qty + qty
        ws.Cells(excel_row, week_col_idx).Value = new_qty
        print(f'[SYNC] ✓ {portal_name} | {week_col_name} | +{qty} → {new_qty}')
        updated += 1

    # Save the workbook
    wb.Save()

    print(f'\n[SYNC] ══ DONE ══')
    print(f'[SYNC] Updated: {updated} | Skipped: {skipped}')
    if not_found:
        print(f'[SYNC] NOT MATCHED ({len(not_found)}):')
        for name in not_found[:10]:
            print(f'       - {name}')

    return {'updated': updated, 'skipped': skipped, 'not_found': not_found}


def run_sync(from_date: str, to_date: str):
    """Main entry point for sync."""
    print(f'[SYNC] Starting portal → Excel sync: {from_date} → {to_date}')
    portal_rows = login_and_get_data(from_date, to_date)
    if not portal_rows:
        return {'error': 'No data fetched from portal', 'updated': 0}
    result = sync_to_excel(portal_rows)
    return result


if __name__ == '__main__':
    # Default: sync today only
    today = datetime.now().strftime('%d/%m/%Y')
    from_d = sys.argv[1] if len(sys.argv) > 1 else today
    to_d   = sys.argv[2] if len(sys.argv) > 2 else today
    run_sync(from_d, to_d)
