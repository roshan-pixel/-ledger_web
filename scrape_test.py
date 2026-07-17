import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to login page...")
        # Most likely login page is at the root or /login
        await page.goto("https://asclepiuswellness.com/Login.aspx")
        print("Page title:", await page.title())
        
        # Take a screenshot to see what it looks like
        await page.screenshot(path="login_page.png")
        print("Screenshot saved to login_page.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
