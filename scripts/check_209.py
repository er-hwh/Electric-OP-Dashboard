import pymupdf as fitz

pdf_path = r"C:\Users\Indian Railway\.gemini\antigravity\brain\9513809e-d90d-4964-98bd-d36e4e05f542\.user_uploaded\media_1791962055864_26843c4a.pdf"
doc = fitz.open(pdf_path)

# Let's search for 2.09 in the PDF
for p in range(len(doc)):
    text = doc[p].get_text()
    if "2.09" in text and "alcoholic" in text.lower():
        print(f"Found official 2.09 on Page {p+1}:")
        print(text[:800])
        break
