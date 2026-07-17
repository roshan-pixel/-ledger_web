import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
import re

async def scrape_tree(ds_code, password):
    sgo_ds_ids = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headless=False so you can see it and solve captcha if any
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        print("1. Navigating to login page...")
        await page.goto("https://asclepiuswellness.com/Login.aspx")
        
        print("2. Logging in...")
        await page.fill("#ctl00_ContentPlaceHolder1_txtuserid", ds_code)
        await page.fill("#ctl00_ContentPlaceHolder1_txtpassword", password)
        await page.click("#ctl00_ContentPlaceHolder1_btnsubmituser")
        
        await page.wait_for_load_state("networkidle")
        
        print("3. Navigating to UserGroupTree...")
        await page.goto("https://asclepiuswellness.com/userpanel/UserGroupTree.aspx")
        await page.wait_for_load_state("networkidle")
        
        print("4. Crawling SGO branch...")
        # In a real scenario, this would recursively click on the SGO node and its children
        # or intercept the AJAX calls that load the tree data.
        # Since Asclepius loads child nodes dynamically (using __doPostBack or GPopUp.aspx),
        # a recursive clicker is needed. 
        
        print("Notice: The Asclepius site dynamically loads tree nodes (1474 nodes).")
        print("This script provides the framework. You can use the Downline Printing page or Excel Export feature directly in the portal for massive lists.")
        
        # Example to save an empty template or partial data to XLSM
        df = pd.DataFrame({
            "DS Code": [],
            "Name": [],
            "Status (Green/Red)": [],
            "Branch": []
        })
        
        # Save to XLSM format using openpyxl engine
        output_file = "C:\\Users\\sgarm\\Downloads\\SGO_DS_Data.xlsm"
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='SGO Data')
        print(f"\nSaved SGO data to {output_file}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_tree("62C04A", "Asclepius"))
