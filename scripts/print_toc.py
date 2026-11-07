import pymupdf as fitz
import sys

pdf_path = r"C:\Users\Indian Railway\.gemini\antigravity\brain\9513809e-d90d-4964-98bd-d36e4e05f542\.user_uploaded\media_1791962055864_26843c4a.pdf"
doc = fitz.open(pdf_path)

print("=== TABLE OF CONTENTS FROM PDF (Pages 11 to 22) ===")
for p in range(10, 22):
    text = doc[p].get_text()
    print(f"\n--- PAGE {p+1} ---")
    print(text)
