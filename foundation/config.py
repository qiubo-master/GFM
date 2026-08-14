from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    foundation_mode: str = "mock"
    foundation_api_keys: str = ""
    foundation_data_dir: Path = Path("./data")
    ollama_base_url: str = "http://127.0.0.1:11434"
    vision_ollama_base_url: str | None = None
    text_model: str = "qwen3:8b"
    embed_model: str = "qwen3-embedding:0.6b"
    vision_model: str = "qwen3-vl:4b-instruct-q4_K_M"
    yolo_model: str = "yolo11n.pt"
    max_image_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 12_000_000
    vision_concurrency: int = 1
    redis_url: str | None = None
    task_ttl_seconds: int = 86400
    database_url: str | None = None
    object_storage_endpoint: str | None = None
    forgeops_deploy_token: str = ""
    forgeops_deploy_script: Path = Path("/root/autodl-tmp/GFM/bootstrap/deploy-pull.sh")
    forgeops_deploy_status: Path = Path("/root/autodl-tmp/GFM/shared/deploy-status.json")

    @property
    def vision_base_url(self) -> str:
        return self.vision_ollama_base_url or self.ollama_base_url

    @property
    def api_keys(self) -> dict[str, str]:
        pairs = (item.strip() for item in self.foundation_api_keys.split(","))
        return dict(item.split(":", 1) for item in pairs if ":" in item)


@lru_cache
def get_settings() -> Settings:
    return Settings()
