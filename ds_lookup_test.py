from playwright.sync_api import sync_playwright

def lookup_ds_live(ds_code):
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
            
            # Wait a moment for AJAX or PostBack
            page.wait_for_timeout(3000)
            
            # Get fields
            name = page.input_value('#ctl00_ContentPlaceHolder1_txtname')
            mobile = page.input_value('#ctl00_ContentPlaceHolder1_txtmobile')
            # The address is in a textarea maybe? Let's get all textareas
            textareas = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('textarea')).map(t => ({id: t.id, value: t.value}));
            }''')
            
            # Ship Mobile and Pincode
            ship_mobile = page.input_value('#ctl00_ContentPlaceHolder1_ShipMobile')
            ship_pincode = page.input_value('#ctl00_ContentPlaceHolder1_txtshpingpincode')
            
            print("Name:", name)
            print("Mobile:", mobile)
            print("Ship Mobile:", ship_mobile)
            print("Ship Pincode:", ship_pincode)
            print("Textareas:", textareas)
            
            return name
        except Exception as e:
            print("Error:", e)
        finally:
            browser.close()

if __name__ == '__main__':
    lookup_ds_live('62C04A')
