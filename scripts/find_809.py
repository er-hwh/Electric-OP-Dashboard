import pymupdf as fitz

pdf_path = r"C:\Users\Indian Railway\.gemini\antigravity\brain\9513809e-d90d-4964-98bd-d36e4e05f542\.user_uploaded\media_1791962055864_26843c4a.pdf"
doc = fitz.open(pdf_path)

found_pages = []
for p in range(len(doc)):
    text = doc[p].get_text()
    if "8.09" in text:
        found_pages.append(p + 1)

print("Pages with 8.09:", found_pages)
for p in found_pages:
    print(f"\n--- PAGE {p} ---")
    for line in doc[p-1].get_text().split('\n'):
        if "8.09" in line or "Obstruction in the face" in line:
            print("  ", line)
