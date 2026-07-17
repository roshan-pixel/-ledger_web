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
        
        page.goto('https://asclepiuswellness.com/shoppingpoint/FSalesInvoiceList.aspx', wait_until='networkidle')
        
        try:
            page.click('#ctl00_ContentPlaceHolder1_btnshow')
            page.wait_for_load_state('networkidle')
        except:
            print("No btnshow found")
        
        html = page.content()
        if '9176AF94' in html:
            print("FOUND IN FSalesInvoiceList!")
        else:
            print("Not in FSalesInvoiceList")
            
        browser.close()

if __name__ == '__main__':
    check()
