# syntax=docker/dockerfile:1

# -- Builder stage: compile dependencies --------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# -- Runtime stage: minimal production image ------------------------------
FROM python:3.12-slim

# Metadata
LABEL org.opencontainers.image.title="Onshape Export Manager"
LABEL org.opencontainers.image.description="Automated Onshape CAD export orchestration"
LABEL org.opencontainers.image.source="https://github.com/your-org/onshape-export-manager"

# Install only runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged user
RUN useradd --create-home --shell /bin/bash oem

# Copy pre-installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
WORKDIR /app
COPY --chown=oem:oem . .

# Runtime directories as volumes
RUN mkdir -p /app/config /app/exports /app/database /app/logs /app/backups \
    && chown -R oem:oem /app

USER oem

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Default: web server in server mode (headless, binds 0.0.0.0)
ENV OEM_MODE=server
ENV OEM_HOST=0.0.0.0
ENV OEM_PORT=8000

ENTRYPOINT ["python", "app.py"]
