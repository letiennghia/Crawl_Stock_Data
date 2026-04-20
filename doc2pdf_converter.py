import os
from tqdm import tqdm
import win32com.client
import time

BRONZE_DIR = 'data_lake/bronze/VN100'

def convert_to_pdf():
    """
    Sử dụng Microsoft Word COM để mở các file .doc và .docx ngầm định 
    và SaveAs lại dưới dạng .pdf. Nhanh và giữ lại định dạng tốt nhất trên Windows.
    """
    if not os.path.exists(BRONZE_DIR):
        print(f"Không tìm thấy thư mục: {BRONZE_DIR}")
        return
        
    # Tìm tất cả file .doc và .docx
    doc_files = []
    for root, _, files in os.walk(BRONZE_DIR):
        for f in files:
            if f.lower().endswith(('.doc', '.docx')):
                doc_files.append(os.path.join(root, f))
                
    if not doc_files:
        print("Không tìm thấy file DOC/DOCX nào cần chuyển đổi.")
        return
        
    print(f"Tìm thấy {len(doc_files)} file DOC/DOCX. Khởi động MS Word COM...\n")
    
    try:
        # Khởi tạo Word thông qua COM
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        # Tắt mọi cảnh báo Popup/Macro để cho quá trình chạy không bị kẹt chèn giữa chừng
        word.DisplayAlerts = False
    except Exception as e:
        print(f"Không thể khởi chạy Word (Hệ thống yêu cầu cài sẵn Microsoft Word trên máy tính Windows). Lỗi: {e}")
        return

    converted_count = 0
    failed_count = 0

    for doc_path in tqdm(doc_files, desc="Đang chuyển sang PDF"):
        try:
            # Tạo đường dẫn PDF tuyệt đối để Win32Com đọc
            base_path, _ = os.path.splitext(doc_path)
            pdf_path = base_path + ".pdf"
            
            abs_doc = os.path.abspath(doc_path)
            abs_pdf = os.path.abspath(pdf_path)
            
            # Nếu PDF đã tồn tại thì bỏ qua chuyển đổi lại và xóa luôn file Doc cũ
            if os.path.exists(abs_pdf):
                try:
                    os.remove(abs_doc)
                    converted_count += 1
                except: pass
                continue
            
            # Mở file .doc/.docx dưới chế độ ReadOnly
            doc = word.Documents.Open(abs_doc, False, True, False)
            
            # Lưu ra file Format = 17 (wdFormatPDF)
            doc.SaveAs(abs_pdf, FileFormat=17)
            doc.Close(False)
            
            converted_count += 1
            
            # Xóa file Docx cũ rác
            try:
                os.remove(abs_doc)
            except Exception as e:
                print(f"\n  -> Đã chuyển đổi thành công nhưng không thể xoá file gốc '{doc_path}' do: {e}")
                
        except Exception as e:
            print(f"\n  [-] Lỗi chuyển đổi '{doc_path}': {e}")
            failed_count += 1
            
    try:
        word.Quit()
    except Exception:
        pass
        
    print(f"\n=== HOÀN TẤT CONVERT ===")
    print(f"Tổng số file Word đã phát hiện: {len(doc_files)}")
    print(f"Chuyển sang PDF thành công & xoá gốc rễ: {converted_count}")
    print(f"Lỗi chuyển đổi: {failed_count}")

if __name__ == "__main__":
    convert_to_pdf()
