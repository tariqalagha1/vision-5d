# Vision 5D — Production Dockerfile (multi-stage, optimized)
# Build: docker build -t vision5d:latest .
# Run API: docker run -p 8000:8000 vision5d:latest api
# Run Worker: docker run vision5d:latest worker

FROM python:3.12-slim AS base
LABEL org.opencontainers.image.title="Vision 5D"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.description="AI-Native Architectural SaaS Platform"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependencies layer ──
COPY pyproject.toml .
RUN pip install --no-cache-dir \
    fastapi>=0.115 uvicorn[standard]>=0.30 \
    pydantic>=2.0 sqlalchemy>=2.0 alembic>=1.13 \
    python-jose[cryptography]>=3.3 passlib[bcrypt]>=1.7 \
    python-multipart>=0.0.9 httpx>=0.27 aiofiles>=24.0 \
    structlog>=24.0 cryptography>=43.0 tenacity>=9.0 \
    numpy opencv-python prometheus-client>=0.21

# ── Application layer ──
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Entrypoints ──
COPY infrastructure/docker-entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint"]
CMD ["api"]
