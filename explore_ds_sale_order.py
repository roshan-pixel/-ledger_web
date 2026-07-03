from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        
        # Login
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        
        # Navigate to Sale Order
        page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
        
        # Type a DS code and see what happens?
        # But first let's see what inputs exist
        inputs = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('input')).map(i => ({id: i.id, name: i.name, type: i.type, value: i.value}));
        }''')
        print("Inputs:", inputs)
        
        spans = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('span')).map(s => ({id: s.id, text: s.innerText.trim()})).filter(s => s.id.toLowerCase().includes('name'));
        }''')
        print("Spans with 'name' in ID:", spans)
        
        page.screenshot(path='ds_sale_order.png')
        browser.close()

if __name__ == '__main__':
    run()
