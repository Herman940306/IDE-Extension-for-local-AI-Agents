FROM python:3.11.9-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	PYTHONUTF8=1

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential curl \
	&& rm -rf /var/lib/apt/lists/*

FROM base AS builder

COPY requirements.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt

COPY . .
RUN python -m compileall src

FROM python:3.11.9-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONUTF8=1 \
	PATH="/home/auraai/.local/bin:$PATH"

RUN apt-get update \
	&& apt-get install -y --no-install-recommends git curl \
	&& rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos "" auraai \
	&& mkdir -p /var/lib/auraia /var/log/auraia /app/data /app/logs /app/cache \
	&& chown -R auraai:auraai /var/lib/auraia /var/log/auraia

WORKDIR /app

COPY --from=builder /app /app
COPY --from=builder /root/.local /home/auraai/.local

RUN chown -R auraai:auraai /app /home/auraai/.local

USER auraai

EXPOSE 8001

# Fast healthcheck using Prometheus metrics endpoint
HEALTHCHECK --interval=30s --timeout=5s --retries=5 CMD curl -fsS http://localhost:8001/metrics || exit 1

# Production command: Gunicorn with Uvicorn worker
CMD ["gunicorn", "src.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8001", "--workers", "2", "--timeout", "120"]
