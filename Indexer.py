# Cài đặt thư viện trước khi chạy: pip install vnstock pandas
from vnstock import listing_companies
import pandas as pd

def generate_target_list():
    print("Bắt đầu kéo dữ liệu danh sách niêm yết...")
    
    # Kéo toàn bộ danh sách công ty từ vnstock (mặc định lấy từ TCBS)
    # Dữ liệu trả về là một Pandas DataFrame chứa Ticker, Sàn, Ngành nghề...
    df = listing_companies()
    
    # Lọc rác: Chỉ lấy các mã đang giao dịch trên HOSE và HNX
    # Bỏ qua sàn UPCOM nếu nghiên cứu của chúng ta yêu cầu chuẩn mực báo cáo cao
    target_exchanges = ['HOSE', 'HNX']
    filtered_df = df[df['comGroupCode'].isin(target_exchanges)]
    
    # Chọn lọc các trường dữ liệu (columns) cần thiết cho nghiên cứu ESG
    # ticker: Mã CP, comGroupCode: Sàn, sector: Ngành nghề, industry: Nhóm ngành chi tiết
    final_df = filtered_df[['ticker', 'comGroupCode', 'sector', 'industry']]
    
    # Xuất ra file CSV
    output_file = 'hose_hnx_tickers_esg.csv'
    final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"Hoàn tất! Đã lưu {len(final_df)} mã chứng khoán vào file {output_file}.")

if __name__ == "__main__":
    generate_target_list()