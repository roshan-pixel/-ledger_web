import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
import os

# Crawler configuration
START_NODE = "AC29B06"  # SGO Root
OUTPUT_FILE = r"C:\Users\sgarm\Downloads\SGO_DS_Data.xlsm"
BACKUP_FILE = r"C:\Users\sgarm\Downloads\SGO_DS_Data_backup.csv"

queue = [START_NODE]
visited = set()
results = []

async def crawl_tree(ds_code, password):
    print("Initializing careful crawler procedure...")
    
    global queue, visited, results
    if os.path.exists(BACKUP_FILE):
        print("Found previous backup. Resuming...")
        try:
            df = pd.read_csv(BACKUP_FILE)
            results = df.to_dict('records')
            visited = set(df['DS Code'].tolist())
            print(f"Loaded {len(results)} previously scraped nodes.")
        except Exception as e:
            print("Could not load backup:", e)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        
        print("1. Logging into Asclepius...")
        await page.goto("https://asclepiuswellness.com/Login.aspx", timeout=60000)
        await page.fill("#ctl00_ContentPlaceHolder1_txtuserid", ds_code)
        await page.fill("#ctl00_ContentPlaceHolder1_txtpassword", password)
        await page.click("#ctl00_ContentPlaceHolder1_btnsubmituser")
        await page.wait_for_load_state("networkidle")
        
        print("2. Navigating to Genealogy Tree...")
        await page.goto("https://asclepiuswellness.com/userpanel/UserGroupTree.aspx", timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        print(f"3. Beginning BFS Extraction from SGO node: {START_NODE}")
        
        while queue:
            current_node = queue.pop(0)
            
            if current_node in visited:
                continue
                
            visited.add(current_node)
            print(f"[{len(visited)}/1474] Extracting Node: {current_node} | Queue size: {len(queue)}")
            
            try:
                # Use the correct Search box
                search_input = page.locator("#ctl00_ContentPlaceHolder1_txtsearch")
                if await search_input.count() > 0:
                    await search_input.fill(current_node)
                    await page.click("#ctl00_ContentPlaceHolder1_btnsearch")
                    await page.wait_for_load_state("networkidle")
                    await page.wait_for_timeout(1000)
                else:
                    print("Could not find search box on page!")
                    break

                html = await page.content()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                
                root_a = soup.find('a', id='ctl00_ContentPlaceHolder1_lbkparentid')
                if not root_a or root_a.text.strip() != current_node:
                    print(f"  -> Skipping {current_node}, not found on page. It returned: {root_a.text.strip() if root_a else 'None'}")
                    continue
                    
                root_name = soup.find('span', id='ctl00_ContentPlaceHolder1_lblparentname')
                root_img = soup.find('img', id='ctl00_ContentPlaceHolder1_imgmains')
                
                name = root_name.text.strip() if root_name else "Unknown"
                img_src = root_img['src'] if root_img else ""
                
                status = "Red"
                if "GMA" in img_src or "GFA" in img_src or "Green" in img_src:
                    status = "Green"
                elif "YMA" in img_src or "YFA" in img_src:
                    status = "Yellow"
                    
                results.append({
                    "DS Code": current_node,
                    "Name": name,
                    "Status": status
                })
                
                # Check for left and right children
                left_a = soup.find('a', id='ctl00_ContentPlaceHolder1_rptleft_ctl00_Link1')
                if left_a and len(left_a.text.strip()) == 6 and left_a.text.strip().isalnum():
                    queue.append(left_a.text.strip())
                    
                right_a = soup.find('a', id='ctl00_ContentPlaceHolder1_rptright_ctl00_Link1')
                if right_a and len(right_a.text.strip()) == 6 and right_a.text.strip().isalnum():
                    queue.append(right_a.text.strip())
                    
                if len(visited) % 10 == 0:
                    df = pd.DataFrame(results)
                    df.to_csv(BACKUP_FILE, index=False)
                    
            except Exception as e:
                print(f"Error extracting {current_node}: {e}")
                queue.insert(0, current_node)
                await page.wait_for_timeout(3000)
                
        print("Extraction complete. Saving final XLSM file...")
        
        if len(results) > 0:
            final_df = pd.DataFrame(results)
            green_count = len(final_df[final_df['Status'] == 'Green'])
            print(f"Total Extracted: {len(final_df)} | Total Green: {green_count}")
            
            with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False, sheet_name='SGO Data')
            print(f"Successfully saved to {OUTPUT_FILE}")
        else:
            print("No data was extracted.")
            
        await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(crawl_tree("62C04A", "Asclepius"))
    except KeyboardInterrupt:
        print("\nProcess interrupted. Progress saved in CSV backup.")
