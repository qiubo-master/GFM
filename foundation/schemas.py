from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class TextChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=50)
    model: str | None = None
    stream: bool = False
    response_schema: dict[str, Any] | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class EmbeddingRequest(BaseModel):
    input: list[str] = Field(min_length=1, max_length=64)
    model: str | None = None


class VisionRequest(BaseModel):
    image_id: str
    scene: str = Field(default="general", max_length=80)
    question: str = Field(default="请分析图片", max_length=2000)
    response_schema: str | dict[str, Any] | None = None


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Detection(BaseModel):
    id: str
    label: str
    confidence: float = Field(ge=0, le=1)
    bbox: BoundingBox


class OCRBlock(BaseModel):
    id: str
    text: str
    confidence: float = Field(ge=0, le=1)
    polygon: list[list[float]]


class Finding(BaseModel):
    code: str
    name: str
    severity: Literal["info", "low", "medium", "high", "critical"] = "info"
    confidence: float = Field(ge=0, le=1)
    evidence: list[dict[str, str]] = Field(default_factory=list)
    region: BoundingBox | None = None


class VisualAnalysisResult(BaseModel):
    schema_version: str = "1.0"
    analysis_id: str
    status: Literal["completed", "partial", "failed"]
    scene: str
    summary: str
    objects: list[Detection] = Field(default_factory=list)
    texts: list[OCRBlock] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    model_versions: dict[str, str] = Field(default_factory=dict)
    timings_ms: dict[str, float] = Field(default_factory=dict)

