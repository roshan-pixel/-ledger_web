"""
Full FSalesInvoiceList scraper.
- Date: 01/01/2026 -> today
- Scrapes all rows from the GV table (all on one page, no pagination)
- For each invoice fetches spSalesInvoiceListDetails.aspx?TId=XXX for product items
- Upserts into ledger.db invoices table
"""
import json
import sqlite3
import re
from pathlib import Path
from datetime import date
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

LOGIN_URL   = 'https://asclepiuswellness.com/login.aspx?webid=1'
INVOICE_URL = 'https://asclepiuswellness.com/shoppingpoint/FSalesInvoiceList.aspx'
DETAIL_BASE = 'https://asclepiuswellness.com/shoppingpoint/spSalesInvoiceListDetails.aspx?TId='
DATE_FROM   = '01/01/2026'
DATE_TO     = date.today().strftime('%d/%m/%Y')
DB_PATH     = str(Path(__file__).parent / 'ledger.db')


def parse_detail_page(html):
    """Parse spSalesInvoiceListDetails.aspx — returns list of product dicts."""
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for tbl in soup.find_all('table'):
        rows = tbl.find_all('tr')
        if not rows:
            continue
        hdrs = [h.text.strip().lower() for h in rows[0].find_all(['th','td'])]
        hdr_str = ' '.join(hdrs)
        if 'product' in hdr_str or 'item' in hdr_str or 'name' in hdr_str or 'rate' in hdr_str:
            print(f"    detail table hdrs: {hdrs[:8]}")
            for tr in rows[1:]:
                tds = tr.find_all('td')
                cells = [t.text.strip() for t in tds]
                if any(cells) and len(cells) >= 3:
                    items.append(cells)
            break
    return items


def cells_to_item(cells):
    """Convert a detail page row to an invoice item dict."""
    # Typical columns: Sr, Code, Name, HSN, Rate, Qty, Amount, IGST%, IGST, Net, SP, BV
    if len(cells) < 6:
        return None
    try:
        name  = cells[2] if len(cells) > 2 else ''
        rate  = float(cells[4].replace(',','')) if len(cells) > 4 and cells[4] else 0
        qty   = int(float(cells[5].replace(',',''))) if len(cells) > 5 and cells[5] else 0
        total = float(cells[6].replace(',','')) if len(cells) > 6 and cells[6] else rate * qty
        sp    = float(cells[10].replace(',','')) if len(cells) > 10 and cells[10] else 0
        return {'name': name, 'qty': qty, 'price': rate, 'total': total, 'description': name, 'sp': sp}
    except Exception:
        return None


def main():
    print("=" * 65)
    print(f"Sales Invoice Scraper  {DATE_FROM} -> {DATE_TO}")
    print("=" * 65)

    all_invoices = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()
        page.on('dialog', lambda d: d.accept())

        # LOGIN
        print("Logging in...")
        page.goto(LOGIN_URL)
        page.wait_for_timeout(2000)
        page.evaluate("""() => {
            ['ctl00_ContentPlaceHolder1_txtspUserid',
             'ctl00_ContentPlaceHolder1_txtsppassword'].forEach(id => {
                const el = document.getElementById(id);
                if(el){let c=el;while(c&&c!==document.body){c.style.display='block';c=c.parentElement;}}
            });
        }""")
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtspUserid"]', 'AAZFD8117G', force=True)
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtsppassword"]', 'ABC@1234', force=True)
        page.click('input[name="ctl00$ContentPlaceHolder1$btnfranlogin"]', force=True)
        page.wait_for_timeout(3000)

        # LOAD INVOICE LIST
        print(f"Loading invoice list {DATE_FROM} -> {DATE_TO}...")
        page.goto(INVOICE_URL)
        page.wait_for_timeout(4000)
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtFrom"]', DATE_FROM)
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtTo"]',   DATE_TO)
        page.click('input[id="ctl00_ContentPlaceHolder1_btnshow"]')
        page.wait_for_timeout(5000)

        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        gv   = soup.find('table', id='ctl00_ContentPlaceHolder1_GV')
        if not gv:
            print("ERROR: GV table not found!")
            browser.close()
            return

        # Parse all rows
        # Cols: SNo|TId|BillNo|BillNo|DSCode|DSName|Date|ShipAddr|Mobile|Pincode|
        #       Amount|CGST|SGST|IGST|TaxAmt|...|Total|...|SP|BV|DelivDate|StockPoint|...|UpdateShip
        data_rows = [tr for tr in gv.find_all('tr') if tr.find_all('td')]
        print(f"Found {len(data_rows)} invoice rows.")

        # Extract TId from links (for detail fetch)
        # Each row has a link: spSalesInvoiceListDetails.aspx?TId=XXXXX
        for i, tr in enumerate(data_rows):
            tds   = tr.find_all('td')
            cells = [t.text.strip() for t in tds]

            # Skip totals row (no bill number pattern)
            if not cells or not (len(cells) > 2 and re.match(r'DSR/', cells[2] or '')):
                print(f"  [{i+1}] Skipping (totals/empty row): {cells[:4]}")
                continue

            # Extract TId from detail link
            tid = None
            for a in tr.find_all('a'):
                href = a.get('href','')
                m = re.search(r'TId=(\d+)', href)
                if m:
                    tid = m.group(1)
                    break
            if not tid:
                # Try to get from the text of second cell
                tid = cells[1] if cells[1].isdigit() else None

            inv_no       = cells[2]  if len(cells) > 2  else ''
            ds_code      = cells[4]  if len(cells) > 4  else ''
            ds_name      = cells[5]  if len(cells) > 5  else ''
            raw_inv_date = cells[6]  if len(cells) > 6  else ''
            ship_addr    = cells[7]  if len(cells) > 7  else ''
            mobile       = cells[8]  if len(cells) > 8  else ''
            pincode      = cells[9]  if len(cells) > 9  else ''
            amount_raw   = cells[10] if len(cells) > 10 else '0'
            total_raw    = cells[17] if len(cells) > 17 else '0'
            sp_raw       = cells[20] if len(cells) > 20 else '0'
            bv_raw       = cells[21] if len(cells) > 21 else '0'
            raw_del_date = cells[22] if len(cells) > 22 else ''
            stock_point  = cells[23] if len(cells) > 23 else ''

            # Date formatter helper
            import datetime
            def to_iso_date(d_str):
                if not d_str: return ''
                d_str = d_str.strip()
                for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
                    try:
                        return datetime.datetime.strptime(d_str[:10], fmt).strftime('%Y-%m-%d')
                    except ValueError:
                        pass
                return d_str

            inv_date = to_iso_date(raw_inv_date)
            delivery_dt = to_iso_date(raw_del_date)

            try: amount = float(amount_raw.replace(',',''))
            except: amount = 0.0
            try: total  = float(total_raw.replace(',',''))
            except: total = 0.0
            try: sp     = float(sp_raw.replace(',',''))
            except: sp = 0.0

            print(f"  [{i+1}/{len(data_rows)}] {inv_no}  {inv_date}  {ds_name[:20]}  total={total}  tid={tid}", end='', flush=True)

            # Fetch product detail
            items = []
            items_json = '[]'
            if tid:
                try:
                    det_page = browser.new_page()
                    det_page.on('dialog', lambda d: d.accept())
                    det_page.goto(DETAIL_BASE + tid)
                    det_page.wait_for_timeout(2000)
                    det_html  = det_page.content()
                    det_page.close()
                    raw_items = parse_detail_page(det_html)
                    for row in raw_items:
                        item = cells_to_item(row)
                        if item:
                            items.append(item)
                    items_json = json.dumps(items, ensure_ascii=False)
                    print(f"  → {len(items)} items")
                except Exception as e:
                    print(f"  → detail error: {e}")
            else:
                print()

            all_invoices.append({
                'invoice_no':    inv_no,
                'ds_code':       ds_code,
                'customer_name': ds_name,
                'amount':        total,
                'date_created':  inv_date,
                'items':         items_json,
                'status':        'active',
                'total_sp':      sp,
                'is_dispatched': 1,
                'remark':        ship_addr,
                'tid':           tid,
                'mobile':        mobile,
                'delivery_date': delivery_dt,
                'stock_point':   stock_point,
            })

        browser.close()

    # UPSERT INTO DB
    print(f"\nUpserting {len(all_invoices)} invoices into DB...")
    conn = sqlite3.connect(DB_PATH)
    c    = conn.cursor()

    # Add new columns if missing
    c.execute("PRAGMA table_info(invoices)")
    existing_cols = {row[1] for row in c.fetchall()}
    for col, dtype in [('tid','TEXT'), ('mobile','TEXT'), ('delivery_date','TEXT'), ('stock_point','TEXT')]:
        if col not in existing_cols:
            c.execute(f"ALTER TABLE invoices ADD COLUMN {col} {dtype}")
            print(f"  Added column: {col}")

    inserted = 0
    updated  = 0
    for inv in all_invoices:
        c.execute("SELECT id FROM invoices WHERE invoice_no=?", (inv['invoice_no'],))
        row = c.fetchone()
        if row:
            c.execute("""UPDATE invoices SET ds_code=?, customer_name=?, amount=?,
                         date_created=?, items=?, status=?, total_sp=?, is_dispatched=?,
                         remark=?, tid=?, mobile=?, delivery_date=?, stock_point=?
                         WHERE invoice_no=?""",
                      (inv['ds_code'], inv['customer_name'], inv['amount'],
                       inv['date_created'], inv['items'], inv['status'],
                       inv['total_sp'], inv['is_dispatched'], inv['remark'],
                       inv['tid'], inv['mobile'], inv['delivery_date'],
                       inv['stock_point'], inv['invoice_no']))
            updated += 1
        else:
            c.execute("""INSERT INTO invoices
                         (invoice_no, ds_code, customer_name, amount, date_created,
                          items, status, total_sp, is_dispatched, remark,
                          tid, mobile, delivery_date, stock_point)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (inv['invoice_no'], inv['ds_code'], inv['customer_name'],
                       inv['amount'], inv['date_created'], inv['items'],
                       inv['status'], inv['total_sp'], inv['is_dispatched'],
                       inv['remark'], inv['tid'], inv['mobile'],
                       inv['delivery_date'], inv['stock_point']))
            inserted += 1

    conn.commit()
    conn.close()
    print(f"\nDone! Inserted: {inserted}  Updated: {updated}  Total: {len(all_invoices)}")


if __name__ == '__main__':
    main()
