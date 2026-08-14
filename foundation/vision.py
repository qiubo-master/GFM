from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from .config import Settings
from .ollama import OllamaService
from .schemas import BoundingBox, Detection, Finding, OCRBlock, VisualAnalysisResult


class YoloAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._model = None

    def _load(self):
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(self.settings.yolo_model)
        return self._model

    async def detect(self, image: Path) -> list[Detection]:
        if self.settings.foundation_mode == "mock":
            with Image.open(image) as item:
                width, height = item.size
            return [Detection(id="det_001", label="tire", confidence=0.9,
                              bbox=BoundingBox(x1=0, y1=0, x2=width, y2=height))]
        results = await asyncio.to_thread(self._load().predict, str(image), verbose=False)
        detections: list[Detection] = []
        for result in results:
            for index, box in enumerate(result.boxes):
                xyxy = box.xyxy[0].tolist()
                class_id = int(box.cls[0])
                detections.append(Detection(
                    id=f"det_{index + 1:03d}", label=result.names[class_id],
                    confidence=float(box.conf[0]),
                    bbox=BoundingBox(x1=xyxy[0], y1=xyxy[1], x2=xyxy[2], y2=xyxy[3]),
                ))
        return detections


class OCRAdapter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._engine = None

    def _load(self):
        if self._engine is None:
            from paddleocr import PaddleOCR
            self._engine = PaddleOCR(
                lang="ch",
                device="cpu",
                enable_mkldnn=False,
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )
        return self._engine

    async def recognize(self, image: Path) -> list[OCRBlock]:
        if self.settings.foundation_mode == "mock":
            return []
        results = await asyncio.to_thread(self._load().predict, str(image))
        blocks: list[OCRBlock] = []
        for result in results:
            data = result.json if hasattr(result, "json") else result
            payload = data.get("res", data) if isinstance(data, dict) else {}
            texts = payload.get("rec_texts", [])
            scores = payload.get("rec_scores", [])
            polygons = payload.get("rec_polys", [])
            for index, text in enumerate(texts):
                polygon = polygons[index].tolist() if hasattr(polygons[index], "tolist") else polygons[index]
                blocks.append(OCRBlock(id=f"ocr_{len(blocks) + 1:03d}", text=text,
                                       confidence=float(scores[index]), polygon=polygon))
        return blocks


class VisionPipeline:
    def __init__(self, settings: Settings, ollama: OllamaService):
        self.settings = settings
        self.yolo = YoloAdapter(settings)
        self.ocr = OCRAdapter(settings)
        self.ollama = ollama
        self.semaphore = asyncio.Semaphore(settings.vision_concurrency)

    async def analyze(self, image: Path, scene: str, question: str) -> VisualAnalysisResult:
        async with self.semaphore:
            started = time.perf_counter()
            basic_started = time.perf_counter()
            objects, texts = await asyncio.gather(self.yolo.detect(image), self.ocr.recognize(image))
            basic_ms = (time.perf_counter() - basic_started) * 1000
            vl_started = time.perf_counter()
            vision = await self.ollama.understand_image(
                image, question,
                {"scene": scene, "objects": [x.model_dump() for x in objects], "texts": [x.model_dump() for x in texts]},
            )
            vl_ms = (time.perf_counter() - vl_started) * 1000
            findings = []
            for index, item in enumerate(vision.get("findings", [])):
                try:
                    findings.append(Finding.model_validate(item))
                except Exception:
                    findings.append(Finding(code=f"vision.finding.{index + 1}", name=str(item), confidence=0.5))
            return VisualAnalysisResult(
                analysis_id=f"va_{uuid.uuid4().hex}", status="completed", scene=scene,
                summary=str(vision.get("summary", "视觉分析完成")), objects=objects, texts=texts,
                findings=findings, uncertainties=[str(x) for x in vision.get("uncertainties", [])],
                model_versions={"detector": self.settings.yolo_model, "ocr": "pp-ocrv5",
                                "vision_language": self.settings.vision_model},
                timings_ms={"detection_and_ocr": round(basic_ms, 2), "qwen_vl": round(vl_ms, 2),
                            "total": round((time.perf_counter() - started) * 1000, 2)},
            )
