FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Pre-compile to avoid __pycache__ writes at runtime under read_only root.
RUN python -m compileall -q src/

COPY config/ ./config/

ENTRYPOINT ["lambertian-agent"]
