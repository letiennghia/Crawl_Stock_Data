import os
import shutil
from pathlib import Path

def main():
    base_dir = Path(r"c:\Server\Data\StockIndex\Crawl_Stock_Data")
    data_dir = base_dir / "data"
    
    pdf_dest = data_dir / "pdf"
    md_dest = data_dir / "markdown"
    
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    if not pdf_dest.exists():
        pdf_dest.mkdir(parents=True, exist_ok=True)
    if not md_dest.exists():
        md_dest.mkdir(parents=True, exist_ok=True)

    print("--- Starting PDF Copy ---")
    # 1. Copy PDF files
    silver_dir = base_dir / "data_lake" / "silver"
    pdf_count = 0
    if silver_dir.exists():
        for pdf_path in silver_dir.rglob('*.pdf'):
            # The folder containing the PDF is the ticker folder
            ticker = pdf_path.parent.name
            target_ticker_dir = pdf_dest / ticker
            if not target_ticker_dir.exists():
                target_ticker_dir.mkdir(parents=True, exist_ok=True)
            
            target_path = target_ticker_dir / pdf_path.name
            if not target_path.exists():
                shutil.copy2(pdf_path, target_path)
            else:
                print(f"File {target_path} already exists. Skipping.")
            pdf_count += 1
    
    print(f"Processed {pdf_count} PDF files.")

    print("--- Starting Markdown Copy ---")
    # 2. Copy MD files
    output_dirs = [
        "output_1", "output_2", "output_3", "output_4", "output_5", "output_VL_merged"
    ]
    
    md_count = 0
    for out_d in output_dirs:
        out_path = base_dir / out_d
        if out_path.exists():
            for md_path in out_path.rglob('*.md'):
                # Extract the ticker from the directory directly under the output source
                rel_path = md_path.relative_to(out_path)
                ticker = rel_path.parts[0]
                
                target_ticker_dir = md_dest / ticker
                target_ticker_dir.mkdir(exist_ok=True)
                
                target_path = target_ticker_dir / md_path.name
                if not target_path.exists():
                    shutil.copy2(md_path, target_path)
                else:
                    print(f"File {target_path} already exists. Skipping.")
                md_count += 1
    
    print(f"Processed {md_count} Markdown files.")
    print(f"Data has been successfully organized into: {data_dir}")

if __name__ == "__main__":
    main()
