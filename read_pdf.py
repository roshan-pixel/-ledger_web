import pypdf

reader = pypdf.PdfReader('C:\\Users\\sgarm\\Downloads\\nnnn.pdf')
text = ""
for page in reader.pages:
    text += page.extract_text() + "\n"

print("PDF TEXT:")
for i, line in enumerate(text.split('\n')):
    if line.strip():
        print(f"{i}: {line}")
