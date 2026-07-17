import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        print("Navigating to login page...")
        await page.goto("https://asclepiuswellness.com/Login.aspx")
        
        print("Logging in...")
        await page.fill("#ctl00_ContentPlaceHolder1_txtuserid", "62C04A")
        await page.fill("#ctl00_ContentPlaceHolder1_txtpassword", "Asclepius")
        await page.click("#ctl00_ContentPlaceHolder1_btnsubmituser")
        
        await page.wait_for_load_state("networkidle")
        
        print("Navigating to Downline Printing (UserGroupDownLineA.aspx)...")
        await page.goto("https://asclepiuswellness.com/userpanel/UserGroupDownLineA.aspx")
        await page.wait_for_load_state("networkidle")
        
        # Change the start date to a very early date so we get all records
        print("Changing start date to get all history...")
        # Evaluate script to change the date value instead of typing to avoid datepicker popup interference
        await page.evaluate('document.getElementById("ctl00_ContentPlaceHolder1_dt1").value = "01/01/2015"')
        
        print("Clicking OK button to search...")
        await page.click("#ctl00_ContentPlaceHolder1_btnleft")
        
        print("Waiting for results to load...")
        await page.wait_for_load_state("networkidle")
        # Give it a few seconds to fully render the large table
        await page.wait_for_timeout(10000)
        
        html = await page.content()
        with open("full_downline.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # Parse table using pandas
        tables = pd.read_html(html)
        if tables:
            for i, t in enumerate(tables):
                if t.shape[0] > 10:
                    print(f"Found main table with {t.shape[0]} rows")
                    
                    # Ensure SGO and Green data exists, then filter
                    # If columns are not perfectly matching, we'll just save the raw table to excel and we can filter it later
                    # It's safer to save the full table
                    output_file = "C:\\Users\\sgarm\\Downloads\\SGO_DS_Data.xlsm"
                    
                    # Let's clean up the table if 'Org.' or similar column exists
                    try:
                        # Assuming 'Org.' or 'Group' column has SGO/SAO
                        # Assuming 'Color' or 'Status' column has Green/Red
                        # We will just dump to Excel first, then we can write a separate script to filter if needed
                        t.to_excel(output_file, index=False)
                        print(f"Saved full data to {output_file}")
                    except Exception as e:
                        print("Error saving to Excel:", e)
        else:
            print("No tables found in full_downline.html")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
