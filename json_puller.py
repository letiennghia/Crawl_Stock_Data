import asyncio
import nest_asyncio
import json
import os
import pandas as pd
from playwright.async_api import async_playwright

nest_asyncio.apply()

LAKE_ROOT = 'data_lake/json_payload'
os.makedirs(LAKE_ROOT, exist_ok=True)

async def hit_and_run_packet(target_url, ticker):
    if os.path.exists(os.path.join(LAKE_ROOT, f"{ticker}.json")):
        print(f"[{ticker}] 💾 Đã có dữ liệu, bỏ qua")
        return
    # ĐỊNH VỊ CHÍNH XÁC URL CẦN BẮT
    target_api = "https://finance.vietstock.vn/data/getdocument"
    
    print(f"\n[{ticker}] 🕵️ Khởi động chiến thuật Hit & Run...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 1. THIẾT LẬP BẪY (Chỉ cần bẫy đúng API này)
            async with page.expect_response(
                lambda response: target_api == response.url.lower() and response.status == 200,
                timeout=15000 # Chờ API tối đa 15s
            ) as response_info:
                
                # 2. ÉP TRANG TẢI NHƯNG KHÔNG CHỜ ĐỢI
                try:
                    # wait_until="commit": Chỉ cần nhận được tín hiệu web phản hồi là ngắt chờ ngay
                    # Không cần chờ quảng cáo hay DOM load xong
                    await page.goto(target_url, wait_until="commit", timeout=10000)
                except Exception as goto_err:
                    # Cố tình nuốt cái lỗi Timeout của giao diện, vì ta KHÔNG QUAN TÂM giao diện
                    pass 
                    
            # 3. THU HOẠCH NGAY LẬP TỨC
            packet = await response_info.value
            print(f"[{ticker}] ✅ Đã ôm gọn gói tin: {packet.url}")
            
            # Mổ dữ liệu
            data = await packet.json()
            
            output_file = os.path.join(LAKE_ROOT, f"{ticker}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            print(f"[{ticker}] 💾 ĐÃ LƯU THÀNH CÔNG: {output_file}")
            
            print("-" * 50)
            print("🔍 MỞ FILE BÊN TRÊN TRONG DRIVE ĐỂ XEM DANH SÁCH URL BÁO CÁO!")
            print("-" * 50)
            
            return data
            
        except Exception as e:
            print(f"[{ticker}] ❌ Lỗi thật sự khi bắt packet: {str(e)}")
            return None
            
        finally:
            await browser.close()

# ==========================================
# KHỞI CHẠY
# ==========================================
async def main():
    #chạy toàn bộ trong vn100.csv
    df = pd.read_csv('vn100.csv')
    for index, row in df.iterrows():
        ticker = row['symbol']
        url = f"https://finance.vietstock.vn/{ticker}/tai-tai-lieu.htm?doctype=2"
        await hit_and_run_packet(url, ticker)
    # test_ticker = "GEE"
    # # Dùng URL từ ảnh của đồng nghiệp
    # test_url = f"https://finance.vietstock.vn/{test_ticker}/tai-tai-lieu.htm?doctype=2"
    
    # await hit_and_run_packet(test_url, test_ticker)

if __name__ == "__main__":
    asyncio.run(main())