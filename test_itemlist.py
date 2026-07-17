from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = browser.new_context()
        page = ctx.new_page()
        
        print("Logging in...")
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        
        print("Navigating to Sale Order...")
        page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
        
        page.fill('#ctl00_ContentPlaceHolder1_txtid', '97880D')
        page.keyboard.press('Tab')
        page.wait_for_timeout(3000)
        
        options = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('#ctl00_ContentPlaceHolder1_itemlist option')).map(o => ({val: o.value, text: o.text}));
        }''')
        print(options)
        
        browser.close()

if __name__ == '__main__':
    run()
