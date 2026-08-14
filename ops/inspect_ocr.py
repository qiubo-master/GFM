from __future__ import annotations

import sys

from paddleocr import PaddleOCR


engine = PaddleOCR(
    lang="ch",
    device="cpu",
    enable_mkldnn=False,
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
)
results = list(engine.predict(sys.argv[1]))
print("result-count", len(results))
for result in results:
    print("type", type(result).__name__)
    print("json-type", type(result.json).__name__)
    print(result.json)
