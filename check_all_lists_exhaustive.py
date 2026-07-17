from playwright.sync_api import sync_playwright

LINKS = [
    'https://asclepiuswellness.com/shoppingpoint/SpdistributorSaleKit.aspx',
    'https://asclepiuswellness.com/shoppingpoint/ApproveRepurchase.aspx',
    'https://asclepiuswellness.com/shoppingpoint/ApproveRepurchaseCustomer.aspx',
    'https://asclepiuswellness.com/shoppingpoint/spcustomersalelist.aspx',
    'https://asclepiuswellness.com/shoppingpoint/PendingCftoFranchise.aspx',
    'https://asclepiuswellness.com/shoppingpoint/CFFranchiseSalesInvoiceList.aspx',
    'https://asclepiuswellness.com/shoppingpoint/spDSSaleReport.aspx',
    'https://asclepiuswellness.com/shoppingpoint/PurchaseListn.aspx'
]

def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        
        for link in LINKS:
            print("Checking", link)
            page.goto(link, wait_until='networkidle')
            html = page.content()
            if "9176AF94" in html:
                print(f"!!! FOUND 9176AF94 IN {link} !!!")
                
        browser.close()

if __name__ == '__main__':
    check()
