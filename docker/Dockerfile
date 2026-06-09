# ============================================================
# Brain Cluster — Docker 部署
# ============================================================
# 用法:
#   docker build -t brain-cluster -f docker/Dockerfile .
#   docker-compose -f docker/docker-compose.yml up -d
# ============================================================

# ===== Stage 1: Frontend Build =====
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY staroffice-ui/frontend-v2/package.json staroffice-ui/frontend-v2/package-lock.json ./
RUN npm ci --production=false
COPY staroffice-ui/frontend-v2/ ./
RUN npm run build

# ===== Stage 2: Python Backend + Frontend =====
FROM python:3.13-slim AS runtime

LABEL org.brain.cluster.version="2.3.0"
LABEL org.brain.cluster.description="24/7 Self-Evolving Multi-Agent Cluster"

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project files
COPY tools/ ./tools/
COPY input/ ./input/
COPY output/ ./output/
COPY hermes-agent/ ./hermes-agent/

# Frontend (from build stage)
COPY --from=frontend-build /app/frontend/dist ./staroffice-ui/frontend-v2/dist

# Configuration
COPY docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose ports
# 18791: StarOfficeUI Backend | 5173: Frontend Dev | 3001: Grafana
EXPOSE 18791 5173 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:18791/api/monitor || exit 1

CMD ["/app/start.sh"]
