from __future__ import annotations

import sys
from pathlib import Path

from ultralytics import YOLO


model_path = Path(sys.argv[1]).resolve()
image_path = Path(sys.argv[2]).resolve()
model = YOLO(str(model_path))
results = model.predict(str(image_path), verbose=False, device=0)
print(f"yolo-ok results={len(results)} detections={len(results[0].boxes)} model={model_path}")
