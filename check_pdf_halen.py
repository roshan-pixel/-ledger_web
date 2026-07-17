import PyPDF2
pdf_file = open('C:\\Users\\sgarm\\Downloads\\nnnn.pdf', 'rb')
reader = PyPDF2.PdfReader(pdf_file)
found = False
for page_num in range(len(reader.pages)):
    text = reader.pages[page_num].extract_text()
    if 'HALEN' in text.upper():
        print(f"Found on page {page_num+1}:")
        for line in text.split('\n'):
            if 'HALEN' in line.upper() or 'LIPSTICK' in line.upper():
                print("  ", line)
        found = True
if not found:
    print("HALEN not found in PDF.")
pdf_file.close()
