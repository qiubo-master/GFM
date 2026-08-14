from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse

from .auth import require_app
from .config import get_settings
from .ollama import OllamaService
from .schemas import EmbeddingRequest, TextChatRequest, VisionRequest
from .storage import ImageStore
from .tasks import TaskStore
from .vision import VisionPipeline


settings = get_settings()
app = FastAPI(title="CICI AI Foundation", version="0.1.0")
ollama = OllamaService(settings)
images = ImageStore(settings)
vision = VisionPipeline(settings, ollama)
tasks = TaskStore(settings.redis_url, settings.task_ttl_seconds)
WEB_ROOT = Path(__file__).resolve().parent / "web"


def envelope(data: Any, request_id: str, started: float, models: dict[str, str] | None = None):
    return {"request_id": request_id, "trace_id": f"tr_{uuid.uuid4().hex[:16]}", "data": data,
            "error": None, "model_versions": models or {},
            "timings_ms": {"total": round((time.perf_counter() - started) * 1000, 2)}}


@app.get("/", include_in_schema=False)
async def console():
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/foundation/v1/health")
async def health():
    ollama_ok = False
    models = []
    if settings.foundation_mode != "mock":
        try:
            models = await ollama.tags()
            ollama_ok = True
        except Exception:
            pass
    return {"status": "ok", "mode": settings.foundation_mode, "ollama": ollama_ok,
            "models": [item.get("name") for item in models],
            "capabilities": ["text", "embeddings", "detect", "ocr", "vision_language", "vision_analysis"]}


@app.get("/foundation/v1/models", dependencies=[Depends(require_app)])
async def models():
    return {"text": settings.text_model, "embedding": settings.embed_model,
            "vision": settings.vision_model, "detector": settings.yolo_model, "ocr": "pp-ocrv5"}


@app.post("/foundation/v1/text/chat")
async def text_chat(body: TextChatRequest, app_id: str = Depends(require_app)):
    started, request_id = time.perf_counter(), f"req_{uuid.uuid4().hex[:16]}"
    result = await ollama.chat([x.model_dump() for x in body.messages], body.model, body.response_schema, body.options)
    return envelope({**result, "app_id": app_id}, request_id, started, {"text": result["model"]})


@app.post("/foundation/v1/embeddings")
async def embeddings(body: EmbeddingRequest, app_id: str = Depends(require_app)):
    started, request_id = time.perf_counter(), f"req_{uuid.uuid4().hex[:16]}"
    result = await ollama.embeddings(body.input, body.model)
    return envelope({**result, "app_id": app_id}, request_id, started,
                    {"embedding": result.get("model", body.model or settings.embed_model)})


@app.post("/foundation/v1/images", status_code=201)
async def upload_image(request: Request, content_type: str | None = Header(default=None),
                       app_id: str = Depends(require_app)):
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > settings.max_image_bytes:
            raise HTTPException(413, "Image exceeds size limit")
    return {**images.save(bytes(content), (content_type or "").split(";", 1)[0].lower()), "app_id": app_id}


@app.get("/foundation/v1/images/{image_id}", dependencies=[Depends(require_app)])
async def get_image(image_id: str):
    return FileResponse(images.resolve(image_id))


@app.post("/foundation/v1/vision/detect")
async def detect(body: VisionRequest, app_id: str = Depends(require_app)):
    result = await vision.yolo.detect(images.resolve(body.image_id))
    return {"app_id": app_id, "image_id": body.image_id, "detections": [x.model_dump() for x in result]}


@app.post("/foundation/v1/vision/ocr")
async def ocr(body: VisionRequest, app_id: str = Depends(require_app)):
    result = await vision.ocr.recognize(images.resolve(body.image_id))
    return {"app_id": app_id, "image_id": body.image_id, "blocks": [x.model_dump() for x in result]}


@app.post("/foundation/v1/vision/understand")
async def understand(body: VisionRequest, app_id: str = Depends(require_app)):
    result = await ollama.understand_image(images.resolve(body.image_id), body.question, {"scene": body.scene})
    return {"app_id": app_id, "image_id": body.image_id, "result": result}


@app.post("/foundation/v1/vision/analyze")
async def analyze(body: VisionRequest, app_id: str = Depends(require_app)):
    result = await vision.analyze(images.resolve(body.image_id), body.scene, body.question)
    return {"app_id": app_id, "data": result.model_dump()}


@app.post("/foundation/v1/tasks", status_code=202)
async def create_task(body: VisionRequest, app_id: str = Depends(require_app)):
    image = images.resolve(body.image_id)
    item = await tasks.create(app_id, lambda: vision.analyze(image, body.scene, body.question))
    return {"task_id": item["task_id"], "status": item["status"]}


@app.get("/foundation/v1/tasks/{task_id}")
async def get_task(task_id: str, app_id: str = Depends(require_app)):
    item = await tasks.get(task_id, app_id)
    if not item:
        raise HTTPException(404, "Task not found")
    result = item.get("result")
    return {**item, "result": result.model_dump() if hasattr(result, "model_dump") else result}
