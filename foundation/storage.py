from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from .config import Settings


IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


class ImageStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.foundation_data_dir / "images"

    def save(self, content: bytes, content_type: str) -> dict[str, object]:
        suffix = IMAGE_TYPES.get(content_type)
        if not suffix:
            raise HTTPException(415, "Only JPEG, PNG and WebP images are supported")
        if not content or len(content) > self.settings.max_image_bytes:
            raise HTTPException(413 if content else 400, "Invalid image size")
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
        except (UnidentifiedImageError, OSError):
            raise HTTPException(400, "Invalid image content") from None
        if width * height > self.settings.max_image_pixels:
            raise HTTPException(413, "Image pixel count exceeds the limit")
        image_id = f"img_{uuid.uuid4().hex}"
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{image_id}{suffix}"
        path.write_bytes(content)
        return {
            "image_id": image_id,
            "content_type": content_type,
            "size": len(content),
            "width": width,
            "height": height,
            "sha256": hashlib.sha256(content).hexdigest(),
            "url": f"/foundation/v1/images/{image_id}",
        }

    def resolve(self, image_id: str) -> Path:
        if not image_id.startswith("img_") or len(image_id) != 36:
            raise HTTPException(404, "Image not found")
        matches = list(self.root.glob(f"{image_id}.*")) if self.root.exists() else []
        if len(matches) != 1 or matches[0].suffix not in IMAGE_TYPES.values():
            raise HTTPException(404, "Image not found")
        return matches[0]

