from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='domcontentloaded', timeout=30000)
    page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
    page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
    page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
    page.wait_for_load_state('domcontentloaded')

    page.goto('https://asclepiuswellness.com/shoppingpoint/FSalesInvoiceList.aspx', wait_until='domcontentloaded')

    for date_range in [('10/09/2026', '15/09/2026'), ('12/09/2026', '12/09/2026'), ('15/09/2026', '15/09/2026')]:
        f_date, t_date = date_range
        print(f"\n--- Checking date range: {f_date} to {t_date} ---")
        page.fill('#ctl00_ContentPlaceHolder1_txtFrom', f_date)
        page.fill('#ctl00_ContentPlaceHolder1_txtTo', t_date)
        page.click('#ctl00_ContentPlaceHolder1_btnshow')
        page.wait_for_timeout(4000)

        rows = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('table tr')).map(tr => tr.innerText.trim()).filter(t => t.length > 0);
        }""")
        print(f"Total rows found: {len(rows)}")
        for r in rows:
            print("Row:", r.replace('\t', ' | ')[:140])

    browser.close()
