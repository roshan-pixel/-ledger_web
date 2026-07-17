from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        
        page.on("dialog", lambda dialog: dialog.accept())
        
        def handle_response(response):
            if "SpdistributorSale.aspx" in response.url and response.request.method == "POST":
                print(f"[{response.status}] POST {response.url}")
                try:
                    text = response.text()
                    with open("post_response.txt", "w", encoding="utf-8") as f:
                        f.write(text)
                    print("Wrote post_response.txt")
                except Exception as e:
                    print("Could not read response:", e)
                
        page.on("response", handle_response)
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')

        page.goto('https://asclepiuswellness.com/shoppingpoint/SpdistributorSale.aspx', wait_until='networkidle')
        
        page.fill('#ctl00_ContentPlaceHolder1_txtid', '9176AF94')
        page.keyboard.press('Tab')
        page.wait_for_timeout(4000)
        
        page.check('#ctl00_ContentPlaceHolder1_chkaddr')
        page.wait_for_timeout(1000)
        
        page.select_option('#ctl00_ContentPlaceHolder1_itemlist', '52')
        page.wait_for_timeout(1000)
        page.fill('#ctl00_ContentPlaceHolder1_txtqty', '1')
        page.click('#ctl00_ContentPlaceHolder1_btnadd')
        page.wait_for_timeout(3000)
        
        print("Clicking Save!")
        page.click('#ctl00_ContentPlaceHolder1_ButtonSave1')
        
        # Wait to capture response
        page.wait_for_timeout(10000)
        
        browser.close()

if __name__ == '__main__':
    test()
