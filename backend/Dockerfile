# Backend Dockerfile - Production Optimized
ARG PYTHON_VERSION=3.11
ARG DEBIAN_SUITE=bookworm

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_SUITE} AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_SUITE}

# Security: Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app/backend

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY Watcher ./Watcher
COPY static ./static
COPY manage.py .
COPY nltk_dependencies.py .

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=Watcher.settings

# Download NLTK dependencies
RUN python nltk_dependencies.py

# Create necessary directories and set permissions
RUN mkdir -p /app/backend/logs /app/backend/static \
    && chown -R appuser:appgroup /app/backend \
    && chmod -R 755 /app/backend

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 9002

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9002/api/health/ || exit 1

# Run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:9002"]
