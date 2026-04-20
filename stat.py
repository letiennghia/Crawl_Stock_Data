import os
import pymupdf as fitz
import pandas as pd
from tqdm import tqdm # Thư viện tạo thanh tiến trình cho đẹp

# 1. CẤU HÌNH ĐƯỜNG DẪN
BRONZE_DIR = 'data_lake/bronze/VN100'
OUTPUT_CSV = 'data_lake/stat/pdf_triage_stats.csv'

# 2. THUẬT TOÁN ĐÁNH GIÁ MẬT ĐỘ VĂN BẢN
def classify_pdf(file_path, sample_size=5):
    """
    Mở file PDF, đọc thử sample_size trang (bỏ qua trang bìa) 
    và phân loại dựa trên mật độ text.
    """
    try:
        # Mở file PDF
        doc = fitz.open(file_path)
        total_pages = len(doc)
        
        # Lỗi: File rỗng hoặc không có trang
        if total_pages == 0:
            return "CORRUPTED", 0
            
        # Lấy mẫu: Bỏ qua trang bìa (index 0), lấy tối đa sample_size trang
        start_page = 1 if total_pages > 1 else 0
        end_page = min(start_page + sample_size, total_pages)
        
        total_chars = 0
        pages_sampled = 0
        
        for page_num in range(start_page, end_page):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            total_chars += len(text.strip())
            pages_sampled += 1
            
        doc.close()
        
        # Nếu không lấy được trang mẫu nào
        if pages_sampled == 0:
            return "UNKNOWN", 0
            
        # Tính trung bình ký tự trên mỗi trang mẫu
        avg_chars_per_page = total_chars / pages_sampled
        
        # 3. NGƯỠNG PHÂN LOẠI (THRESHOLDS)
        if avg_chars_per_page < 50:
            return "SCANNED (Image-based)", round(avg_chars_per_page, 1)
        elif avg_chars_per_page > 500:
            return "NATIVE (Text-based)", round(avg_chars_per_page, 1)
        else:
            return "MIXED / LOW TEXT", round(avg_chars_per_page, 1)
            
    except fitz.FileDataError:
        return "CORRUPTED (File hỏng/Không phải PDF)", 0
    except Exception as e:
        return f"ERROR ({str(e)})", 0

# 4. LUỒNG QUÉT TOÀN BỘ DATA LAKE
def run_triage_pipeline():
    if not os.path.exists(BRONZE_DIR):
        print(f"Không tìm thấy thư mục: {BRONZE_DIR}")
        return
        
    pdf_files = []
    for root, dirs, files in os.walk(BRONZE_DIR):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, f))
                
    print(f"Bắt đầu phân loại {len(pdf_files)} file PDF trong Bronze Zone...\n")
    
    results = []
    
    # Dùng tqdm để bọc vòng lặp, hiển thị thanh tiến trình %
    for file_path in tqdm(pdf_files, desc="Đang quét"):
        filename = os.path.basename(file_path)
        
        # Phân tích file
        category, avg_density = classify_pdf(file_path)
        
        # Tách tên file để lấy Ticker và Năm (Giả định định dạng: VNM_BCTN_2022.pdf)
        parts = filename.replace('.pdf', '').split('_')
        ticker = parts[0] if len(parts) > 0 else "UNKNOWN"
        year = parts[-1] if len(parts) > 0 else "UNKNOWN"
        
        results.append({
            'Filename': filename,
            'Ticker': ticker,
            'Year': year,
            'Category': category,
            'Avg_Chars_Per_Page': avg_density,
            'File_Size_MB': round(os.path.getsize(file_path) / (1024 * 1024), 2)
        })
        
    # Xuất ra DataFrame và lưu thống kê
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    print("\n\n=== TỔNG KẾT THỐNG KÊ (TRIAGE REPORT) ===")
    summary = df['Category'].value_counts()
    for cat, count in summary.items():
        percentage = (count / len(pdf_files)) * 100
        print(f"- {cat}: {count} files ({percentage:.1f}%)")
        
    print(f"\nĐã lưu báo cáo chi tiết tại: {OUTPUT_CSV}")

if __name__ == "__main__":
    run_triage_pipeline()