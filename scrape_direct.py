import asyncio
from playwright.async_api import async_playwright

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
        
        # We know there are about 1474 nodes and we need to fetch them.
        # But UserGroupDownLine.aspx only showed 2 rows (AC29B06 and 97880D). 
        # Maybe we need to search or change a dropdown in the tree or downline page.
        print("Navigating to UserDownLineDirectNew.aspx...")
        await page.goto("https://asclepiuswellness.com/userpanel/UserDownLineDirectNew.aspx")
        await page.wait_for_load_state("networkidle")
        
        # Save HTML
        html = await page.content()
        with open("direct_page.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        await page.screenshot(path="direct_rendered.png", full_page=True)
        print("Saved direct_page.html and direct_rendered.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
