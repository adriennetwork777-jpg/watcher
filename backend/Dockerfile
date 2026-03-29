# Builder stage
FROM python:3.11-slim-bookworm AS builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ default-libmysqlclient-dev libldap2-dev libsasl2-dev libssl-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY ./Watcher ./Watcher
COPY Watcher/manage.py .
COPY nltk_dependencies.py .

# Production stage
FROM python:3.11-slim-bookworm

WORKDIR /app/backend

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

RUN apt-get update && apt-get install -y --no-install-recommends default-libmysqlclient-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /app/Watcher ./Watcher
COPY --from=builder /app/manage.py .
COPY --from=builder /app/nltk_dependencies.py .

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=Watcher.settings \
    PYTHONPATH=/app/backend \
    NLTK_DATA=/home/appuser/nltk_data

RUN mkdir -p /app/backend/logs /home/appuser/nltk_data \
    && chown -R appuser:appgroup /app/backend /home/appuser/nltk_data \
    && chmod -R 755 /app/backend

USER appuser

# Download NLTK dependencies
RUN python nltk_dependencies.py

# Gunicorn command: logs go into writable folder
CMD ["gunicorn", "Watcher.wsgi:application", "--chdir=/app/backend", "-b", "0.0.0.0:9002", "--workers=3", "--threads=2",  "--worker-tmp-dir", "/tmp", "--access-logfile", "/app/backend/logs/access.log", "--error-logfile", "/app/backend/logs/error.log"]