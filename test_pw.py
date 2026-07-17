import asyncio
from playwright.sync_api import sync_playwright
import time
import gspread

def test_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('http://127.0.0.1:5000/invoice')
        print('Page loaded')
        
        # 1. Fill DS Code
        page.fill('#dsCodeInput', '62c04a')
        # Click search icon
        page.click('#lookupBtn')
        time.sleep(2)
        print('DS code lookup done')
        
        # 2. Add Kidgdoc
        page.fill('#itemSearch', 'kidgdoc')
        time.sleep(1)
        # Click on the first dropdown item
        page.click('.dropdown-item')
        time.sleep(1)
        print('Added KIDGDOC')
        
        # Print the total SP
        total_sp = page.locator('#grandTotalSP').inner_text()
        print('Grand Total SP on UI:', total_sp)
        
        # 3. Save Invoice
        page.click('button:has-text("Save Invoice")')
        time.sleep(3)
        print('Saved invoice!')
        browser.close()
        
    print('Checking Google Sheets...')
    gc = gspread.service_account(filename='credentials.json')
    sheet = gc.open('Ledger_Database')
    invoices = sheet.worksheet('Invoices').get_all_values()
    print('Latest invoice in Google Sheets:', invoices[-1])

if __name__ == '__main__':
    test_ui()
