import os
import json
import time
import random
import requests
import re
from tqdm import tqdm
from fake_useragent import UserAgent

# 1. THIẾT LẬP HẠ TẦNG "DATA LAKE" CƠ BẢN
BRONZE_DIR = "data_lake/bronze/VN100"
os.makedirs(BRONZE_DIR, exist_ok=True)

# 2. HÀM NGỤY TRANG VÀ KIỂM SOÁT NHỊP ĐỘ
ua = UserAgent()

def get_random_headers():
    """Tạo 'danh tính' trình duyệt giả để tránh bị nhận diện là Bot"""
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive"
    }

def human_sleep():
    """Mô phỏng thời gian nghỉ ngẫu nhiên của con người (1 đến 3 giây)"""
    sleep_time = random.uniform(1.0, 3.0)
    time.sleep(sleep_time)

# 3. LUỒNG CHẠY TỪ JSON PAYLOAD (CHÍNH XÁC TUYỆT ĐỐI)
def run_crawl_from_json():
    json_dir = "data_lake/json_payload"
    if not os.path.exists(json_dir):
        print(f"Không tìm thấy thư mục {json_dir}. Vui lòng chạy json_puller.py trước.")
        return
        
    json_files = ['VPL.json']
    print(f"=== TẢI DỮ LIỆU CHÍNH XÁC TỪ {len(json_files)} FILE JSON ===\n")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    # Duyệt từng file JSON của từng Ticker
    for filename in tqdm(json_files, desc="Đang quét JSON Payload"):
        ticker = filename[:-5] # VD: VTP.json -> VTP
        json_path = os.path.join(json_dir, filename)
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"\n[!] Lỗi đọc {filename}: {e}")
            continue
            
        # Bỏ qua nếu json trống
        if not data or not isinstance(data, list):
            continue
            
        for item in data:
            url = item.get('Url')
            title = str(item.get('Title', '')).strip()
            file_ext = str(item.get('FileExt', '')).strip().lower()
            
            if not url or not file_ext:
                continue
                
            # Trích xuất năm từ Title nhằm đưa về định dạng Ticker_BCTN_Year
            # VD title: "Báo cáo thường niên năm 2024 " -> 2024
            year_match = re.search(r'(20\d{2}|19\d{2})', title)
            BCTN_match = re.search(r'Báo cáo thường niên', title)
            if BCTN_match:
                BCTN = "BCTN"
            else:
                BCTN = "UNKNOWN"
            year = year_match.group(1) if year_match else "UNKNOWN"
            
            # Tên file cuối cùng: Ticker_BCTN_Year.pdf
            save_filename = f"{ticker}_{BCTN}_{year}{file_ext}"
            
            # Tạo thư mục theo ticker nếu cần
            ticker_dir = os.path.join(BRONZE_DIR, ticker)
            #Dựa theo code cũ, các file nằm chung ở BRONZE_DIR, nếu muốn để thư mục con thì uncomment
            os.makedirs(ticker_dir, exist_ok=True)
            save_path = os.path.join(ticker_dir, save_filename)
            
            # Để nguyên dạng cũ nằm chung 1 root:
            # save_path = os.path.join(BRONZE_DIR, save_filename)
            
            # Bỏ qua nếu đã tải rồi
            if os.path.exists(save_path):
                skip_count += 1
                continue
                
            # TẢI FILE THEO URL CHUẨN
            headers = get_random_headers()
            try:
                # Đổi HTTP sang HTTPS nêú source đưa chuẩn HTTP bị chặn
                if url.startswith("http://"):
                    url = url.replace("http://", "https://")
                    
                with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with open(save_path, 'wb') as f_out:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f_out.write(chunk)
                                
                success_count += 1
                human_sleep() # Nghỉ một nhịp sau khi tải thành công
            except Exception as e:
                print(f"\n[-] Lỗi tải file {url}: {e}")
                fail_count += 1

    print("\n\n=== KẾT QUẢ KÉO DỮ LIỆU TỪ CHÍNH XÁC URL ===")
    print(f"Tổng số file tải MỚI thành công: {success_count} file")
    print(f"Số file bỏ qua (đã tồn tại): {skip_count} file")
    print(f"Số file lỗi/không tải được: {fail_count} file")

if __name__ == "__main__":
    run_crawl_from_json()