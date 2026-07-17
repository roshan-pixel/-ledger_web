import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
import os

# Crawler configuration
START_NODE = "62C04A"
OUTPUT_FILE = r"C:\Users\sgarm\Downloads\Full_Tree_Data.xlsm"
BACKUP_FILE = r"C:\Users\sgarm\Downloads\Full_Tree_Data_backup.csv"
NUM_WORKERS = 6  # 6 parallel browsers to speed up extraction

results = []
visited = set()
processing = set()  # To avoid adding the same node to queue multiple times if discovered twice
queue = asyncio.Queue()

# Thread-safe writing
lock = asyncio.Lock()

async def worker(worker_id, context, ds_code, password):
    page = await context.new_page()
    
    # Login individually for this page just in case session isn't perfectly shared
    # Actually, if we use the same context, cookies are shared! We just need one login.
    # We'll just go to the tree page.
    print(f"Worker {worker_id}: Navigating to Genealogy Tree...")
    await page.goto("https://asclepiuswellness.com/userpanel/UserGroupTree.aspx", timeout=60000)
    await page.wait_for_load_state("networkidle")
    
    while True:
        try:
            current_node = await queue.get()
        except asyncio.CancelledError:
            break
            
        async with lock:
            if current_node in visited:
                queue.task_done()
                continue
            visited.add(current_node)
            print(f"[Worker {worker_id} | Total: {len(visited)}] Extracting: {current_node} | Queue: {queue.qsize()}")
        
        try:
            search_input = page.locator("#ctl00_ContentPlaceHolder1_txtsearch")
            if await search_input.count() > 0:
                await search_input.fill(current_node)
                await page.click("#ctl00_ContentPlaceHolder1_btnsearch")
                await page.wait_for_load_state("networkidle")
                await page.wait_for_timeout(500) # Small delay for rendering
            else:
                # If page session timed out, we might need to re-login. Let's just break and it'll fail this node
                print(f"Worker {worker_id}: Session might have dropped.")
                pass

            html = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            root_a = soup.find('a', id='ctl00_ContentPlaceHolder1_lbkparentid')
            if not root_a or root_a.text.strip() != current_node:
                queue.task_done()
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
                
            async with lock:
                results.append({
                    "DS Code": current_node,
                    "Name": name,
                    "Status": status
                })
            
            # Find children
            left_a = soup.find('a', id='ctl00_ContentPlaceHolder1_rptleft_ctl00_Link0')
            if left_a and len(left_a.text.strip()) == 6 and left_a.text.strip().isalnum():
                child = left_a.text.strip()
                async with lock:
                    if child not in processing:
                        processing.add(child)
                        queue.put_nowait(child)
                
            right_a = soup.find('a', id='ctl00_ContentPlaceHolder1_rptright_ctl00_Link1')
            if right_a and len(right_a.text.strip()) == 6 and right_a.text.strip().isalnum():
                child = right_a.text.strip()
                async with lock:
                    if child not in processing:
                        processing.add(child)
                        queue.put_nowait(child)
                        
            # Incremental backup
            async with lock:
                if len(visited) % 50 == 0:
                    df = pd.DataFrame(results)
                    df.to_csv(BACKUP_FILE, index=False)
                    
        except Exception as e:
            print(f"Worker {worker_id}: Error extracting {current_node}: {e}")
            # Put back in queue to retry
            async with lock:
                visited.discard(current_node)
                queue.put_nowait(current_node)
            await page.wait_for_timeout(3000)
            
        queue.task_done()

async def crawl_tree(ds_code, password):
    print("Initializing PARALLEL careful crawler procedure...")
    
    global visited, results
    if os.path.exists(BACKUP_FILE):
        print("Found previous backup. It will be overwritten as we fast-forward.")
    
    processing.add(START_NODE)
    queue.put_nowait(START_NODE)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # We need a context to share cookies among pages
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        
        # 1. Login using one page to establish the session cookie
        login_page = await context.new_page()
        print("Logging into Asclepius to establish session...")
        await login_page.goto("https://asclepiuswellness.com/Login.aspx", timeout=60000)
        await login_page.fill("#ctl00_ContentPlaceHolder1_txtuserid", ds_code)
        await login_page.fill("#ctl00_ContentPlaceHolder1_txtpassword", password)
        await login_page.click("#ctl00_ContentPlaceHolder1_btnsubmituser")
        await login_page.wait_for_load_state("networkidle")
        await login_page.close()
        print("Login complete. Starting workers...")
        
        # 2. Start workers
        tasks = []
        for i in range(NUM_WORKERS):
            task = asyncio.create_task(worker(i+1, context, ds_code, password))
            tasks.append(task)
            
        # 3. Wait for queue to empty
        await queue.join()
        
        # Cancel workers
        for task in tasks:
            task.cancel()
            
        print("Extraction complete. Saving final XLSM file...")
        
        if len(results) > 0:
            final_df = pd.DataFrame(results)
            green_count = len(final_df[final_df['Status'] == 'Green'])
            print(f"Total Extracted: {len(final_df)} | Total Green: {green_count}")
            
            with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
                final_df.to_excel(writer, index=False, sheet_name='Full Tree Data')
            print(f"Successfully saved to {OUTPUT_FILE}")
        else:
            print("No data was extracted.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(crawl_tree("62C04A", "Asclepius"))
