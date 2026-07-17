from playwright.sync_api import sync_playwright
import re

def test_submit():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        # Handle all dialogs by accepting them
        page.on("dialog", lambda dialog: (print("DIALOG:", dialog.message), dialog.accept()))
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')

        ds_code = '9176AF94'
        page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
        
        page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
        page.keyboard.press('Tab')
        page.wait_for_timeout(4000)
        
        page.check('#ctl00_ContentPlaceHolder1_chkaddr')
        page.wait_for_timeout(1000)
        
        desc = "BRAINDOC PRAVAHI KWATH [52] -"
        match = re.search(r'\[(\d+)\]', desc)
        if match:
            prod_id = match.group(1)
            page.select_option('#ctl00_ContentPlaceHolder1_itemlist', value=prod_id)
            page.wait_for_timeout(1000)
            page.fill('#ctl00_ContentPlaceHolder1_txtqty', '1')
            page.click('#ctl00_ContentPlaceHolder1_btnadd')
            page.wait_for_timeout(2000)
        
        page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
        page.wait_for_load_state('networkidle', timeout=15000)
        
        # check html
        html = page.content()
        with open("after_save_html.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        browser.close()

if __name__ == '__main__':
    test_submit()
