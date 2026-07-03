from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta

p = sync_playwright().start()
browser = p.chromium.launch(headless=True)
ctx = browser.new_context()
page = ctx.new_page()

page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
page.wait_for_load_state('networkidle')

# Try the DS Sale Report which has product-level breakdown
page.goto('https://asclepiuswellness.com/shoppingpoint/spDSSaleReport.aspx', wait_until='networkidle')
page.screenshot(path='ds_sale_report.png', full_page=True)
print('DS Sale Report URL:', page.url)
for el in page.query_selector_all('input, select'):
    print(el.get_attribute('id'), '|', el.get_attribute('type'))

browser.close()
p.stop()
