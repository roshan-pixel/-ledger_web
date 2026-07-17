import asyncio
from playwright.async_api import async_playwright
import time

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("Navigating to login page...")
        await page.goto("https://asclepiuswellness.com/Login.aspx")
        
        print("Logging in...")
        await page.fill("#ctl00_ContentPlaceHolder1_txtuserid", "62C04A")
        await page.fill("#ctl00_ContentPlaceHolder1_txtpassword", "Asclepius")
        await page.click("#ctl00_ContentPlaceHolder1_btnsubmituser")
        
        print("Waiting for login to complete...")
        await page.wait_for_load_state("networkidle")
        
        print("Navigating to Geneology page (Tree usually loads via JS)...")
        await page.goto("https://asclepiuswellness.com/userpanel/UserGroupTree.aspx")
        await page.wait_for_load_state("networkidle")
        
        # Wait a bit longer for any AJAX data to load the tree
        await page.wait_for_timeout(5000)
        
        # Take a screenshot to see what's actually rendered
        await page.screenshot(path="tree_rendered.png", full_page=True)
        
        # We need to figure out if there's a specific button to expand the tree or if it's an iframe/AJAX call
        html = await page.content()
        with open("tree_rendered.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
