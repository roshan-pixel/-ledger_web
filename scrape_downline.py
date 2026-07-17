import asyncio
from playwright.async_api import async_playwright

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
        
        await page.wait_for_load_state("networkidle")
        
        print("Navigating to UserGroupDownLine.aspx (Depth Downline)...")
        await page.goto("https://asclepiuswellness.com/userpanel/UserGroupDownLine.aspx")
        await page.wait_for_load_state("networkidle")
        
        # Save HTML
        html = await page.content()
        with open("downline_page.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        await page.screenshot(path="downline_rendered.png", full_page=True)
        print("Saved downline_page.html and downline_rendered.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
