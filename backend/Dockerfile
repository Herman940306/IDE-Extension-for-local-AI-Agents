FROM python:3.13-slim@sha256:5b3b46fda94e5c9ef07f62b2c71c7a64c199930ec5b1b6ecf5f92ba37264c95a AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential \
	&& rm -rf /var/lib/apt/lists/*

FROM base AS builder

COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

COPY . .
RUN python -m compileall src

FROM python:3.13-slim@sha256:5b3b46fda94e5c9ef07f62b2c71c7a64c199930ec5b1b6ecf5f92ba37264c95a AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PATH="/home/auraai/.local/bin:$PATH"

RUN adduser --disabled-password --gecos "" auraai \
	&& mkdir -p /var/lib/auraia /var/log/auraia \
	&& chown -R auraai:auraai /var/lib/auraia /var/log/auraia

WORKDIR /app

COPY --from=builder /app /app
COPY --from=builder /root/.local /home/auraai/.local

USER auraai

EXPOSE 8001

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
