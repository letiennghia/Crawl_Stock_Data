from paddleocr import PaddleOCR  

ocr = PaddleOCR(
    lang ="vi",
    device="gpu"
      # Disables text line orientation classification model via this parameter
)
# ocr = PaddleOCR(lang="en") # Uses English model by specifying language parameter
# ocr = PaddleOCR(ocr_version="PP-OCRv4") # Uses other PP-OCR versions via version parameter
# ocr = PaddleOCR(device="gpu") # Enables GPU acceleration for model inference via device parameter
# ocr = PaddleOCR(
#     text_detection_model_name="PP-OCRv5_mobile_det",
#     text_recognition_model_name="PP-OCRv5_mobile_rec",
#     use_doc_orientation_classify=False,
#     use_doc_unwarping=False,
#     use_textline_orientation=False,
# ) # Switch to PP-OCRv5_mobile models
result = ocr.predict("./data_lake/silver/VN100/ACB/ACB_BCTN_2021.pdf")  
for res in result:  
    res.print()  
    try:
        res.save_to_markdown(save_path="output2")
    except Exception as e:
        print(f"Error saving markdown: {e}")
        pass
    res.save_to_json("output2")