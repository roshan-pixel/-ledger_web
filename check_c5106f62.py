from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        page.on("dialog", lambda dialog: dialog.accept())
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')

        page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
        
        # Check C5106F62
        page.fill('#ctl00_ContentPlaceHolder1_txtid', 'C5106F62')
        page.keyboard.press('Tab')
        page.wait_for_timeout(4000)
        
        name = page.locator('#ctl00_ContentPlaceHolder1_txtname').input_value()
        print("Name:", name)
        
        # Check if SAO/SGO radio buttons are visible
        sao_visible = page.is_visible('#ctl00_ContentPlaceHolder1_rbsao')
        sgo_visible = page.is_visible('#ctl00_ContentPlaceHolder1_rbSgo')
        print("SAO visible:", sao_visible)
        print("SGO visible:", sgo_visible)
        
        # Check if it's a Green or Red ID
        # The radio buttons presence indicates Green ID
        sao_exists = page.locator('#ctl00_ContentPlaceHolder1_rbsao').count() > 0
        print("SAO exists (Green ID):", sao_exists)
        
        browser.close()

if __name__ == '__main__':
    test()
