# === Backend API — FastAPI server with bundled AI service ===
# Builds in one stage: copies both nyaai-ai and nyaai-backend code.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY nyaai-backend/requirements.txt /app/nyaai-backend/requirements.txt
RUN pip install --no-cache-dir -r /app/nyaai-backend/requirements.txt

# Install AI service dependencies
COPY nyaai-ai/requirements.txt /app/nyaai-ai/requirements.txt
RUN pip install --no-cache-dir -r /app/nyaai-ai/requirements.txt

# Pre-download embedding model during build
COPY nyaai-ai/setup.py /app/setup.py
RUN python /app/setup.py

# Copy application code
COPY nyaai-ai/src/ /app/nyaai-ai/src/
COPY nyaai-backend/src/ /app/nyaai-backend/src/

ENV PYTHONPATH=/app/nyaai-ai/src:/app/nyaai-backend/src
ENV HF_HOME=/root/.cache/huggingface

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
