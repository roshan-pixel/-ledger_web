from playwright.sync_api import sync_playwright

def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        
        # Check ApproveRepurchase but change Status filter to ALL
        page.goto('https://asclepiuswellness.com/shoppingpoint/ApproveRepurchase.aspx', wait_until='networkidle')
        
        # Change Select Status dropdown to "All" or "" 
        status_options = page.evaluate("""
            Array.from(document.querySelectorAll('[id*="Status"] option, [id*="status"] option, select option')).map(o => ({value: o.value, text: o.text}))
        """)
        print("Status options:", status_options)
        
        # Get the ID of the status dropdown
        status_sel = page.evaluate("""
            Array.from(document.querySelectorAll('select')).map(s => ({id: s.id, options: Array.from(s.options).map(o => o.text)}))
        """)
        print("All selects:", status_sel)
        
        browser.close()

if __name__ == '__main__':
    check()
