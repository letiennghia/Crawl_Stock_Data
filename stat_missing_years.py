import os
import pandas as pd

# CẤU HÌNH ĐƯỜNG DẪN
BRONZE_DIR = 'data_lake/bronze/VN100'
OUTPUT_CSV = 'data_lake/stat/missing_years_report.csv'

def run_missing_years_stat():
    if not os.path.exists(BRONZE_DIR):
        print(f"Không tìm thấy thư mục: {BRONZE_DIR}")
        return
        
    pdf_files = []
    for root, dirs, files in os.walk(BRONZE_DIR):
        for f in files:
            if f.lower().endswith('.pdf'):
                pdf_files.append(f)
                
    print(f"Đã tìm thấy {len(pdf_files)} file PDF. Đang phân tích các năm bảo cáo...\n")
    
    # Cấu trúc: { 'VNM': set([2021, 2022, 2023]), ... }
    ticker_years = {}
    
    for filename in pdf_files:
        name_no_ext = filename[:-4]
        parts = name_no_ext.split('_')
        
        # Kiểm tra giả định file hợp lệ: Ticker_BCTN_Year
        if len(parts) >= 3:
            ticker = parts[0].upper()
            year_str = parts[2]
            
            if year_str.isdigit() and len(year_str) == 4:
                year = int(year_str)
                if ticker not in ticker_years:
                    ticker_years[ticker] = set()
                ticker_years[ticker].add(year)
                
    # Mục tiêu thống kê từ 2015 đến 2025
    expected_years = set(range(2015, 2025))
    results = []
    
    for ticker, present_years in sorted(ticker_years.items()):
        missing_years = sorted(list(expected_years - present_years))
        missing_str = ", ".join(map(str, missing_years)) if missing_years else "Đủ bộ (Không thiếu)"
        
        results.append({
            'Ticker': ticker,
            'Years_Found': len(present_years),
            'Missing_Count': len(missing_years),
            'Missing_Years_List': missing_str
        })
        
    df = pd.DataFrame(results)
    
    # Xuất ra CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    
    # In báo cáo ra Terminal
    total_tickers = len(ticker_years)
    tickers_full = len(df[df['Missing_Count'] == 0]) if not df.empty else 0
    tickers_missing = total_tickers - tickers_full
    
    print("=== BÁO CÁO THỐNG KÊ THIẾU NĂM (2015 - 2025) ===")
    print(f"Tổng số mã cổ phiếu có nhận diện được file: {total_tickers}")
    print(f"Số mã THU THẬP ĐỦ (0 thiếu): {tickers_full}")
    print(f"Số mã BỊ THIẾU (thiếu >= 1 năm): {tickers_missing}")
    
    if not df.empty:
        print("\nTOP CÁC MÃ BỊ THIẾU NHIỀU NHẤT:")
        top_missing = df.sort_values(by='Missing_Count', ascending=False).head(15)
        for _, row in top_missing.iterrows():
            if row['Missing_Count'] > 0:
                print(f" - [{row['Ticker']}]: Thiếu {row['Missing_Count']} năm -> {row['Missing_Years_List']}")
            
    print(f"\nĐã xuất file báo cáo chi tiết từng mã tại: {OUTPUT_CSV}")

if __name__ == "__main__":
    run_missing_years_stat()
