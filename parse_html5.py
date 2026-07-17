import re

with open("after_save_html.html", "r", encoding="utf-8") as f:
    html = f.read()

# Find all textareas
textareas = re.findall(r'<textarea[^>]*id="(.*?)"[^>]*>', html)
print("Textareas:", textareas)

# Find all inputs
inputs = re.findall(r'<input[^>]*id="(.*?)"[^>]*>', html)
print("Inputs:", [i for i in inputs if 'ctl00_ContentPlaceHolder1' in i])
