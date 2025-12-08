import fitz  # PyMuPDF
import sys

# Set stdout to handle utf-8
sys.stdout.reconfigure(encoding='utf-8')

def analyze_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        print(f"Analyzing {pdf_path}...")
        for page_num, page in enumerate(doc):
            print(f"--- Page {page_num + 1} ---")
            # Get blocks (x0, y0, x1, y1, text, block_no, block_type)
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: b[1]) # Sort by vertical position
            
            for b in blocks:
                print(f"Block: {b[4].strip()}")
                print("-" * 10)
            print("=" * 20)
    except Exception as e:
        print(f"Error analyzing PDF: {e}")

if __name__ == "__main__":
    analyze_pdf("CHITIN INDIAN OCEAN EXPORTERS.pdf")
