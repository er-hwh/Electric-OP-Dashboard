import pymupdf as fitz

pdf_path = r"C:\Users\Indian Railway\.gemini\antigravity\brain\9513809e-d90d-4964-98bd-d36e4e05f542\.user_uploaded\media_1791962055864_26843c4a.pdf"
doc = fitz.open(pdf_path)

for p in range(25, 36):
    text = doc[p].get_text()
    if "2.09" in text:
        print(f"=== PAGE {p+1} ===")
        print(text)
