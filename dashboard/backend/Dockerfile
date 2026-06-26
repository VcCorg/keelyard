# Production image for the Agentic Dashboard backend (FastAPI).
#
# IMPORTANT: build with the repository ROOT as the build context, because the
# backend depends on the local `agentic-cli` package:
#
#   docker build -f dashboard/backend/Dockerfile -t agentic-dashboard-backend .
#
# (The provided dashboard/docker-compose.prod.yml already sets this context.)

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Minimal system deps (git is used by some CLI onboarding flows)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the local agentic-cli first (satisfies the `agentic-cli` dependency),
# then the dashboard backend. Copy only what each step needs for better caching.
COPY agentic-cli/ /app/agentic-cli/
RUN pip install /app/agentic-cli

COPY dashboard/backend/ /app/dashboard/backend/
RUN pip install /app/dashboard/backend

WORKDIR /app/dashboard/backend

EXPOSE 8000

# Lightweight health endpoint exposed by the API.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
