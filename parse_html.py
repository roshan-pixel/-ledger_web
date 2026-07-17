import re

with open("after_save_html.html", "r", encoding="utf-8") as f:
    html = f.read()

msg = re.search(r'id="ctl00_ContentPlaceHolder1_lblMsg"[^>]*>(.*?)</span>', html)
if msg:
    print("lblMsg:", msg.group(1))

if "Bill Save Successfully" in html:
    print("Bill Save Successfully is in HTML!")

if "9176AF94" in html:
    print("ID is still in HTML")
