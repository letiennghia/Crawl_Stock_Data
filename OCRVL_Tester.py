from paddleocr import PaddleOCRVL
import json
ocr = PaddleOCRVL()
output = ocr.predict(input="./data_lake/silver/VN100/ACB/ACB_BCTN_2021.pdf")
page_res=list(output)
output = ocr.restructure_pages(page_res)
for res in output:
    res.print()
    #res.save_to_json(save_path="output_VL")
    res.save_to_markdown(save_path="output_VL")
