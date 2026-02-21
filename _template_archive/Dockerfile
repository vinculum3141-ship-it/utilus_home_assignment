# Multi-stage Dockerfile for Energy Platform

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir .

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser pyproject.toml ./

# Install the package in editable mode
USER root
RUN pip install -e .
USER appuser

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV EXECUTION_MODE=local
ENV PROCESSING_MODE=batch
ENV LOG_LEVEL=INFO

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command: run API server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
