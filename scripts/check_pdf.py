import fitz # PyMuPDF
import sys, os

pdf_path = r"C:\Users\Indian Railway\.gemini\antigravity\brain\9513809e-d90d-4964-98bd-d36e4e05f542\.user_uploaded\media_1791962055864_26843c4a.pdf"

if not os.path.exists(pdf_path):
    print("PDF not found at:", pdf_path)
    # search for it
    import glob
    files = glob.glob(r"C:\Users\Indian Railway\.gemini\antigravity\brain\**\*.pdf", recursive=True)
    print("Found PDFs:", files[:5])
else:
    doc = fitz.open(pdf_path)
    print("Total pages in PDF:", len(doc))
    print("\n--- TOC / First 15 pages sample ---")
    for page_num in range(min(15, len(doc))):
        text = doc[page_num].get_text()
        first_line = text.strip().split('\n')[0] if text.strip() else 'EMPTY'
        print(f"Page {page_num+1}: {first_line[:80]}")
