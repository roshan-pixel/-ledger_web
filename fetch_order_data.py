import json
import sys
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def fetch_order_data(username, password):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://asclepiuswellness.com/login.aspx?webid=1")
            page.wait_for_load_state("networkidle")
            
            page.evaluate('''() => {
                const el = document.getElementById('ctl00_ContentPlaceHolder1_txtspUserid');
                if(el) {
                    let curr = el;
                    while(curr && curr !== document.body) {
                        curr.style.display = 'block';
                        curr = curr.parentElement;
                    }
                }
            }''')
            
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtspUserid']", username, force=True)
            page.fill("input[name='ctl00$ContentPlaceHolder1$txtsppassword']", password, force=True)
            page.click("input[name='ctl00$ContentPlaceHolder1$btnfranlogin']", force=True)
            
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
                page.wait_for_timeout(2000)
            except Exception:
                pass
                
            # Fetch balance from Home
            if "Home.aspx" not in page.url:
                page.goto("https://asclepiuswellness.com/shoppingpoint/Home.aspx")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(2000)
                
            body_text = page.locator("body").inner_text()
            lines = [line.strip() for line in body_text.split('\n') if line.strip()]
            balance_str = "0"
            for i, line in enumerate(lines):
                if 'wallet balance' in line.lower():
                    if i+1 < len(lines):
                        balance_str = lines[i+1]
                        break
            
            match = re.search(r'[\d,\.]+', balance_str)
            if match:
                balance_val = float(match.group(0).replace(',', ''))
            else:
                balance_val = 0.0
                
            # Fetch products from FranchiseorderN
            page.goto("https://asclepiuswellness.com/shoppingpoint/FranchiseorderN.aspx")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            
            products = []
            select = soup.find('select', id='ctl00_ContentPlaceHolder1_itemlist')
            if select:
                for opt in select.find_all('option'):
                    val = opt.get('value', '')
                    text = opt.text.strip()
                    if not val or val == "0" or "select" in text.lower():
                        continue
                    # Format is often "ID-NAME", but we will just pass it as is
                    products.append({"id": val, "name": text})
                    
            # Try to grab rate info if embedded in a JS array or attribute.
            # Often, rates are fetched via AJAX when selecting a product. 
            # In our UI, if we don't have rates, we can let user input them, 
            # or try to extract from the inventory database if it matches.
            # Wait, the prompt says "rate display, amount calculation". 
            # I will let the script return products. We will query our local inventory 
            # to match the product and get the rate, OR allow user to type it if not found.
            
            browser.close()
            return {
                "success": True, 
                "balance": balance_val, 
                "raw_balance": balance_str,
                "products": products
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Missing username or password"}))
        sys.exit(1)
    res = fetch_order_data(sys.argv[1], sys.argv[2])
    print(json.dumps(res))
