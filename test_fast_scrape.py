import asyncio
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# To keep track of visited nodes to avoid infinite loops
visited = set()
data = []

def parse_page(html, current_node_id):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Extract root node info
    root_a = soup.find('a', id='ctl00_ContentPlaceHolder1_lbkparentid')
    root_name_span = soup.find('span', id='ctl00_ContentPlaceHolder1_lblparentname')
    root_img = soup.find('img', id='ctl00_ContentPlaceHolder1_imgmains')
    
    if not root_a:
        return None
        
    ds_id = root_a.text.strip()
    name = root_name_span.text.strip() if root_name_span else ""
    img_src = root_img['src'] if root_img else ""
    
    status = "Red"
    if "GMA" in img_src or "GFA" in img_src or "Green" in img_src:
        status = "Green"
    elif "YMA" in img_src or "YFA" in img_src:
        status = "Yellow"
        
    data.append({
        "DS ID": ds_id,
        "Name": name,
        "Status": status,
        "Parent ID": current_node_id,
        "Image": img_src
    })
    
    # 2. Extract ViewState
    viewstate = soup.find('input', id='__VIEWSTATE')['value'] if soup.find('input', id='__VIEWSTATE') else ''
    viewstategen = soup.find('input', id='__VIEWSTATEGENERATOR')['value'] if soup.find('input', id='__VIEWSTATEGENERATOR') else ''
    eventvalidation = soup.find('input', id='__EVENTVALIDATION')['value'] if soup.find('input', id='__EVENTVALIDATION') else ''
    
    # 3. Find left and right children
    children = []
    
    left_a = soup.find('a', id='ctl00_ContentPlaceHolder1_rptleft_ctl00_Link1')
    if left_a and len(left_a.text.strip()) == 6:
        # Check if it has a postback link
        href = left_a.get('href', '')
        if 'doPostBack' in href:
            target = href.split("'")[1]
            children.append(('Left', left_a.text.strip(), target))
            
    right_a = soup.find('a', id='ctl00_ContentPlaceHolder1_rptright_ctl00_Link1')
    if right_a and len(right_a.text.strip()) == 6:
        href = right_a.get('href', '')
        if 'doPostBack' in href:
            target = href.split("'")[1]
            children.append(('Right', right_a.text.strip(), target))
            
    return {
        'ds_id': ds_id,
        'viewstate': viewstate,
        'viewstategen': viewstategen,
        'eventvalidation': eventvalidation,
        'children': children
    }

async def get_initial_session(ds_code, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://asclepiuswellness.com/Login.aspx")
        await page.fill("#ctl00_ContentPlaceHolder1_txtuserid", ds_code)
        await page.fill("#ctl00_ContentPlaceHolder1_txtpassword", password)
        await page.click("#ctl00_ContentPlaceHolder1_btnsubmituser")
        await page.wait_for_load_state("networkidle")
        
        await page.goto("https://asclepiuswellness.com/userpanel/UserGroupTree.aspx")
        await page.wait_for_load_state("networkidle")
        
        html = await page.content()
        
        # Get cookies
        cookies = await context.cookies()
        session_cookies = {c['name']: c['value'] for c in cookies}
        
        await browser.close()
        return html, session_cookies

def scrape_recursive(initial_html, cookies, start_target='ctl00$ContentPlaceHolder1$rptright$ctl00$Link1'):
    session = requests.Session()
    session.cookies.update(cookies)
    
    url = "https://asclepiuswellness.com/userpanel/UserGroupTree.aspx"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # 1. Parse initial page to get ViewState
    parsed = parse_page(initial_html, "ROOT")
    if not parsed:
        print("Failed to parse initial page")
        return
        
    print(f"Root node: {parsed['ds_id']}")
    
    # 2. Find SGO (right) branch target
    sgo_target = start_target # We assume SGO is right side
    
    # 3. BFS Queue: stores (parent_id, target_to_postback, current_viewstate_data)
    # Actually, ViewState is specific to the current page state. 
    # Wait, ASP.NET TreeView requires navigating one node at a time.
    # If we do PostBack, it returns a new page with a new ViewState.
    # So we can't easily do parallel BFS because each POST depends on the previous page's ViewState!
    print("WARNING: ViewState requires sequential navigation if we rely on it.")
    pass

if __name__ == "__main__":
    pass
