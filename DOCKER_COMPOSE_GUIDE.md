# 🐳 Watcher - Docker Compose Guide

## 📋 Overview

This Docker Compose configuration provides a **production-ready stack** for Watcher with:

- **Traefik** as reverse proxy with automatic SSL/TLS
- **CertStream** for real-time certificate transparency monitoring
- **SearXNG** as privacy-respecting search engine
- **MySQL 8.0** database optimized for Watcher
- **Watcher** application built locally from source

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Ensure you have Docker and Docker Compose installed
docker --version
docker compose version
```

### 2. Configuration

```bash
# Copy the environment template
cp .env.example .env

# Edit the .env file with your settings
nano .env
```

**Important variables to configure:**
- `DOMAIN_CORP` - Your domain name (e.g., `example.com`)
- `DB_PASSWORD` - Change to a strong password
- `DB_ROOT_PASSWORD` - Change to a strong password
- `SEARX_HOSTNAME` - Your SearXNG hostname

### 3. TLS Certificates (Optional but Recommended)

For production, place your certificates in `./traefik/certs/`:
- `certfile.pem` - Your SSL certificate
- `keyfile.pem` - Your private key
- `rootcafile.pem` - Root CA certificate

### 4. Start the Stack

```bash
# Build and start all services
docker compose up -d --build

# View logs
docker compose logs -f

# Check service health
docker compose ps
```

## 🔧 Services & Ports

| Service    | Internal Port | External Access         | Description                          |
|------------|---------------|-------------------------|--------------------------------------|
| Traefik    | 80, 443       | `http://your-domain`    | Reverse proxy & SSL termination      |
| Traefik DB | 8080          | `http://localhost:8080` | Dashboard (optional)                 |
| Watcher    | 9002          | `https://watcher.domain`| Main application                     |
| SearXNG    | 8080          | `https://searxng.domain`| Search engine                        |
| MySQL      | 3306          | Internal only           | Database (not exposed externally)    |
| CertStream | 8080          | Internal only           | Certificate transparency server      |

## 🔐 Security Features

- **Network isolation**: All services on dedicated network (`10.10.10.0/24`)
- **Minimal capabilities**: SearXNG runs with dropped capabilities
- **Read-only volumes**: Configuration files mounted as read-only
- **Health checks**: All services have health monitoring
- **TLS 1.2+**: Enforced minimum TLS version
- **No new privileges**: Traefik runs with security options

## 📊 Volumes

| Volume Name     | Purpose                    | Persistence |
|-----------------|----------------------------|-------------|
| `db_data`       | MySQL data                 | ✅ Yes      |
| `db_logs`       | MySQL logs                 | ✅ Yes      |
| `searx_data`    | SearXNG configuration      | ✅ Yes      |
| `watcher_static`| Watcher static files       | ✅ Yes      |
| `watcher_logs`  | Watcher application logs   | ✅ Yes      |

## 🛠️ Common Commands

```bash
# Rebuild Watcher after code changes
docker compose build watcher
docker compose up -d watcher

# Restart a specific service
docker compose restart watcher

# View logs for a service
docker compose logs -f watcher

# Access database shell
docker compose exec db_watcher mysql -u watcher_user -p

# Run database migrations
docker compose exec watcher python manage.py migrate

# Collect static files
docker compose exec watcher python manage.py collectstatic --noinput

# Stop all services
docker compose down

# Stop and remove volumes (⚠️ deletes data!)
docker compose down -v
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Internet                         │
└────────────────────┬────────────────────────────────┘
                     │
              ┌──────▼──────┐
              │   Traefik   │ :80, :443
              │  (Reverse   │
              │   Proxy)    │
              └──────┬──────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        │            │            │              │
  ┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐ ┌──────▼──────┐
  │  Watcher  │ │SearXNG │ │CertStream│ │  MySQL DB   │
  │  :9002    │ │ :8080  │ │  :8080   │ │   :3306     │
  └───────────┘ └────────┘ └──────────┘ └─────────────┘
        │            │            │              │
        └────────────┴────────────┴──────────────┘
                     │
          ┌──────────▼──────────┐
          │  watcher_network    │
          │   10.10.10.0/24     │
          └─────────────────────┘
```

## ⚙️ Advanced Configuration

### Custom Build Arguments

Edit the `watcher` service in `docker-compose.yml`:

```yaml
watcher:
  build:
    args:
      - PYTHON_VERSION=3.11
      - HTTP_PROXY=http://proxy.example.com
      - HTTPS_PROXY=https://proxy.example.com
```

### Scaling

For high availability, you can scale Watcher (stateless):

```bash
docker compose up -d --scale watcher=3
```

### Monitoring

Enable Traefik metrics:

```yaml
# In docker-compose.yml, add to traefik service:
command:
  - "--metrics.prometheus=true"
ports:
  - "8080:8080"  # Prometheus metrics endpoint
```

## 🐛 Troubleshooting

### Watcher fails to start
```bash
# Check logs
docker compose logs watcher

# Verify database is healthy
docker compose ps db_watcher

# Run migrations manually
docker compose exec watcher python manage.py migrate
```

### SSL/TLS issues
```bash
# Verify certificates are in place
ls -la ./traefik/certs/

# Check Traefik logs
docker compose logs traefik
```

### Database connection errors
```bash
# Test database connectivity
docker compose exec db_watcher mysqladmin status -u watcher_user -p

# Reset database (⚠️ deletes all data!)
docker compose down -v
docker compose up -d db_watcher
docker compose up -d watcher
```

## 📝 Environment Variables Reference

See `.env.example` for all available variables. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TZ` | UTC | Timezone |
| `DOMAIN_CORP` | example.com | Your domain |
| `DEBUG` | False | Debug mode |
| `DB_USER` | watcher_user | Database user |
| `DB_PASSWORD` | (required) | Database password |
| `SEARX_HOSTNAME` | searxng.domain | SearXNG hostname |

## 🔄 Updates

```bash
# Pull latest images (for external services)
docker compose pull

# Rebuild Watcher with latest code
docker compose build --no-cache watcher

# Restart all services
docker compose up -d
```

## 📄 License

Same as Watcher project license.
