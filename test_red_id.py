from playwright.sync_api import sync_playwright
import re

def test_submit():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        # Handle all dialogs by accepting them
        page.on("dialog", lambda dialog: (print("DIALOG:", dialog.message), dialog.accept()))
        
        print("Logging in...")
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        print("Logged in!")

        ds_code = '9176AF94'
        order_type = 'approve'
        
        print(f"Submitting for {ds_code}, type={order_type}")
        page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
        
        print("Filling DS code...")
        page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
        page.keyboard.press('Tab')
        
        # Wait for name and items to load via AJAX
        page.wait_for_timeout(4000)
        print("Name should be loaded.")
        
        # 2. Select Order Type (SAO vs SGO)
        if order_type == 'sao':
            try:
                if page.is_visible('#ctl00_ContentPlaceHolder1_rbsao', timeout=3000):
                    page.click('#ctl00_ContentPlaceHolder1_rbsao')
                    print(f"[{ds_code}] Selected SAO radio button.")
            except Exception as e:
                print(f"[{ds_code}] Could not select SAO: {e}")
        elif order_type == 'sgo':
            try:
                if page.is_visible('#ctl00_ContentPlaceHolder1_rbSgo', timeout=3000):
                    page.click('#ctl00_ContentPlaceHolder1_rbSgo')
                    print(f"[{ds_code}] Selected SGO radio button.")
            except Exception as e:
                print(f"[{ds_code}] Could not select SGO: {e}")
        
        print("Checking address...")
        page.check('#ctl00_ContentPlaceHolder1_chkaddr')
        page.wait_for_timeout(1000)
        
        print("Adding item [52]...")
        desc = "BRAINDOC PRAVAHI KWATH [52] -"
        match = re.search(r'\[(\d+)\]', desc)
        if match:
            prod_id = match.group(1)
            try:
                # Use value instead of label for reliable selection
                page.select_option('#ctl00_ContentPlaceHolder1_itemlist', value=prod_id)
                page.wait_for_timeout(1000)
                page.fill('#ctl00_ContentPlaceHolder1_txtqty', '1')
                page.click('#ctl00_ContentPlaceHolder1_btnadd')
                page.wait_for_timeout(2000)
                print("Item added!")
            except Exception as e:
                print(f"Failed to add item: {e}")
        
        print("Clicking save...")
        page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
        print("Waiting for network idle...")
        page.wait_for_load_state('networkidle', timeout=15000)
        print("Done wait!")
        
        # check html
        html = page.content()
        if "Bill Save Successfully" in html or "Total Amount" not in html:
            print("Looks like it saved? (or redirected)")
        else:
            print("Did not save. Checking for error messages...")
            errors = page.evaluate("document.querySelector('#ctl00_ContentPlaceHolder1_lblMsg')?.innerText")
            print("Error lblMsg:", errors)
            
        browser.close()

if __name__ == '__main__':
    test_submit()
