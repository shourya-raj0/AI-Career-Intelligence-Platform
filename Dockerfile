# Career Intelligence Platform — single-container deployment.
#
# The Streamlit frontend imports the backend Python APIs directly (no separate
# HTTP service yet), so one image runs the whole product. The embedding model
# downloads on first use at cold start (~90 MB) — expect a slower first boot.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

WORKDIR /app

# CPU-only torch (avoids the multi-GB CUDA wheel).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt backend/requirements.txt
COPY frontend/requirements.txt frontend/requirements.txt
RUN pip install --no-cache-dir \
        -r backend/requirements.txt \
        -r frontend/requirements.txt

# Application code (backend + frontend in one tree so the frontend's
# relative import of the backend package resolves).
COPY backend/ backend/
COPY frontend/ frontend/

# Run as a non-root user; the runtime also writes jobs.db / model cache here.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

CMD ["streamlit", "run", "frontend/app.py"]
