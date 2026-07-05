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
            
            # Auto-accept all alerts and confirmations (crucial for Save button)
            def handle_dialog(dialog):
                print(f"[PORTAL ALERT] {dialog.message}")
                dialog.accept()
            page.on("dialog", handle_dialog)
            
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
            
            # 2. Select Order Type (SAO vs SGO) - always force-click via JS
            # because radio buttons exist in DOM but are hidden (is_visible returns False)
            if 'sao' in order_type:
                try:
                    result = page.evaluate("""
                        () => {
                            var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbsao');
                            if (rb) { rb.checked = true; rb.click(); return true; }
                            return false;
                        }
                    """)
                    print(f"[{ds_code}] Force-clicked SAO radio button: {result}")
                except Exception as e:
                    print(f"[{ds_code}] Could not force-click SAO: {e}")
            elif 'sgo' in order_type:
                try:
                    result = page.evaluate("""
                        () => {
                            var rb = document.querySelector('#ctl00_ContentPlaceHolder1_rbSgo');
                            if (rb) { rb.checked = true; rb.click(); return true; }
                            return false;
                        }
                    """)
                    print(f"[{ds_code}] Force-clicked SGO radio button: {result}")
                except Exception as e:
                    print(f"[{ds_code}] Could not force-click SGO: {e}")
            # For 'approve' (Red ID First Purchase) - no radio button needed
            
            # Check "Same As Profile Address" to auto-fill shipping details
            page.check('#ctl00_ContentPlaceHolder1_chkaddr')
            page.wait_for_timeout(1000)

            # Manually copy Mobile to ShipMobile because Red IDs sometimes fail to auto-fill it
            try:
                mobile_val = page.locator('#ctl00_ContentPlaceHolder1_txtmobile').input_value()
                if mobile_val:
                    page.fill('#ctl00_ContentPlaceHolder1_ShipMobile', mobile_val)
            except Exception:
                pass
            
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
                    
                # Extract product ID if it exists in brackets, e.g. "JC OIL [41] -" -> "41"
                import re
                match_id = re.search(r'\[(\d+)\]', desc)
                target_val = match_id.group(1) if match_id else None
                
                # Find matching option
                best_match = None
                for opt in options:
                    if target_val and opt['val'] == target_val:
                        best_match = opt['val']
                        break
                    
                    # Fallback to string matching
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
            
            print(f"[{ds_code}] Saving order...")
            page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
            page.wait_for_timeout(3000)
            
            # Debug screenshot
            page.screenshot(path=f'C:/Users/sgarm/Downloads/ledger_web/debug_{ds_code}.png', full_page=True)
            
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
