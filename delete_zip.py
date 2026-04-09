import os
from tqdm import tqdm

# CẤU HÌNH ĐƯỜNG DẪN
BRONZE_DIR = 'data_lake/bronze/VN100'

def delete_zip_files():
    """
    Tìm và xoá các file .zip trong thư mục VN100 và các thư mục con
    """
    if not os.path.exists(BRONZE_DIR):
        print(f"Không tìm thấy thư mục: {BRONZE_DIR}")
        return
        
    compressed_files = []
    for root, _, files in os.walk(BRONZE_DIR):
        for f in files:
            if f.lower().endswith('.zip'):
                compressed_files.append(os.path.join(root, f))
            elif f.lower().endswith('.rar'):
                compressed_files.append(os.path.join(root, f))
                
    if not compressed_files:
        print("Không tìm thấy file nén nào cần xoá.")
        return
        
    print(f"Tìm thấy {len(compressed_files)} file nén. Bắt đầu xoá...\n")
    deleted_count = 0
    
    for compressed_path in tqdm(compressed_files, desc="Đang xoá file nén"):
        try:
            os.remove(compressed_path)
            deleted_count += 1
        except Exception as e:
            print(f" Lỗi khi xoá {compressed_path}: {e}")
            
    print("\n\n=== TỔNG KẾT ===")
    print(f"Tổng số file nén đã quét: {len(compressed_files)}")
    print(f"Số file nén xoá thành công: {deleted_count}")

if __name__ == "__main__":
    delete_zip_files()
