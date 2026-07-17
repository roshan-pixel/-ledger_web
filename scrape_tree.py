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
        
        # Taking screenshot to see if btnsubmituser exists or is hidden
        await page.screenshot(path="login_form_filled.png")
        
        # Try ID selector instead of name selector
        await page.click("#ctl00_ContentPlaceHolder1_btnsubmituser")
        
        print("Waiting for login to complete...")
        await page.wait_for_load_state("networkidle")
        
        print("Navigating to UserGroupTree.aspx...")
        await page.goto("https://asclepiuswellness.com/userpanel/UserGroupTree.aspx")
        await page.wait_for_load_state("networkidle")
        
        # Save HTML
        html = await page.content()
        with open("tree_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved tree_page.html")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
