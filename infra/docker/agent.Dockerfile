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

# Seed the agent-work volume with the initial workspace scaffold.
# Docker initializes a named volume from image content on first creation (empty volume only).
# Subsequent lifetimes are reset by the graveyard lifecycle reset (step 10).
RUN mkdir -p runtime/agent-work/journal \
             runtime/agent-work/knowledge \
             runtime/agent-work/observations \
             runtime/agent-work/lineage && \
    cp config/workspace_scaffold/WORKSPACE.md runtime/agent-work/WORKSPACE.md

ENTRYPOINT ["lambertian-agent"]
