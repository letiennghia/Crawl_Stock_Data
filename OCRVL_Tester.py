import os
import gc
import json
import numpy as np
from tqdm import tqdm
from pdf2image import pdfinfo_from_path
import fitz
from paddleocr import PaddleOCRVL
import time
import pandas as pd
import shutil

CURRENT_OUTPUT_DIR = None

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
def OCRVL(PDF_PATH = None, OUTPUT_DIR = "./output_VL", ocr = None, overwrite = False):
    start_time = time.time()
    # Khởi tạo thư mục và mô hình
    ticker = os.path.basename(PDF_PATH).split("_")[0]  # Lấy ticker từ tên file PDF
    year = os.path.basename(PDF_PATH).split("_")[2].split(".")[0]  # Lấy năm từ tên file PDF
    OUTPUT_DIR = os.path.join(OUTPUT_DIR, ticker, year)
    global CURRENT_OUTPUT_DIR
    CURRENT_OUTPUT_DIR = OUTPUT_DIR
    if(not os.path.exists(OUTPUT_DIR)):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    elif os.path.exists(OUTPUT_DIR) and not overwrite:
        print(f"Existing output directory found: {OUTPUT_DIR}. Skipping, to overwrite config overwrite variable as True.")
        return
    # ==========================================
    # 2. KHẢO SÁT TÀI LIỆU VÀ CHIA CHUNK
    # ==========================================
    try:
        doc = fitz.open(PDF_PATH)
        total_pages = doc.page_count
        print(f"📄 Đã tìm thấy Báo cáo: Tổng cộng {total_pages} trang.")
    except Exception as e:
        print(f"❌ Lỗi đọc PDF: {e}")
        return

    # Biến đếm kết quả output cho tên file mảnh
    count = 0
    chunk_size = 100
    
    # ==========================================
    # 3. YÊU CẦU PADDLEOCRVL XỬ LÝ THEO CHUNK
    # ==========================================
    print(f"🔄 Đang xử lý theo từng chunk ({chunk_size} trang/chunk)...")
    
    for start_idx in range(0, total_pages, chunk_size):
        end_idx = min(start_idx + chunk_size, total_pages) - 1
        print(f"\n🔄 Đang xử lý chunk trang {start_idx + 1} đến {end_idx + 1}...")
        
        # Tạo PDF tạm cho chunk
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(doc, from_page=start_idx, to_page=end_idx)
        chunk_pdf_path = os.path.join(OUTPUT_DIR, "temp_chunk.pdf")
        chunk_doc.save(chunk_pdf_path)
        chunk_doc.close()
        
        # Chạy OCR
        output_generator = ocr.predict(
            input=chunk_pdf_path,
            use_layout_detection=True,
            use_chart_recognition=True
        )
        
        all_results = []
        for page_res in output_generator:
            all_results.append(page_res)
                
        print(f"🧠 Đang tái cấu trúc ngữ nghĩa chunk ({len(all_results)} trang)...")
        final_output = ocr.restructure_pages(all_results)
        
        for res in final_output:
            count += 1
            filename = os.path.basename(PDF_PATH).replace(".pdf", f"_{count}.json")
            filename_md = os.path.basename(PDF_PATH).replace(".pdf", f"_{count}.md")

            # Lưu định dạng JSON để nạp vào Database/RAG
            res.save_to_json(save_path=os.path.join(OUTPUT_DIR, filename))        
            # Lưu định dạng Markdown để con người đọc / LLM Fine-tuning
            res.save_to_markdown(save_path=os.path.join(OUTPUT_DIR, filename_md))
            
        del all_results
        del final_output
        gc.collect()
        
        # Xoá file PDF tạm
        if os.path.exists(chunk_pdf_path):
            os.remove(chunk_pdf_path)
            
    doc.close()

    # ==========================================
    # 4. TỔNG HỢP VÀ DỌN DẸP
    # ==========================================
    print("🔄 Đang gộp các file Markdown & JSON phần mảnh, sau đó dọn dẹp...")
    merged_md_filename = os.path.basename(PDF_PATH).replace(".pdf", ".md")
    merged_md_path = os.path.join(OUTPUT_DIR, merged_md_filename)
    
    merged_json_filename = os.path.basename(PDF_PATH).replace(".pdf", ".json")
    merged_json_path = os.path.join(OUTPUT_DIR, merged_json_filename)
    
    merged_json_data = []

    with open(merged_md_path, "w", encoding="utf-8") as outfile:
        for i in range(1, count + 1):
            # Xử lý Markdown
            part_md_path = os.path.join(OUTPUT_DIR, os.path.basename(PDF_PATH).replace(".pdf", f"_{i}.md"))
            if os.path.exists(part_md_path):
                with open(part_md_path, "r", encoding="utf-8") as infile:
                    outfile.write(infile.read().strip() + "\n\n")
                os.remove(part_md_path)
            
            # Xử lý JSON (đọc, gộp và xoá file rác)
            part_json_path = os.path.join(OUTPUT_DIR, os.path.basename(PDF_PATH).replace(".pdf", f"_{i}.json"))
            if os.path.exists(part_json_path):
                try:
                    with open(part_json_path, "r", encoding="utf-8") as json_infile:
                        data = json.load(json_infile)
                        # Nếu là list thì nối vào list tổng, nếu là dict thì append trực tiếp
                        if isinstance(data, list):
                            merged_json_data.extend(data)
                        else:
                            merged_json_data.append(data)
                except Exception as e:
                    print(f"Lỗi khi đọc JSON phần mảnh: {part_json_path}. Chi tiết: {e}")
                os.remove(part_json_path)

    # Xuất file JSON tổng hợp
    with open(merged_json_path, "w", encoding="utf-8") as json_outfile:
        json.dump(merged_json_data, json_outfile, indent=4, ensure_ascii=False)
    end_time = time.time()
    print(f"⏱️  Time taken: {end_time - start_time:.2f} seconds")
    print(f"✅ Đã gộp thành công tại:\n  - {merged_md_path}\n  - {merged_json_path}, Total time: {end_time - start_time:.2f} seconds, Time per page: {(end_time - start_time)/total_pages:.2f} seconds")

def main():
    # Load configuration from environment variables with defaults
    INPUT_FILE = os.environ.get("INPUT_CSV", "./data_lake/stat/pdf_triage_stats.csv")
    OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "./output_VL_merged")
    VLLM_URL = os.environ.get("VLLM_URL", "http://localhost:8118/v1")
    TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"
    
    print(f"🔧 CONFIGURATION:")
    print(f"  - INPUT_CSV: {INPUT_FILE}")
    print(f"  - OUTPUT_DIR: {OUTPUT_DIR}")
    print(f"  - VLLM_URL: {VLLM_URL}")
    print(f"  - TEST_MODE: {TEST_MODE}")

    df = pd.read_csv(INPUT_FILE)
    ocr = PaddleOCRVL(
        vl_rec_backend="fastdeploy-server", 
        vl_rec_server_url=VLLM_URL,
        use_doc_orientation_classify=True,
        use_doc_unwarping=True,
        use_layout_detection=True,
        use_chart_recognition=True,
        use_seal_recognition=True,
    )
    
    if TEST_MODE:
        print("\n🧪 Running in TEST MODE (processing single file)...")
        # Test mode defaults
        test_pdf = os.environ.get("TEST_PDF", "data_lake/silver/VN100/ACB/ACB_BCTN_2021.pdf")
        OCRVL(PDF_PATH=test_pdf, ocr=ocr, overwrite=True, OUTPUT_DIR=OUTPUT_DIR)
    else:
        print(f"\n🚀 Running in BATCH MODE ({len(df)} files in CSV)...")
        for idx, row in df.iterrows():
            pdf_path_raw = row['Path']
            # Re-format path in case of Windows backslashes
            pdf_path = pdf_path_raw.replace('\\', '/')
            cat_type = row['Category']
            if cat_type in ["SCANNED"]:
                print(f"\n🔍 Đang xử lý: {pdf_path}")
                OCRVL(PDF_PATH=pdf_path, ocr=ocr, overwrite=False, OUTPUT_DIR=OUTPUT_DIR)

if __name__ == "__main__":
    while True:
        try:
            main()
            break
        except Exception as e:
            print(f"Exception caught in main: {e}")
            if CURRENT_OUTPUT_DIR and os.path.exists(CURRENT_OUTPUT_DIR):
                print(f"Removing current folder to retry: {CURRENT_OUTPUT_DIR}")
                shutil.rmtree(CURRENT_OUTPUT_DIR)
            print("Rerunning main() in 5 seconds...")
            time.sleep(5)
