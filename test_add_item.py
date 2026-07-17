from playwright.sync_api import sync_playwright

def test_add_item():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
            ctx = browser.new_context()
            page = ctx.new_page()
            
            page.on("dialog", lambda dialog: (print("ALERT:", dialog.message), dialog.accept()))
            
            print("Logging in...")
            page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
            page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
            page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
            page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
            page.wait_for_load_state('networkidle')
            
            print("Navigating to Sale Order...")
            page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
            
            ds_code = '67864B5B'
            page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
            page.keyboard.press('Tab')
            
            print("Waiting for DS details to load...")
            page.wait_for_timeout(4000)
            
            print("Selecting SAO...")
            page.click('#ctl00_ContentPlaceHolder1_rbsao')
            page.wait_for_timeout(1000)
            
            print("Checking 'Same As Profile Address'...")
            page.check('#ctl00_ContentPlaceHolder1_chkaddr')
            page.wait_for_timeout(1000)
            
            # Copy mobile to shipping mobile
            mobile = page.input_value('#ctl00_ContentPlaceHolder1_txtmobile')
            if mobile:
                page.fill('#ctl00_ContentPlaceHolder1_ShipMobile', mobile)
                
            # Extract pincode from address and fill
            address = page.input_value('#ctl00_ContentPlaceHolder1_txtaddress')
            if address:
                import re
                match = re.search(r'\b\d{6}\b', address)
                if match:
                    page.fill('#ctl00_ContentPlaceHolder1_txtshpingpincode', match.group(0))
                else:
                    page.fill('#ctl00_ContentPlaceHolder1_txtshpingpincode', '000000')
                    
            name = page.input_value('#ctl00_ContentPlaceHolder1_txtname')
            print("Found Name:", name)
            
            options = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('#ctl00_ContentPlaceHolder1_itemlist option')).map(o => ({val: o.value, text: o.text}));
            }''')
            if options and "select" in options[0]['text'].lower():
                options = options[1:]
                
            # Try to add 'HAIRDOC OIL 200 ML'
            desc = 'HAIRDOC OIL 200 ML'.upper()
            best_match = None
            for opt in options:
                opt_text = opt['text'].strip().upper()
                if desc in opt_text or opt_text in desc:
                    best_match = opt['val']
                    break
                    
            if not best_match:
                print(f"Could not find matching item for: {desc}")
            else:
                print(f"Adding item {desc} (ID: {best_match}) Qty: 1")
                page.select_option('#ctl00_ContentPlaceHolder1_itemlist', best_match)
                page.wait_for_timeout(2000)
                
                page.fill('#ctl00_ContentPlaceHolder1_txtqty', '1')
                page.click('#ctl00_ContentPlaceHolder1_btnadd')
                print("Clicked Add, waiting 3s...")
                page.wait_for_timeout(3000)
                
                # Check if item was added to the grid
                grid_html = page.evaluate('document.querySelector("#ctl00_ContentPlaceHolder1_GridView1") ? document.querySelector("#ctl00_ContentPlaceHolder1_GridView1").innerHTML : "No GridView"')
                print("GridView snippet:", grid_html[:200])
                page.screenshot(path='test_add_item.png', full_page=True)
                
                print("Clicking Save...")
                page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
                page.wait_for_timeout(4000)
                
                page.screenshot(path='test_add_item_after_save.png', full_page=True)
                
            browser.close()
            
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test_add_item()
