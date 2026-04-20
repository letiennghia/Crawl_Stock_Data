import os
import json
import argparse
from pathlib import Path
import pandas as pd
from docling.datamodel import vlm_model_specs
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    EasyOcrOptions,
    TableFormerMode,
    VlmPipelineOptions
)

from docling.pipeline.vlm_pipeline import VlmPipeline
# ==========================================
# CONFIGURATION
# ==========================================
# Set this to a file path to test a single file, or a folder path to process multiple files.
# Example for a test file: './test_split/test_1.pdf'
# Example for a folder: 'data_lake/bronze/VN100'

CSV_PATH = './data_lake/stat/pdf_triage_stats.csv'

# Base output directory
DEFAULT_OUTPUT_DIR = 'data/markdown'
# ==========================================

def extract_ticker_and_year(filename: str):
    """
    Extract Ticker and Year from filename. 
    Assumes format like: ACB_BCTN_2007.pdf or ACB_BCTN_2007_1.pdf
    Year is expected at exactly the 3rd position.
    """
    parts = filename.replace('.pdf', '').split('_')
    ticker = parts[0] if len(parts) > 0 else "UNKNOWN"
    year = parts[2] if len(parts) > 2 else "UNKNOWN"
    return ticker, year

def process_file(file_path: str, output_base_dir: str, vlm=False, converter=None,overwrite=False):
    """
    Process a single PDF file using Docling and save as MD and JSON in output/{ticker}/{year}.
    """
    filepath_obj = Path(file_path)
    if not filepath_obj.is_file() or filepath_obj.suffix.lower() != '.pdf':
        print(f"Skipping non-PDF or non-existent file: {file_path}")
        return

    filename = filepath_obj.name
    
    # Extract ticker and year using the established logic
    ticker, year = extract_ticker_and_year(filename)
    
    # Construct output directory: output/{ticker}/{year}
    out_dir = Path(output_base_dir) / ticker
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
    if not overwrite:
        if out_dir.exists():
            #truely check if our file are in there
            md_path = out_dir / f"{filepath_obj.stem}.md"
            json_path = out_dir / f"{filepath_obj.stem}.json"
            if md_path.exists() or json_path.exists():
                print(f"Skipping {filename}: Output files already exist")
                return
    print(f"\nProcessing: {filename}")
    print(f"Target Output Directory: {out_dir}")
    
    

    if vlm:
        print("  - Converting with Docling (VLM)...")
    else:
        print("  - Converting with Docling (EasyOCR)...")
    result = converter.convert(str(file_path))
    doc = result.document
        
    # Export to Markdown
    md_content = doc.export_to_markdown()
    md_path = out_dir / f"{filepath_obj.stem}.md"
    with open(md_path, "w", encoding="utf-8") as md_file:
        md_file.write(md_content)
    print(f"  - Saved Markdown: {md_path}")
        
    # Export to JSON
    # doc_dict = doc.export_to_dict()
    # json_path = out_dir / f"{filepath_obj.stem}.json"
    # with open(json_path, "w", encoding="utf-8") as json_file:
    #     json.dump(doc_dict, json_file, indent=2, ensure_ascii=False)
    # print(f"  - Saved JSON: {json_path}")
        


def main():
    parser = argparse.ArgumentParser(description="Docling Service to convert PDFs to MD and JSON.")
    parser.add_argument(
        "-c", "--csv", 
        default=CSV_PATH,
        help=f"CSV path. Default: {CSV_PATH}"
    )
    parser.add_argument(
        "-o", "--output", 
        default=DEFAULT_OUTPUT_DIR, 
        help=f"Base output directory. Default: {DEFAULT_OUTPUT_DIR}"
    )
    parser.add_argument(
        "-b", "--batch_number", 
        default=None,
        help=f"Batch number out of 5 batches"
    )
    parser.add_argument(
        "-v", "--vlm", 
        default=False,
        help=f"Use VLM"
    )
    
    args = parser.parse_args()
    vlm = args.vlm
    pdf_df = pd.read_csv(args.csv)
    pdf_df = pdf_df[pdf_df['Category'] == 'NATIVE']
    batch_number = args.batch_number
    count_success = 0
    count_fail = 0
    failed_files = []

    try:
        if vlm:
            # Convert using Docling with VLM
            vlm_options = VlmPipelineOptions(
                do_ocr=True,
                do_table_structure=True,
                do_vlm=True,
                do_layout=True,
            )
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_cls=VlmPipeline, vlm_options=vlm_options)
                }
            )

        else:
            # Convert using Docling with EasyOCR
            os.environ["EASYOCR_MODULE_PATH"] = "1" # Optional, to suppress warnings if any
            ocr_options = EasyOcrOptions(lang=["vi"])
            pipeline_options = PdfPipelineOptions(do_ocr=True, ocr_options=ocr_options)
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = True
            pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
            pipeline_options.table_structure_options = TableStructureOptions(
                do_cell_matching=True
            )
            converter = DocumentConverter(
                    format_options={
                        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options, backend =PyPdfiumDocumentBackend)
                    }
                )
    except Exception as e:
        print(f"Error initializing Docling: {e}")
        return

    if batch_number is not None:
        print(f"Processing batch {batch_number} out of 5")
        batch_number = int(batch_number)
        output_base_dir = args.output + "_" + str(batch_number)
        pdf_df = pdf_df.iloc[(batch_number - 1) * (len(pdf_df) // 5):batch_number * (len(pdf_df) // 5)]
        for index, row in pdf_df.iterrows():
            try:
                process_file(row['Path'], output_base_dir, vlm=False, converter=converter, overwrite=False)
                count_success += 1
            except Exception as e:
                failed_files.append(row['Path'])
                count_fail += 1
    else:
        print(f"Processing all batches")
        output_base_dir = args.output
        for index, row in pdf_df.iterrows():
            try:
                process_file(row['Path'], output_base_dir, vlm=False, converter=converter, overwrite=False)
                count_success += 1
            except Exception as e:
                failed_files.append(row['Path'])
                count_fail += 1
    print(f"--- Docling Service Pipeline ---")
    print(f"CSV Path: {args.csv}")
    print(f"Output Base: {output_base_dir}\n")

if __name__ == "__main__":
    main()
