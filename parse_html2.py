import re

with open("after_save_html.html", "r", encoding="utf-8") as f:
    html = f.read()

# Look for visible text that might be an error
matches = re.findall(r'<span[^>]*style="color:Red;"[^>]*>(.*?)</span>', html, re.IGNORECASE)
print("Red spans:", matches)

matches2 = re.findall(r'alert\((.*?)\)', html, re.IGNORECASE)
print("Alerts:", matches2)
