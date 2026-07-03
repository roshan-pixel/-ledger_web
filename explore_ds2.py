from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        
        page.goto('https://asclepiuswellness.com/login.aspx?webid=1', wait_until='networkidle')
        page.fill('#ctl00_ContentPlaceHolder1_txtspUserid', 'AAZFD8117G')
        page.fill('#ctl00_ContentPlaceHolder1_txtsppassword', 'ABC@1234')
        page.click('#ctl00_ContentPlaceHolder1_btnfranlogin')
        page.wait_for_load_state('networkidle')
        
        links = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({text: a.innerText.trim(), href: a.href})).filter(a => a.text.length > 0);
        }''')
        print(links)
        browser.close()

if __name__ == '__main__':
    run()
