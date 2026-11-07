import pymupdf as fitz
import re, json

pdf_path = r"C:\Users\Indian Railway\.gemini\antigravity\brain\9513809e-d90d-4964-98bd-d36e4e05f542\.user_uploaded\media_1791962055864_26843c4a.pdf"
doc = fitz.open(pdf_path)

# Extract full text of TOC pages (11 to 20)
toc_text = ""
for p in range(10, 20):
    toc_text += f"\n--- TOC PAGE {p+1} ---\n" + doc[p].get_text()

with open("scripts/raw_toc_text.txt", "w", encoding="utf-8") as f:
    f.write(toc_text)

print("Saved raw TOC text. Length:", len(toc_text))
