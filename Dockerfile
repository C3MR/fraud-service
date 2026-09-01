# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir "fastapi[standard]" uvicorn pandas scikit-learn joblib \
    "pydantic>=2" pydantic-settings structlog

COPY src/ src/
RUN pip install --no-cache-dir --no-deps .

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 10001 appuser
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY models/fraud_xgb_v3.joblib /models/fraud_xgb_v3.joblib

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/v1/ready || exit 1

CMD ["uvicorn", "fraud_service.api.app:app", \
    "--host", "0.0.0.0", "--port", "8000"]