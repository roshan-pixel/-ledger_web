from playwright.sync_api import sync_playwright

def check_approval():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
            ctx = browser.new_context()
            page = ctx.new_page()
            
            print("Logging in...")
            page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
            page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
            page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
            page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
            page.wait_for_load_state('networkidle')
            
            print("Navigating to Approve Repurchase...")
            page.goto('https://asclepiuswellness.com/shoppingpoint/ApproveRepurchase.aspx', wait_until='networkidle')
            
            print("Filtering for DS Code 67864B5B...")
            page.fill('#ctl00_ContentPlaceHolder1_txtMid', '67864B5B')
            page.click('#ctl00_ContentPlaceHolder1_Button1')
            page.wait_for_timeout(3000)
            
            page.screenshot(path='test_approve.png', full_page=True)
            print("Screenshot taken as test_approve.png")
            
            html = page.evaluate('document.querySelector("#ctl00_ContentPlaceHolder1_GridView1") ? document.querySelector("#ctl00_ContentPlaceHolder1_GridView1").innerHTML : "No GridView"')
            print("Results:", html[:500])
            browser.close()
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    check_approval()
