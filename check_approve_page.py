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
        
        # Go to Approve Repurchase page
        page.goto('https://www.asclepiuswellness.com/shoppingpoint/ApproveRepurchase.aspx', wait_until='networkidle')
        
        # Extract rows
        rows = page.evaluate('''() => {
            const trs = Array.from(document.querySelectorAll('#ctl00_ContentPlaceHolder1_GridView1 tr'));
            return trs.map(tr => tr.innerText.replace(/\\t/g, ' | '));
        }''')
        
        for row in rows:
            print(row)
            
        browser.close()

if __name__ == '__main__':
    check()
