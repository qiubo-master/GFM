# CICI AI Foundation

当前 O2DL 第一阶段已启用：`qwen3:8b`、`qwen3-embedding:0.6b`、YOLO11n、PP-OCRv5、`qwen3-vl:4b-instruct-q4_K_M` 和 Redis 持久化任务状态。

Qwen3-VL 使用官方 Qwen GGUF 的主模型与视觉投影文件，通过 `ops/Qwen3-VL.Modelfile` 导入独立视觉 Ollama（11435），不影响文本 Ollama（11434）。

面向智能客服、AI 运营数字人、AI 图像检测和 AI 保养方案的共享模型基座。

## 第一版能力

- Qwen3 8B 文本生成适配器。
- Qwen3 Embedding 0.6B 向量适配器。
- YOLO 通用检测适配器。
- PP-OCRv5 OCR 适配器。
- Qwen3-VL 图片理解适配器。
- YOLO + OCR + Qwen-VL 结构化视觉流水线。
- 图片安全校验、同步接口和异步任务接口。
- 按项目鉴权、统一请求 ID 和模型版本。

## 本地契约测试

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
FOUNDATION_MODE=mock .venv/bin/python -m pytest -q
```

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\pip.exe install -e ".[dev]"
$env:FOUNDATION_MODE="mock"
.\.venv\Scripts\python.exe -m pytest -q
```

## 服务器配置

```bash
cp .env.example .env
```

至少修改：

```dotenv
FOUNDATION_MODE=real
FOUNDATION_API_KEYS=customer-service:强随机密钥,digital-human:强随机密钥,image-inspection:强随机密钥,maintenance-plan:强随机密钥
FOUNDATION_DATA_DIR=/data
OLLAMA_BASE_URL=http://host.docker.internal:11434
VISION_OLLAMA_BASE_URL=http://host.docker.internal:11435
```

外部项目只能访问 AI Gateway，不应直接访问 Ollama、YOLO 或 OCR 内部端口。

## 接口

```text
POST /foundation/v1/text/chat
POST /foundation/v1/embeddings
POST /foundation/v1/images
GET  /foundation/v1/images/{image_id}
POST /foundation/v1/vision/detect
POST /foundation/v1/vision/ocr
POST /foundation/v1/vision/understand
POST /foundation/v1/vision/analyze
POST /foundation/v1/tasks
GET  /foundation/v1/tasks/{task_id}
GET  /foundation/v1/health
GET  /foundation/v1/models
```

当前异步任务存储在进程内，只用于第一阶段接口验证。正式多实例部署前应切换为 Redis 队列和 PostgreSQL 任务状态。
