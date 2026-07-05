from playwright.sync_api import sync_playwright
import time
import json
import sqlite3

def submit_order_to_portal(ds_code, items, order_type='sao'):
    """
    Submits an order to the C&F portal.
    items is a list of dicts: [{'description': 'ITEM NAME', 'qty': 2}, ...]
    order_type can be 'sao', 'sgo', or 'approve'
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
            ctx = browser.new_context()
            page = ctx.new_page()
            
            # Auto-accept any confirmation dialogs (like "Are Sure To Add this Product ." or "Are you sure to save?")
            page.on("dialog", lambda dialog: dialog.accept())
            
            # 1. Login
            page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
            page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
            page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
            page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
            page.wait_for_load_state('networkidle')
            
            # 2. Go to Sales Order page
            page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
            
            # Enter DS ID and press Tab to trigger details loading
            page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
            page.keyboard.press('Tab')
            
            # Wait for name and items to load via AJAX
            page.wait_for_timeout(4000)
            
            # Handle Sale Group (SAO / SGO) based on order_type
            if order_type == 'sao':
                try:
                    if page.is_visible('#ctl00_ContentPlaceHolder1_rbsao', timeout=3000):
                        page.click('#ctl00_ContentPlaceHolder1_rbsao')
                        page.wait_for_timeout(1000)
                except Exception:
                    pass
            elif order_type == 'sgo':
                try:
                    if page.is_visible('#ctl00_ContentPlaceHolder1_rbsgo', timeout=3000):
                        page.click('#ctl00_ContentPlaceHolder1_rbsgo')
                        page.wait_for_timeout(1000)
                except Exception:
                    pass
            # If order_type == 'approve', we do not click any SAO/SGO radio button

            
            # Check "Same As Profile Address" to auto-fill shipping details
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
            if not name:
                print(f"[{ds_code}] DS Code not found on portal.")
                browser.close()
                return False
                
            # 2. Get available items from dropdown
            options = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('#ctl00_ContentPlaceHolder1_itemlist option')).map(o => ({val: o.value, text: o.text}));
            }''')
            
            # Remove the first "Select" option if it exists
            if options and "select" in options[0]['text'].lower():
                options = options[1:]
                
            # 3. Add each item
            for item in items:
                desc = item.get('description', '').strip().upper()
                qty = float(item.get('qty', 0))
                
                if not desc or qty <= 0:
                    continue
                    
                # Find matching option
                best_match = None
                for opt in options:
                    opt_text = opt['text'].strip().upper()
                    if desc in opt_text or opt_text in desc:
                        best_match = opt['val']
                        break
                        
                if not best_match:
                    print(f"[{ds_code}] Could not find matching item for: {desc}")
                    continue
                    
                print(f"[{ds_code}] Adding item {desc} (ID: {best_match}) Qty: {qty}")
                
                # Select the item
                page.select_option('#ctl00_ContentPlaceHolder1_itemlist', best_match)
                page.wait_for_timeout(2000) # Wait for price etc to load
                
                # Fill qty
                page.fill('#ctl00_ContentPlaceHolder1_txtqty', str(int(qty)))
                
                # Click Add
                page.click('#ctl00_ContentPlaceHolder1_btnadd')
                page.wait_for_timeout(2500) # Wait for row to be added to grid
            
            # 4. Click Save
            print(f"[{ds_code}] Saving order...")
            page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
            page.wait_for_timeout(3000)
            
            print(f"[{ds_code}] Order submitted successfully to portal!")
            browser.close()
            return True
            
    except Exception as e:
        print(f"[{ds_code}] Error submitting order to portal: {e}")
        return False

def submit_order_async(ds_code, items, order_type='sao'):
    import threading
    t = threading.Thread(target=submit_order_to_portal, args=(ds_code, items, order_type))
    t.daemon = True
    t.start()
