from playwright.sync_api import sync_playwright
import time

def check():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        # Listen for dialogs and print them
        def on_dialog(dialog):
            dialog.accept()
        page.on("dialog", on_dialog)
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
        
        page.fill('#ctl00_ContentPlaceHolder1_txtid', '9176AF94')
        page.keyboard.press('Tab')
        page.wait_for_timeout(4000)
        
        # Add item
        page.select_option('#ctl00_ContentPlaceHolder1_itemlist', '38')
        page.wait_for_timeout(1000)
        page.fill('#ctl00_ContentPlaceHolder1_txtqty', '1')
        page.click('#ctl00_ContentPlaceHolder1_btnadd')
        page.wait_for_timeout(3000)
        
        # Save
        page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
        page.wait_for_load_state('networkidle', timeout=10000)
            
        page.screenshot(path='C:/Users/sgarm/Downloads/ledger_web/after_save.png', full_page=True)
            
        browser.close()

if __name__ == '__main__':
    check()
