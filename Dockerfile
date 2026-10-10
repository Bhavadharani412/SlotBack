# ==============================================================================
# Stage 1: Build Frontend Assets
# ==============================================================================
FROM node:20-alpine AS frontend-builder
WORKDIR /build

# Enable corepack and install pnpm
RUN corepack enable && corepack prepare pnpm@9 --activate

# Install dependencies with lockfile freezing
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# Copy source and compile production bundle
COPY frontend/ ./
RUN pnpm build

# ==============================================================================
# Stage 2: Production Application Runtime
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Install security updates and PostgreSQL client utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application backend code, migrations, and scripts
COPY backend/ ./backend/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Copy compiled static frontend artifacts from builder
COPY --from=frontend-builder /build/dist ./frontend/dist

# Non-root least-privilege runtime user
RUN useradd -m -u 1001 slotback && chown -R slotback:slotback /app
USER slotback

EXPOSE 8000

ENV APP_ENV=production \
    DEBUG=false \
    PYTHONUNBUFFERED=1

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD curl -f http://localhost:8000/health/ready || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips=*"]
