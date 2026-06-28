# Multi-stage Docker build for GraphNovel
#
# Stages:
#   1. frontend-build: npm install + vite build
#   2. frontend-serve: nginx serving static files
#   3. backend: Python 3.12 + uvicorn

# ============ Frontend Build Stage ============
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* frontend/pnpm-lock.yaml* ./
RUN if [ -f pnpm-lock.yaml ]; then \
      npm install -g pnpm && pnpm install --frozen-lockfile; \
    else \
      npm install --legacy-peer-deps; \
    fi
COPY frontend/ ./
RUN npm run build

# ============ Frontend Serve (nginx) ============
FROM nginx:alpine AS frontend-serve
COPY --from=frontend-build /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

# ============ Backend Stage ============
FROM python:3.12-slim AS backend
WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies in venv (avoids --user conflicts with torch)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-cache embedding model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')"

# Offline mode: prevent runtime model downloads
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV HF_HUB_OFFLINE=1

# Copy backend code
COPY backend/ .

# Copy built frontend static files
COPY --from=frontend-build /app/frontend/dist /app/static

# Entrypoint
COPY backend/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN groupadd -r graphnovel && useradd -r -g graphnovel graphnovel && \
    chown -R graphnovel:graphnovel /app
USER graphnovel

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
