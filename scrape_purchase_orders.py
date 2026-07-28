"""
Full purchase history scraper.
- Date range: 01/06/2026 → 26/07/2026
- Fetches each row from GV table
- Clicks 'Detail' for each bill to get product breakdown
- Saves to purchase_orders.json
"""
import json
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

LOGIN_URL    = 'https://asclepiuswellness.com/login.aspx?webid=1'
PURCHASE_URL = 'https://asclepiuswellness.com/shoppingpoint/PurchaseListn.aspx'
DATE_FROM    = '01/06/2026'
DATE_TO      = '31/07/2026'
OUT_FILE     = 'purchase_orders.json'


def get_gv_rows(soup):
    gv = soup.find('table', id='ctl00_ContentPlaceHolder1_GV')
    if not gv:
        return []
    rows = []
    for i, tr in enumerate(gv.find_all('tr')):
        tds = tr.find_all('td')
        if not tds:
            continue
        rows.append(tds)
    return rows


def parse_bill_detail(soup):
    """Parse product table from the bill detail page."""
    products = []
    for tbl in soup.find_all('table'):
        rows = tbl.find_all('tr')
        if not rows:
            continue
        hdrs = [h.text.strip().lower() for h in rows[0].find_all(['th', 'td'])]
        hdr_str = ' '.join(hdrs)
        if 'product' in hdr_str or 'item' in hdr_str or 'rate' in hdr_str or 'qty' in hdr_str:
            print(f"    Bill detail table headers: {hdrs}")
            for tr in rows[1:]:
                tds = tr.find_all('td')
                if tds:
                    products.append([t.text.strip() for t in tds])
            break
    # fallback: just grab the biggest table
    if not products:
        biggest = None
        max_rows = 0
        for tbl in soup.find_all('table'):
            r = tbl.find_all('tr')
            if len(r) > max_rows and len(r) > 2:
                biggest = tbl
                max_rows = len(r)
        if biggest:
            for tr in biggest.find_all('tr')[1:]:
                tds = tr.find_all('td')
                if tds:
                    products.append([t.text.strip() for t in tds])
    return products


def main():
    print("=" * 60)
    print(f"Purchase History Scraper  {DATE_FROM} → {DATE_TO}")
    print("=" * 60)

    orders = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page()
        page.on('dialog', lambda d: d.accept())

        # LOGIN
        print("Logging in …")
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

        def load_purchase_page():
            page.goto(PURCHASE_URL)
            page.wait_for_timeout(4000)
            page.fill('input[name="ctl00$ContentPlaceHolder1$txtFrom"]', DATE_FROM)
            page.fill('input[name="ctl00$ContentPlaceHolder1$txtTo"]',   DATE_TO)
            page.click('input[id="ctl00_ContentPlaceHolder1_btnshow"]')
            page.wait_for_timeout(4000)

        load_purchase_page()

        # PARSE MAIN TABLE
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        gv   = soup.find('table', id='ctl00_ContentPlaceHolder1_GV')

        if not gv:
            print("ERROR: Main GV table not found!")
            browser.close()
            return

        data_rows = [tr for tr in gv.find_all('tr') if tr.find_all('td')]
        print(f"Found {len(data_rows)} orders.")

        # Print full header
        hdr_row = gv.find('tr')
        if hdr_row:
            hdrs = [h.text.strip() for h in hdr_row.find_all(['th', 'td'])]
            print(f"Columns: {hdrs}")

        for i, tr in enumerate(data_rows):
            tds   = tr.find_all('td')
            cells = [t.text.strip() for t in tds]
            print(f"\n[{i+1}] Bill={cells[2] if len(cells)>2 else '?'}  Date={cells[4] if len(cells)>4 else '?'}")
            print(f"     Cells: {cells}")

            order = {
                'sr':         cells[0]  if len(cells) > 0  else '',
                'bill_no':    cells[2]  if len(cells) > 2  else '',
                'party':      cells[3]  if len(cells) > 3  else '',
                'date':       cells[4]  if len(cells) > 4  else '',
                'cgst':       cells[5]  if len(cells) > 5  else '',
                'sgst':       cells[6]  if len(cells) > 6  else '',
                'igst':       cells[7]  if len(cells) > 7  else '',
                'total':      cells[10] if len(cells) > 10 else '',
                'lr_no':      cells[17] if len(cells) > 17 else '',
                'delivery_date': cells[18] if len(cells) > 18 else '',
                'courier':    cells[20] if len(cells) > 20 else '',
                'products':   []
            }

            # Click Detail link (col index 1)
            detail_links = tds[1].find_all('a') if len(tds) > 1 else []
            print(f"     Detail links: {[(a.text.strip(), a.get('href',''), a.get('onclick','')) for a in detail_links]}")

            if detail_links:
                try:
                    # Try clicking by text
                    detail_text = detail_links[0].text.strip()
                    # Use row index to find the right link on current page
                    all_detail_links = page.query_selector_all(
                        '#ctl00_ContentPlaceHolder1_GV a'
                    )
                    # Find the link matching this row
                    clicked = False
                    for lnk in all_detail_links:
                        if lnk.inner_text().strip() in ('Detail', 'View', 'detail'):
                            parent_row = lnk.evaluate('el => el.closest("tr")')
                            if parent_row:
                                row_cells = page.query_selector_all(
                                    'tr:has(a[id*="' + (lnk.get_attribute('id') or '') + '"])'
                                )
                            # Just click based on position
                            break

                    # Simpler: click the i-th "Detail" link in the table
                    nth_link = page.query_selector(
                        f'#ctl00_ContentPlaceHolder1_GV tr:nth-child({i+2}) td:nth-child(2) a'
                    )
                    if nth_link:
                        print(f"     Clicking detail for row {i+2}…")
                        with page.expect_navigation(wait_until='networkidle', timeout=10000):
                            nth_link.click()
                        page.wait_for_timeout(2000)

                        detail_html = page.content()
                        detail_soup = BeautifulSoup(detail_html, 'html.parser')

                        # Dump all tables on detail page
                        print(f"     Detail page tables:")
                        for j, tbl2 in enumerate(detail_soup.find_all('table')):
                            rows2 = tbl2.find_all('tr')
                            h2 = [c.text.strip() for c in rows2[0].find_all(['th','td'])] if rows2 else []
                            print(f"       [{j}] id={tbl2.get('id','no-id')!r} rows={len(rows2)} hdrs={h2[:8]}")
                            if len(rows2) > 1:
                                r1 = [c.text.strip()[:20] for c in rows2[1].find_all('td')]
                                print(f"            row1={r1}")

                        prods = parse_bill_detail(detail_soup)
                        order['products'] = prods
                        print(f"     → {len(prods)} product rows")

                        # Go back
                        page.go_back()
                        page.wait_for_timeout(2000)
                        # Re-submit date range (postback resets the page)
                        try:
                            page.fill('input[name="ctl00$ContentPlaceHolder1$txtFrom"]', DATE_FROM)
                            page.fill('input[name="ctl00$ContentPlaceHolder1$txtTo"]',   DATE_TO)
                            page.click('input[id="ctl00_ContentPlaceHolder1_btnshow"]')
                            page.wait_for_timeout(3000)
                        except Exception:
                            load_purchase_page()

                    else:
                        print(f"     No nth-link found for row {i+2}")

                except Exception as e:
                    print(f"     ERROR clicking detail: {e}")
                    try:
                        load_purchase_page()
                    except Exception:
                        pass

            orders.append(order)

        browser.close()

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)
    print(f"\n{'='*60}")
    print(f"Saved {len(orders)} orders to {OUT_FILE}")
    for o in orders:
        print(f"  {o['bill_no']}  {o['date']}  total={o['total']}  products={len(o['products'])}")

if __name__ == '__main__':
    main()
