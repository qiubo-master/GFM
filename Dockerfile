FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY foundation ./foundation
RUN pip install --no-cache-dir .
EXPOSE 6010
CMD ["uvicorn", "foundation.main:app", "--host", "0.0.0.0", "--port", "6010"]

