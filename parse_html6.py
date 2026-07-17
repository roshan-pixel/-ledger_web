import re

with open("after_save_html.html", "r", encoding="utf-8") as f:
    html = f.read()

shipping = re.search(r'<textarea[^>]*id="ctl00_ContentPlaceHolder1_txtshipaddress"[^>]*>(.*?)</textarea>', html, re.DOTALL)
if shipping:
    print("Shipping Address:", repr(shipping.group(1)))

mobile = re.search(r'<input[^>]*id="ctl00_ContentPlaceHolder1_ShipMobile"[^>]*value="(.*?)"', html)
if mobile:
    print("Shipping Mobile:", repr(mobile.group(1)))
