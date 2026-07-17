import re

with open("after_save_html.html", "r", encoding="utf-8") as f:
    html = f.read()

btn = re.search(r'<input[^>]*id="ctl00_ContentPlaceHolder1_ButtonSave1"[^>]*>', html)
if btn:
    print("Button HTML:", btn.group(0))

print("Is there any validation summary?")
val_sum = re.search(r'<div[^>]*id="ctl00_ContentPlaceHolder1_ValidationSummary1"[^>]*>(.*?)</div>', html, re.DOTALL)
if val_sum:
    print("Val Summary:", val_sum.group(1))
