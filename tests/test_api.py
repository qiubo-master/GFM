import io
import time

from fastapi.testclient import TestClient
from PIL import Image

from foundation.main import app


client = TestClient(app)


def image_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (64, 48), "white").save(output, format="PNG")
    return output.getvalue()


def upload() -> str:
    response = client.post("/foundation/v1/images", content=image_bytes(), headers={"Content-Type": "image/png"})
    assert response.status_code == 201
    return response.json()["image_id"]


def test_health_and_models():
    assert client.get("/foundation/v1/health").json()["status"] == "ok"
    assert client.get("/foundation/v1/models").json()["text"] == "qwen3:8b"
    from foundation.config import get_settings
    assert get_settings().vision_base_url.endswith("11434")


def test_console_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "GFM" in response.text
    assert "视觉大模型" in response.text


def test_text_and_embedding_contracts():
    chat = client.post("/foundation/v1/text/chat", json={"messages": [{"role": "user", "content": "你好"}]})
    assert chat.status_code == 200
    assert chat.json()["data"]["content"] == "mock text response"
    embedding = client.post("/foundation/v1/embeddings", json={"input": ["轮胎鼓包"]})
    assert len(embedding.json()["data"]["embeddings"][0]) == 8


def test_image_and_vision_contracts():
    image_id = upload()
    body = {"image_id": image_id, "scene": "tire_inspection", "question": "检查轮胎"}
    assert client.post("/foundation/v1/vision/detect", json=body).json()["detections"][0]["label"] == "tire"
    assert client.post("/foundation/v1/vision/ocr", json=body).json()["blocks"] == []
    result = client.post("/foundation/v1/vision/analyze", json=body)
    assert result.status_code == 200
    assert result.json()["data"]["status"] == "completed"


def test_async_task():
    image_id = upload()
    response = client.post("/foundation/v1/tasks", json={"image_id": image_id, "scene": "general"})
    assert response.status_code == 202
    task_id = response.json()["task_id"]
    for _ in range(20):
        task = client.get(f"/foundation/v1/tasks/{task_id}").json()
        if task["status"] == "completed":
            break
        time.sleep(0.01)
    assert task["status"] == "completed"


def test_invalid_image_rejected():
    response = client.post("/foundation/v1/images", content=b"not-image", headers={"Content-Type": "image/png"})
    assert response.status_code == 400
