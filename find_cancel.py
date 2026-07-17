from playwright.sync_api import sync_playwright

def cancel_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        page.on("dialog", lambda dialog: dialog.accept())
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        
        page.goto('https://asclepiuswellness.com/shoppingpoint/ApproveRepurchase.aspx', wait_until='networkidle')
        page.select_option('#ctl00_ContentPlaceHolder1_ddlkycstatus', value='0')
        page.wait_for_timeout(500)
        page.click('#ctl00_ContentPlaceHolder1_Button1')
        page.wait_for_load_state('networkidle')
        
        # Get all cancel buttons on the page (rows for 9176AF94 test entries)
        cancel_btns = page.evaluate("""
            Array.from(document.querySelectorAll('input[value="Cancel"], button')).filter(b => b.value === 'Cancel' || b.innerText === 'Cancel').map(b => b.id)
        """)
        print(f"Found {len(cancel_btns)} cancel buttons:", cancel_btns)
        
        # Count checkboxes and look for select all
        checkboxes = page.evaluate("""
            Array.from(document.querySelectorAll('input[type="checkbox"]')).map(c => ({id: c.id, name: c.name}))
        """)
        print("Checkboxes:", checkboxes[:5])
        
        browser.close()

if __name__ == '__main__':
    cancel_all()
