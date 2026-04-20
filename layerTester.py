import os
import gc
import json
import cv2
import numpy as np
from pdf2image import convert_from_path, pdfinfo_from_path
from doclayout_yolo import YOLOv10

# ========================================================
# CẤU HÌNH HỆ THỐNG
# ========================================================
PDF_PATH = "./data_lake/silver/VN100/ACB/ACB_BCTN_2021.pdf"   # Đường dẫn PDF
MODEL_PATH = "yolov10-doclayout.pt"       # Đường dẫn mô hình YOLOv10
OUTPUT_DIR = "./output_layout"            # Thư mục lưu ảnh kiểm tra
JSON_OUTPUT = "master_layout.json"        # File JSON tổng hợp
CHUNK_SIZE = 10                           # CỬA SỔ TRƯỢT: Số trang nạp vào RAM mỗi mẻ
DPI = 300                                 # Độ nét để chống mất dấu Tiếng Việt

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("🚀 Đang khởi động Động cơ DocLayout-YOLOv10...")
    model = YOLOv10(MODEL_PATH)
    
    # 1. Trinh sát PDF: Lấy tổng số trang mà KHÔNG cần tải PDF vào RAM
    try:
        info = pdfinfo_from_path(PDF_PATH)
        total_pages = info["Pages"]
        print(f"📄 Đã quét PDF: Tổng cộng {total_pages} trang.")
    except Exception as e:
        print(f"❌ Lỗi đọc PDF: Đảm bảo bạn đã cài poppler-utils. Lỗi: {e}")
        return

    # Khởi tạo cấu trúc JSON Tổng (Master JSON)
    master_data = {
        "metadata": {
            "source_file": PDF_PATH,
            "total_pages": total_pages,
            "dpi_used": DPI
        },
        "pages": []
    }

    # ========================================================
    # 2. VÒNG LẶP CỬA SỔ TRƯỢT (SLIDING WINDOW)
    # ========================================================
    for start_page in range(1, total_pages + 1, CHUNK_SIZE):
        end_page = min(start_page + CHUNK_SIZE - 1, total_pages)
        print(f"\n🌊 [CỬA SỔ TRƯỢT] Đang nạp mẻ trang {start_page} đến {end_page} vào RAM...")
        
        # Bóc tách 1 mẻ PDF thành ảnh PIL (Giữ lại RAM)
        chunk_images = convert_from_path(
            PDF_PATH, 
            dpi=DPI, 
            first_page=start_page, 
            last_page=end_page
        )
        
        # 3. XỬ LÝ TỪNG TRANG TRONG MẺ
        for i, pil_img in enumerate(chunk_images):
            current_page_num = start_page + i
            print(f"   👉 Đang trích xuất Bố cục trang {current_page_num}...")
            
            # YOLOv10 hỗ trợ nạp thẳng ảnh PIL, cực kỳ tiện lợi
            results = model.predict(
                pil_img, 
                imgsz=1024, 
                conf=0.25,      # Lọc nhiễu, chỉ lấy box có độ tin cậy > 25%
                verbose=False,  # Tắt log thừa của Ultralytics
                device="cuda:0" # Đổi thành 'cpu' nếu chạy máy thường
            )
            result = results[0]

            # --- 3.1: Ghi nhận dữ liệu vào JSON ---
            page_data = {
                "page_number": current_page_num,
                "image_width": result.orig_shape[1],
                "image_height": result.orig_shape[0],
                "elements": []
            }
            
            for box in result.boxes:
                coords = box.xyxy[0].tolist()
                page_data["elements"].append({
                    "type": model.names[int(box.cls[0])],
                    "confidence": round(float(box.conf[0]), 4),
                    "bbox": [round(c, 2) for c in coords]
                })
            
            master_data["pages"].append(page_data)

            # --- 3.2: Lưu ảnh trực quan (Cho con người kiểm tra) ---
            # result.plot() trả về numpy array hệ BGR, dùng cv2.imwrite là hoàn hảo
            annotated_img = result.plot(pil=True, line_width=4, font_size=18)
            img_save_path = os.path.join(OUTPUT_DIR, f"page_{current_page_num:03d}.jpg")
            cv2.imwrite(img_save_path, annotated_img)
            
            # Xóa ảnh PIL đơn lẻ khỏi RAM ngay khi xử lý xong
            del pil_img 

        # ========================================================
        # 4. GIAI ĐOẠN XẢ RÁC BỘ NHỚ (CRITICAL STEP)
        # ========================================================
        # Xóa toàn bộ mẻ ảnh vừa convert khỏi RAM
        del chunk_images
        # Ép Python dọn dẹp rác bộ nhớ ngay lập tức
        gc.collect() 
        print(f"🧹 Đã xả RAM cho mẻ {start_page}-{end_page}.")

    # ========================================================
    # 5. XUẤT MASTER JSON ĐẦU CUỐI
    # ========================================================
    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=4)
        
    print(f"\n🎉 HOÀN TẤT CHIẾN DỊCH!")
    print(f"📊 Dữ liệu cấu trúc được gộp tại: {JSON_OUTPUT}")
    print(f"🖼️ Ảnh kiểm tra được lưu trong: {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()