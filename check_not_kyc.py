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
        
        page.goto('https://asclepiuswellness.com/shoppingpoint/ApproveRepurchase.aspx', wait_until='networkidle')
        
        # Change status to "Not Complete KYC" (value = '0')
        page.select_option('#ctl00_ContentPlaceHolder1_ddlkycstatus', value='0')
        page.wait_for_timeout(500)
        
        # Find the actual Show button ID
        buttons = page.evaluate("""
            Array.from(document.querySelectorAll('input[type="submit"], button')).map(b => ({id: b.id, value: b.value || b.innerText}))
        """)
        print("Buttons:", buttons)
        
        # Click whichever Show button exists
        for btn in buttons:
            if 'show' in (btn.get('value','') or '').lower() or 'show' in (btn.get('id','') or '').lower():
                print("Clicking:", btn)
                page.click(f"#{btn['id']}")
                break
        
        page.wait_for_load_state('networkidle')
        
        html = page.content()
        if '9176AF94' in html:
            print("YES! 9176AF94 IS IN NOT-COMPLETE-KYC LIST!!")
        else:
            print("Not found in Not Complete KYC list either.")
            
        page.screenshot(path='not_kyc_list.png', full_page=True)
        print("Screenshot saved.")
        
        browser.close()

if __name__ == '__main__':
    check()
