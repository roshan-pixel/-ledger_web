import json
import sys
from playwright.sync_api import sync_playwright

def get_wallet_balance(username, password):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto("https://asclepiuswellness.com/login.aspx?webid=1")
            page.wait_for_load_state("networkidle")
            
            # Show fields if hidden
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
            
            # Clean balance_str e.g. '₹285195.92/-' -> 285195.92
            import re
            match = re.search(r'[\d,\.]+', balance_str)
            if match:
                balance_val = float(match.group(0).replace(',', ''))
            else:
                balance_val = 0.0
                
            browser.close()
            res = {"success": True, "balance": balance_val, "raw": balance_str}
            try:
                save_wallet_to_db(balance_val)
            except Exception as e:
                pass
            return res
    except Exception as e:
        return {"success": False, "error": str(e)}

def save_wallet_to_db(balance: float):
    import sqlite3, os
    db_path = os.path.join(os.path.dirname(__file__), 'ledger.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS kpis (key TEXT PRIMARY KEY, value TEXT)")
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('wallet_balance', ?)", (str(balance),))
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('ledger_closing_balance', ?)", (str(balance),))
    c.execute("INSERT OR REPLACE INTO kpis (key, value) VALUES ('Wallet Balance', ?)", (str(round(balance, 2)),))
    conn.commit()
    conn.close()

    # Also update closing_balance in ledger_report.json if exists
    json_path = os.path.join(os.path.dirname(__file__), 'ledger_report.json')
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data['closing_balance'] = balance
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"success": False, "error": "Missing username or password"}))
        sys.exit(1)
    res = get_wallet_balance(sys.argv[1], sys.argv[2])
    print(json.dumps(res))
