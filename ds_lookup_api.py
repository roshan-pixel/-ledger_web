from playwright.sync_api import sync_playwright

def fetch_ds_from_portal(ds_code):
    """
    Look up DS code in the C&F portal.
    Returns a dictionary with ds_name, mobile, address, shipping_mobile, shipping_pincode, shipping_address
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        
        try:
            # Login
            page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
            page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
            page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
            page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
            page.wait_for_load_state('networkidle')
            
            # Navigate to Sale Order
            page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
            
            # Type DS code and trigger change/blur
            page.fill('#ctl00_ContentPlaceHolder1_txtid', ds_code)
            page.keyboard.press('Tab')
            
            # Wait a moment for AJAX or PostBack to populate fields
            page.wait_for_timeout(3000)
            
            # Get fields
            name = page.input_value('#ctl00_ContentPlaceHolder1_txtname')
            if not name:
                return None
                
            mobile = page.input_value('#ctl00_ContentPlaceHolder1_txtmobile')
            
            # Extract TextAreas for Address and Shipping Address
            address = page.input_value('#ctl00_ContentPlaceHolder1_txtaddress')
            shipping_address = page.input_value('#ctl00_ContentPlaceHolder1_txtshipaddress')
            
            ship_mobile = page.input_value('#ctl00_ContentPlaceHolder1_ShipMobile')
            ship_pincode = page.input_value('#ctl00_ContentPlaceHolder1_txtshpingpincode')
            
            return {
                'ds_code': ds_code,
                'ds_name': name,
                'mobile': mobile,
                'address': address,
                'shipping_address': shipping_address,
                'shipping_mobile': ship_mobile,
                'shipping_pincode': ship_pincode,
                'last_invoice': ''
            }
        except Exception as e:
            print("Error in fetch_ds_from_portal:", e)
            return None
        finally:
            browser.close()
