from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('https://www.asclepiuswellness.com/login.aspx?webid=1')
        
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtuserid"]', 'AAZFD8117G')
        page.fill('input[name="ctl00$ContentPlaceHolder1$txtpassword"]', 'ABC@1234')
        page.click('input[name="ctl00$ContentPlaceHolder1$btnlogin"]')
        
        page.wait_for_url('https://www.asclepiuswellness.com/shoppingpoint/Home.aspx', timeout=10000)
        
        links = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('a')).map(a => ({text: a.innerText.trim(), href: a.href})).filter(a => a.text.toLowerCase().includes('sale'));
        }''')
        print(links)
        browser.close()

if __name__ == '__main__':
    run()
