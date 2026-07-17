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
        
        # Select SGO or filter downline
        # First, let's just see what filters are available
        html = await page.content()
        with open("printing_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # See if there's a button to load all or select SGO
        
        await page.screenshot(path="printing_rendered.png", full_page=True)
        print("Saved printing_page.html and printing_rendered.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
