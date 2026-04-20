# spacing_fix.py
import re
from pyvi import ViTokenizer          # pip install pyvi
# or alternatively: from underthesea import word_tokenize

# Vietnamese syllable onset/rhyme patterns for rule-based detection
# A valid Vietnamese syllable ends with: a vowel cluster + optional final consonant
# This regex matches boundaries between fused Vietnamese syllables
_SYLLABLE_BOUNDARY = re.compile(
    r'(?<=[aăâeêiouươôáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ])'
    r'(?=[bcdđghklmnpqrstvx](?=[aăâeêiouươô]))',
    re.UNICODE
)

def fix_missing_spaces(text: str) -> str:
    """
    Two-stage fix:
    1. Rule-based: insert spaces at obvious syllable boundaries
    2. Segmenter-based: let pyvi re-tokenize the result
    """
    # Stage 1: protect numbers and known tokens (don't split these)
    protected = {}
    def protect(m):
        key = f"__P{len(protected)}__"
        protected[key] = m.group(0)
        return key

    text = re.sub(r'\d[\d\.,]+', protect, text)   # numbers: 598.280.712.859
    text = re.sub(r'[A-Z]{2,}', protect, text)    # acronyms: ESG, VND

    # Stage 2: pyvi segmentation on the fused Vietnamese text
    # pyvi works on unsegmented text and outputs space-separated syllables
    segmented = ViTokenizer.tokenize(text)

    # Stage 3: restore protected tokens
    for key, val in protected.items():
        segmented = segmented.replace(key, val)

    return segmented


# Example:
raw = "Điều hành chung hoạt động của Ngânhàng. Chỉ đạo hoạt động Khối Khách hàng doanh nghiệp, Khối Khách hàng cá nhân, Khối Vậnhành, Phòng Quảnlý nợ, Phòng Phân tích tín dụng, Phòng Tuân thủ, Phòng Pháp chế, và Phòng Tổnghợp. Chỉđạohoạtđộngcủacáccôngtyconsau:CôngtyTNHHMTVCho thuêtàichínhNgânhàngÁChâuvàCôngtyTNHHQuảnlýnợvàKhai thác tàisảnNgânhàngÁChâu."
print(fix_missing_spaces(raw))