import os
import gc
import numpy as np
from tqdm import tqdm
from pdf2image import pdfinfo_from_path, convert_from_path
from paddleocr import PaddleOCRVL
import pandas as pd

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================
def OCRVL(PDF_PATH = None, OUTPUT_DIR = "./output_VL"
,BATCH_SIZE = 32      # Số trang xử lý mỗi mẻ (Tối ưu cho RAM 16GB-32GB)
,DPI = 200, ocr = None, overwrite = False):            # Ép xung độ phân giải chống rụng dấu Tiếng Việt
    # Khởi tạo thư mục và mô hình
    ticker = os.path.basename(PDF_PATH).split("_")[0]  # Lấy ticker từ tên file PDF
    year = os.path.basename(PDF_PATH).split("_")[2].split(".")[0]  # Lấy năm từ tên file PDF
    OUTPUT_DIR = os.path.join(OUTPUT_DIR, ticker, year)
    if(not os.path.exists(OUTPUT_DIR)):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    elif os.path.exists(OUTPUT_DIR) and not overwrite:
        print(f"Existing output directory found: {OUTPUT_DIR}. Skipping, to overwrite config overwrite variable as True.")
        return
    # ==========================================
    # 2. KHẢO SÁT TÀI LIỆU (KHÔNG TẢI VÀO RAM)
    # ==========================================
    try:
        info = pdfinfo_from_path(PDF_PATH)
        total_pages = info["Pages"]
        print(f"📄 Đã tìm thấy Báo cáo: Tổng cộng {total_pages} trang.")
    except Exception as e:
        print(f"❌ Lỗi đọc PDF: {e}")
        exit()

    # Biến lưu trữ kết quả của tất cả các trang
    all_page_results = []

    # ==========================================
    # 3. VÒNG LẶP XỬ LÝ THEO LÔ (BATCH PROCESSING)
    # ==========================================
    # Sử dụng tqdm để tạo thanh tiến trình cực đẹp ngoài Terminal
    with tqdm(total=total_pages, desc="Tiến độ OCR", unit="trang") as pbar:
        
        for start_page in range(1, total_pages + 1, BATCH_SIZE):
            end_page = min(start_page + BATCH_SIZE - 1, total_pages)
            
            # --- BƯỚC 3.1: BÓC PDF SANG ẢNH (SLIDING WINDOW) ---
            # Chỉ nạp đúng 32 trang vào RAM
            images = convert_from_path(
                PDF_PATH, 
                dpi=DPI, 
                first_page=start_page, 
                last_page=end_page
            )
            
            # --- BƯỚC 3.2: CHẠY OCR TỪNG TRANG TRONG LÔ ---
            batch_results = []
            for img in images:
                # Chuyển đổi PIL Image (RGB) sang Numpy Array (BGR) cho Paddle
                cv_img = np.array(img)[:, :, ::-1].copy()
                
                # Đưa ảnh mảng số vào PaddleOCRVL
                output = ocr.predict(input=cv_img)
                
                # Tùy thuộc vào thiết kế của PaddleOCRVL, output có thể là 1 list hoặc 1 object
                # Ta ép kiểu về list và lấy kết quả trang hiện tại
                page_res = list(output)[0] 
                batch_results.append(page_res)
                
                # Cập nhật thanh tiến trình tăng lên 1
                pbar.update(1)
                
                # Xóa ảnh cục bộ để dọn RAM
                del cv_img
                del img
                
            # Gom kết quả của Lô này vào Kho lưu trữ Tổng
            all_page_results.extend(batch_results)
            
            # --- BƯỚC 3.3: DỌN RÁC BỘ NHỚ ---
            del images
            del batch_results
            gc.collect() # Ép Python xả RAM ngay lập tức

    # ==========================================
    # 4. TỔNG HỢP VÀ XUẤT DỮ LIỆU
    # ==========================================
    print("\n🧠 Đang kích hoạt VLM để tái cấu trúc ngữ nghĩa toàn bộ tài liệu...")
    # Chạy hàm restructure của bạn trên toàn bộ tài liệu đã gom lại
    final_output = ocr.restructure_pages(all_page_results)

    print("💾 Đang lưu kết quả...")
    count = 0
    for res in final_output:
        # res.print() # Bỏ comment nếu muốn in ra terminal
        count += 1
        filename = PDF_PATH.split("/")[-1].replace(".pdf", f"_{count}.json")
        filename_md = PDF_PATH.split("/")[-1].replace(".pdf", f"_{count}.md")

        # Lưu định dạng JSON để nạp vào Database/RAG
        res.save_to_json(save_path=os.path.join(OUTPUT_DIR, filename))        
        # Lưu định dạng Markdown để con người đọc / LLM Fine-tuning
        res.save_to_markdown(save_path=os.path.join(OUTPUT_DIR, filename_md))

def main():
    INPUT_FILE = "./data_lake/stat/pdf_triage_stats.csv"  # File CSV chứa đường dẫn PDF
    df = pd.read_csv(INPUT_FILE)
    ocr = PaddleOCRVL()
    for idx, row in df.iterrows():
        pdf_path = row['Path']
        type = row['Category']
        if type in ["SCANNED"]:
            print(f"\n🔍 Đang xử lý: {pdf_path}")
            OCRVL(PDF_PATH=pdf_path, ocr=ocr)
if __name__ == "__main__":
    main()
