import os

target_dir = r"C:\Users\sgarm\Downloads\ledger_web\templates"
html_files = [f for f in os.listdir(target_dir) if f.endswith('.html')]

new_nav_item = """
        <li class="nav-item" onclick="navigateTo('/stock_point_order')">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
            Stock Point Order
        </li>"""

# Handle templates using navigateTo and window.location.href
for filename in html_files:
    if filename == "stock_point_order.html":
        continue
    filepath = os.path.join(target_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "Stock Point Order" in content:
        print(f"Skipping {filename}, already has it.")
        continue

    # Look for the last nav-item or a specific one to insert after
    # We will insert it right before </ul>
    
    if "</ul>" in content:
        # Some use </ul> for nav
        parts = content.split("</ul>")
        if len(parts) >= 2:
            # Insert before the first </ul> that belongs to nav
            idx = content.find("</ul>")
            # But wait, there could be other uls.
            # Let's search for "Mizoram Bronze" or "Disease Guide"
            anchor = "Mizoram Bronze\n            </li>"
            if anchor in content:
                content = content.replace(anchor, anchor + new_nav_item)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filename}")
                continue

            anchor2 = "Disease Guide\n        </li>"
            if anchor2 in content:
                # adjust spaces based on file
                if "navigateTo" not in new_nav_item:
                    pass
                content = content.replace(anchor2, anchor2 + new_nav_item.replace('navigateTo', 'window.location.href=').replace("('/stock", "('/stock").replace("')", "')"))
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filename}")
                continue
            
            anchor3 = "Disease Guide\n            </li>"
            if anchor3 in content:
                content = content.replace(anchor3, anchor3 + new_nav_item)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filename}")
                continue
                
            print(f"Could not find anchor in {filename}")

