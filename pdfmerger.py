import os
import re
import pymupdf  # Sử dụng tên alias mới của PyMuPDF (thay cho fitz)
from tqdm import tqdm

BRONZE_DIR = 'data_lake/bronze/VN100'

def run_pdf_merger():
    if not os.path.exists(BRONZE_DIR):
        print(f"Không tìm thấy thư mục: {BRONZE_DIR}")
        return
        
    # Dictionary nhóm các file có chung tiền tố chuẩn (Ticker_BCTN_Year)
    # Cấu trúc: { thư_mục_chứa: { base_name: [ (số_hậu_tố, filename), ... ] } }
    grouped_files = {}
    
    # Định dạng chuỗi regex bắt lấy tên file dạng: Ticker_BCTN_Year_hậuTố.pdf
    # Ví dụ: VNM_BCTN_2022_1.pdf, CTG_BCTN_2019_12.pdf
    pattern = re.compile(r'^([A-Za-z0-9]+_BCTN_\d{4})_(\d+)\.pdf$', re.IGNORECASE)
    
    # Quét toàn bộ thư mục tìm các file phần mảnh (có đánh số hậu tố)
    print("Đang quét tìm các cụm file có hậu tố định dạng...")
    for root, _, files in os.walk(BRONZE_DIR):
        for f in files:
            match = pattern.match(f)
            if match:
                base_name = match.group(1) # Lấy phần Ticker_BCTN_Year
                suffix = int(match.group(2)) # Lấy phần hậu tố: 1, 2, 3...
                
                if root not in grouped_files:
                    grouped_files[root] = {}
                
                if base_name not in grouped_files[root]:
                    grouped_files[root][base_name] = []
                    
                grouped_files[root][base_name].append((suffix, f))
                
    # Bắt đầu vòng lặp duyệt qua từ điển để merge
    merged_count = 0
    
    for root, base_dict in grouped_files.items():
        for base_name, files_info in base_dict.items():
            
            # Theo lệnh chỉ đạo: CHỈ MERGE KHI CÓ 3 FILE CÓ HẬU TỐ TRỞ LÊN
            if len(files_info) >= 3:
                print(f"\n[*] Phát hiện cụm {len(files_info)} file phần mảnh thuộc '{base_name}'. Tiến hành gộp...")
                
                # Quan trọng: Sort lại files_info theo hậu tố thứ tự từ bé đến lớn (ví dụ _1 rồi mới tới _2, _10)
                files_info.sort(key=lambda x: x[0])
                
                # Tên file xuất ra là dạng chuẩn, không có hậu tố
                target_filename = f"{base_name}.pdf"
                target_path = os.path.join(root, target_filename)
                
                merged_doc = pymupdf.open() # Tạo tài liệu PDF trống
                can_merge = True
                files_to_delete = []
                
                for suffix, filename in files_info:
                    part_path = os.path.join(root, filename)
                    try:
                        # Mở từng PDF rời và nối vào file PDF tổng
                        doc_part = pymupdf.open(part_path)
                        merged_doc.insert_pdf(doc_part)
                        doc_part.close()
                        
                        files_to_delete.append(part_path) # Mark để xóa sau cùng
                    except Exception as e:
                        print(f"  [-] Lỗi đọc file {part_path} khi merge: {e}")
                        can_merge = False
                        break
                        
                if can_merge:
                    try:
                        # Ghi/lưu file tổng ra đĩa
                        merged_doc.save(target_path)
                        merged_doc.close()
                        print(f"  -> Đã lưu file tổng thể thành công tại: {target_path}")
                        
                        # Xóa bỏ các mảnh cũ để dọn dẹp data lake
                        cleanup_count = 0
                        for path in files_to_delete:
                            os.remove(path)
                            cleanup_count += 1
                        print(f"  -> Đã dọn {cleanup_count} file rác hậu tố.")
                        merged_count += 1
                        
                    except Exception as e:
                        print(f"  [-] Lỗi lưu file gộp vào thư mục: {e}")
                        if not merged_doc.is_closed:
                            merged_doc.close()
                else:
                    print(f"  [-] Quá trình merge cho {base_name} bị hủy do lỗi đọc mảnh.")
                    if not merged_doc.is_closed:
                        merged_doc.close()

            # NẾU CÓ _1 MÀ KHÔNG CÓ _2... TỨC LÀ CHỈ CÒN ĐÚNG 1 TỆP LẺ LOI MANG HẬU TỐ
            elif len(files_info) == 1:
                suffix, filename = files_info[0]
                old_path = os.path.join(root, filename)
                new_filename = f"{base_name}.pdf"
                new_path = os.path.join(root, new_filename)
                
                print(f"\n[*] Phát hiện '{filename}' bị cô lập (không có các mảnh hậu tố khác). Tiến hành xoá hậu tố...")
                try:
                    if os.path.exists(new_path):
                        print(f"  -> File gốc '{new_filename}' đã tồn tại! Xoá luôn tệp mảnh lẻ '{filename}' này.")
                        os.remove(old_path)
                    else:
                        os.rename(old_path, new_path)
                        print(f"  -> Đã đổi tên chuẩn thành: {new_filename}")
                except Exception as e:
                    print(f"  [-] Lỗi đổi tên/xoá file '{filename}': {e}")

    print(f"\n=== HOÀN TẤT KIỂM KÊ: ĐÃ MERGE XONG {merged_count} BỘ TÀI LIỆU ===")

if __name__ == "__main__":
    run_pdf_merger()
