from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from .config import Settings


class OllamaService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def tags(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{self.settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])

    async def chat(self, messages: list[dict[str, str]], model: str | None = None,
                   response_schema: dict[str, Any] | None = None,
                   options: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.settings.foundation_mode == "mock":
            return {"model": model or self.settings.text_model, "content": "mock text response"}
        payload: dict[str, Any] = {
            "model": model or self.settings.text_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.1, "num_ctx": 4096, **(options or {})},
        }
        if response_schema:
            payload["format"] = response_schema
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(f"{self.settings.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        return {"model": data.get("model", payload["model"]), "content": data["message"]["content"]}

    async def embeddings(self, values: list[str], model: str | None = None) -> dict[str, Any]:
        if self.settings.foundation_mode == "mock":
            return {"model": model or self.settings.embed_model, "embeddings": [[0.0] * 8 for _ in values]}
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/embed",
                json={"model": model or self.settings.embed_model, "input": values},
            )
            response.raise_for_status()
            return response.json()

    async def understand_image(self, image: Path, question: str,
                               context: dict[str, Any]) -> dict[str, Any]:
        if self.settings.foundation_mode == "mock":
            return {"summary": "mock visual analysis", "findings": [], "uncertainties": ["mock mode"]}
        prompt = (
            "你是通用视觉分析服务。结合图片、目标检测和OCR结果回答问题。"
            "只输出JSON，字段为summary、findings、uncertainties。"
            f"\n问题：{question}\n已有证据：{json.dumps(context, ensure_ascii=False)}"
        )
        payload = {
            "model": self.settings.vision_model,
            "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(image.read_bytes()).decode()]}],
            "format": "json",
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 800},
        }
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(f"{self.settings.vision_base_url}/api/chat", json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
        return json.loads(content)
