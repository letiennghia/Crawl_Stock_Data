#take one pdf from data_lake, split it into 32 pages per file, then save as test_1 to test_n in .pdf format
import os
import tqdm
from PyPDF2 import PdfReader, PdfWriter
# Cấu hình đường dẫn và số trang mỗi file
PDF_PATH = "./data_lake/silver/VN100/ACB/ACB_BCTN_2021.pdf"
OUTPUT_DIR = "./test_split" 
PAGES_PER_FILE = 32
# Tạo thư mục đầu ra nếu chưa tồn tại
os.makedirs(OUTPUT_DIR, exist_ok=True)
# Đọc file PDF gốc
reader = PdfReader(PDF_PATH)
total_pages = len(reader.pages)
print(f"Tổng số trang trong PDF: {total_pages}")
# Vòng lặp để chia PDF thành các file nhỏ
for start_page in range(0, total_pages, PAGES_PER_FILE):
    end_page = min(start_page + PAGES_PER_FILE, total_pages)
    writer = PdfWriter()
    
    # Thêm các trang vào file mới
    for page_num in range(start_page, end_page):
        writer.add_page(reader.pages[page_num])
    
    # Lưu file mới
    output_path = os.path.join(OUTPUT_DIR, f"test_{start_page // PAGES_PER_FILE + 1}.pdf")
    with open(output_path, "wb") as output_file:
        writer.write(output_file)
    
    print(f"Đã tạo file: {output_path} chứa trang {start_page + 1} đến {end_page}") 