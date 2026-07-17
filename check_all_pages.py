from playwright.sync_api import sync_playwright

def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        page.on("dialog", lambda dialog: dialog.accept())
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        
        urls = [
            'https://asclepiuswellness.com/shoppingpoint/ApproveRepurchase.aspx',
            'https://asclepiuswellness.com/shoppingpoint/FSalesInvoiceList.aspx',
            'https://asclepiuswellness.com/shoppingpoint/ApproveRepurchaseCustomer.aspx',
            'https://asclepiuswellness.com/shoppingpoint/spcustomersalelist.aspx',
            'https://asclepiuswellness.com/shoppingpoint/PendingCftoFranchise.aspx',
            'https://asclepiuswellness.com/shoppingpoint/spDSSaleReport.aspx'
        ]
        
        found = False
        for url in urls:
            try:
                page.goto(url, wait_until='networkidle')
                if '9176AF94' in page.content():
                    print(f"FOUND IN: {url}")
                    found = True
            except:
                pass
                
        if not found:
            print("Not found in any of those pages.")
            
        browser.close()

if __name__ == '__main__':
    check()
