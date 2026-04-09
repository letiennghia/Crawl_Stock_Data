import os
import re
import pymupdf as fitz
import pandas as pd
import zipfile
from tqdm import tqdm

# 1. CẤU HÌNH ĐƯỜNG DẪN
BRONZE_DIR = 'data_lake/bronze/VN100'
OUTPUT_CSV = 'data_lake/stat/pdf_pages_stats.csv'
TO_DELETE_CSV = 'data_lake/stat/pdf_to_be_deleted.csv' # Thêm báo cáo xoá

# 2. THUẬT TOÁN ĐẾM SỐ TRANG
def get_pdf_pages(file_path):
    """
    Mở file PDF và trả về số trang, phân loại dựa trên độ dài (<=10 trang là SHORT)
    """
    try:
        doc = fitz.open(file_path)
        total_pages = len(doc)
        doc.close()
        
        if total_pages == 0:
            return "CORRUPTED (0 pages)", 0
        elif total_pages <= 8:
            return "SHORT (<= 8 pages)", total_pages
        else:
            return "LONG (> 8 pages)", total_pages
            
    except fitz.FileDataError:
        return "CORRUPTED (File hỏng/Không phải PDF)", 0
    except Exception as e:
        return f"ERROR ({str(e)})", 0

def check_filename_format(filename):
    """
    Đánh giá độ khớp tên file với format chuẩn Ticker_BCTN_Year.pdf
    Trả về điểm từ 0.0 đến 1.0
    """
    score = 0.0
    total_criteria = 5
    
    if filename.lower().endswith('.pdf'):
        score += 1
        
    name_no_ext = filename[:-4] if filename.lower().endswith('.pdf') else filename
    parts = name_no_ext.split('_')
    
    if len(parts) == 3:
        score += 1
        if re.match(r'^[A-Z0-9]{3}$', parts[0]): score += 1
        if parts[1].upper() == 'BCTN': score += 1
        if re.match(r'^(19|20)\d{2}$', parts[2]): score += 1
    else:
        if re.search(r'[A-Z0-9]{3}', name_no_ext): score += 1
        if re.search(r'BCTN', name_no_ext, re.IGNORECASE): score += 1
        if re.search(r'(19|20)\d{2}', name_no_ext): score += 1
            
    return score / total_criteria

# 3. LUỒNG QUÉT
def run_pages_stat_pipeline():
    if not os.path.exists(BRONZE_DIR):
        print(f"Không tìm thấy thư mục: {BRONZE_DIR}")
        return
        
    # BƯỚC 1: XỬ LÝ FILE ZIP VÀ RAR
    zip_files = []
    rar_files = []
    for root, _, files in os.walk(BRONZE_DIR):
        for f in files:
            if f.lower().endswith('.zip'):
                zip_files.append(os.path.join(root, f))
            elif f.lower().endswith('.rar'):
                rar_files.append(os.path.join(root, f))
                
    if zip_files:
        print(f"Tìm thấy {len(zip_files)} file ZIP. Bắt đầu giải nén...\n")
        for zip_path in tqdm(zip_files, desc="Đang giải nén ZIP"):
            try:
                extract_dir = os.path.dirname(zip_path)
                base_name = os.path.basename(zip_path)[:-4]
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    pdf_members = [m for m in zip_ref.namelist() if m.lower().endswith('.pdf') and '__MACOSX' not in m]
                    for i, member in enumerate(pdf_members):
                        target_name = f"{base_name}.pdf" if len(pdf_members) == 1 else f"{base_name}_{i+1}.pdf"
                        target_path = os.path.join(extract_dir, target_name)
                        with zip_ref.open(member) as source, open(target_path, "wb") as target:
                            target.write(source.read())
            except Exception as e:
                print(f"Lỗi khi giải nén file {zip_path}: {e}")

    if rar_files:
        import rarfile
        if os.path.exists(r"C:\Program Files\WinRAR\UnRAR.exe"):
            rarfile.UNRAR_TOOL = r"C:\Program Files\WinRAR\UnRAR.exe"
            
        print(f"Tìm thấy {len(rar_files)} file RAR. Bắt đầu giải nén...\n")
        for rar_path in tqdm(rar_files, desc="Đang giải nén RAR"):
            try:
                extract_dir = os.path.dirname(rar_path)
                base_name = os.path.basename(rar_path)[:-4]
                with rarfile.RarFile(rar_path, 'r') as rar_ref:
                    pdf_members = [m for m in rar_ref.namelist() if m.lower().endswith('.pdf') and '__MACOSX' not in m]
                    for i, member in enumerate(pdf_members):
                        target_name = f"{base_name}.pdf" if len(pdf_members) == 1 else f"{base_name}_{i+1}.pdf"
                        target_path = os.path.join(extract_dir, target_name)
                        with rar_ref.open(member) as source, open(target_path, "wb") as target:
                            target.write(source.read())
            except Exception as e:
                print(f"Lỗi khi giải nén file RAR {rar_path}: {e}\n(Chú ý: Cần WinRAR ở C:\\Program Files\\WinRAR\\UnRAR.exe hoặc thêm unrar vào PATH hệ thống)")

    # BƯỚC 2: QUÉT FILE PDF VÀ KIỂM TRA
    pdf_files = []
    for root, _, files in os.walk(BRONZE_DIR):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, f))
                
    print(f"\nBắt đầu kiểm tra {len(pdf_files)} file PDF...\n")
    
    results = []
    to_delete = [] # Lưu danh sách để ghi ra CSV
    
    deleted_count = 0
    deleted_format_count = 0
    
    for file_path in tqdm(pdf_files, desc="Đang phân tích PDF"):
        filename = os.path.basename(file_path)
        format_score = check_filename_format(filename)
        pages = 0
        
        if format_score < 0.8:
            category = f"TO BE DELETED - INVALID FORMAT ({(format_score*100):.0f}%)"
            deleted_format_count += 1
            to_delete.append({
                'File_Path': file_path,
                'Filename': filename,
                'Reason': 'INVALID FORMAT',
                'Format_Match': f"{(format_score*100):.0f}%",
                'Total_Pages': 0
            })
        else:
            cat_pages, pages = get_pdf_pages(file_path)
            category = cat_pages
            if pages <= 8:
                category += " (TO BE DELETED)"
                deleted_count += 1
                to_delete.append({
                    'File_Path': file_path,
                    'Filename': filename,
                    'Reason': 'SHORT PAGES (<= 10)',
                    'Format_Match': f"{(format_score*100):.0f}%",
                    'Total_Pages': pages
                })
            
        parts = filename.replace('.pdf', '').split('_')
        ticker = parts[0] if len(parts) > 0 else "UNKNOWN"
        year = parts[-1] if len(parts) > 0 else "UNKNOWN"
        
        results.append({
            'Filename': filename,
            'Ticker': ticker,
            'Year': year,
            'Category': category,
            'Format_Match': f"{(format_score*100):.0f}%",
            'Total_Pages': pages,
            'File_Size_MB': round(os.path.getsize(file_path) / (1024 * 1024), 2),
            'File_Path': file_path
        })
        
    df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    df_delete = pd.DataFrame(to_delete)
    if not df_delete.empty:
        df_delete.to_csv(TO_DELETE_CSV, index=False, encoding='utf-8-sig')
        
    print("\n\n=== TỔNG KẾT THỐNG KÊ ===")
    print(f"Tổng số file PDF đã quét: {len(pdf_files)}")
    print(f"Số file CHUẨN BỊ xoá do sai cấu trúc tên (<80%): {deleted_format_count}")
    print(f"Số file CHUẨN BỊ xoá do dưới 10 trang: {deleted_count}")
    
    print("\nChi tiết phân loại:")
    summary = df['Category'].value_counts()
    for cat, count in summary.items():
        percentage = (count / len(pdf_files)) * 100 if len(pdf_files) > 0 else 0
        print(f"- {cat}: {count} files ({percentage:.1f}%)")
        
    print(f"\nĐã lưu báo cáo thống kê chung tại: {OUTPUT_CSV}")
    if not df_delete.empty:
        print(f"!!! QUAN TRỌNG: Đã lưu danh sách các file CHUẨN BỊ XÓA ra file: {TO_DELETE_CSV}")
        print("Vui lòng mở file trên kiểm tra. Nếu ổn có thể bật lại hàm os.remove() để xoá vật lý.")

    # BƯỚC 3: XÓA VẬT LÝ (TỰ ĐỘNG)
    if not df_delete.empty:
        print(f"\nBắt đầu xoá {len(df_delete)} file đã đánh dấu...\n")
        deleted_actual_count = 0
        for _, row in df_delete.iterrows():
            file_path = row['File_Path']
            try:
                os.remove(file_path)
                deleted_actual_count += 1
                # print(f"Đã xoá: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Lỗi khi xoá {file_path}: {e}")
        
        print(f"\n=== KẾT QUẢ CUỐI CÙNG ===")
        print(f"Tổng số file PDF quét: {len(pdf_files)}")
        print(f"Số file đã xoá thành công: {deleted_actual_count}")
        print(f"Số file còn lại: {len(pdf_files) - deleted_actual_count}")

if __name__ == "__main__":
    run_pages_stat_pipeline()
