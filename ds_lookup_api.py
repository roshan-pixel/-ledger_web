import os
import tempfile
from playwright.sync_api import sync_playwright

SESSION_STATE_FILE = os.path.join(tempfile.gettempdir(), 'awpl_portal_session.json')

def fetch_ds_from_portal(ds_code):
    """
    High-performance live DS code lookup in the AWPL C&F portal:
    1. Reuses authenticated session cookies across requests (~3-5s).
    2. Blocks all heavy media/images/fonts (saves ~5MB transfer per lookup).
    3. Uses targeted DOM state waiting instead of fixed timers or networkidle.
    4. Falls back to fast re-authentication if session expired (~7-8s).
    """
    username = os.environ.get('PORTAL_USER', 'AAZFD8117G')
    password = os.environ.get('PORTAL_PASSWORD', 'ABC@1234')
    
    launch_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--disable-extensions'
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=launch_args)
        
        # Restore session state if available
        if os.path.exists(SESSION_STATE_FILE):
            try:
                ctx = browser.new_context(storage_state=SESSION_STATE_FILE)
            except Exception:
                ctx = browser.new_context()
        else:
            ctx = browser.new_context()
            
        page = ctx.new_page()
        
        # Block images, fonts, media to maximize speed
        page.route('**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,mp4,mp3,ico}', lambda r: r.abort())
        
        try:
            # 1. Try going directly to Sale Order page using cached session
            page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='domcontentloaded', timeout=15000)
            
            # Check if redirected to login or session invalid
            if 'login.aspx' in page.url or page.locator('#ctl00_ContentPlaceHolder1_txtid').count() == 0:
                if 'login.aspx' not in page.url:
                    page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='domcontentloaded', timeout=15000)
                page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', username)
                page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', password)
                with page.expect_navigation(wait_until='domcontentloaded', timeout=15000):
                    page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
                try:
                    ctx.storage_state(path=SESSION_STATE_FILE)
                except Exception:
                    pass
                page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='domcontentloaded', timeout=15000)
                
            # 2. Type DS code and trigger AJAX lookup
            txt_id = page.locator('#ctl00_ContentPlaceHolder1_txtid')
            txt_id.fill(ds_code)
            page.keyboard.press('Tab')
            
            # 3. Wait for name field to be populated (or timeout if invalid code)
            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#ctl00_ContentPlaceHolder1_txtname'); return el && el.value.trim().length > 0; }",
                    timeout=5000
                )
            except Exception:
                pass
                
            name = page.input_value('#ctl00_ContentPlaceHolder1_txtname').strip()
            if not name:
                return None
                
            mobile = page.input_value('#ctl00_ContentPlaceHolder1_txtmobile').strip()
            address = page.input_value('#ctl00_ContentPlaceHolder1_txtaddress').strip()
            shipping_address = page.input_value('#ctl00_ContentPlaceHolder1_txtshipaddress').strip()
            ship_mobile = page.input_value('#ctl00_ContentPlaceHolder1_ShipMobile').strip()
            ship_pincode = page.input_value('#ctl00_ContentPlaceHolder1_txtshpingpincode').strip()
            
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
