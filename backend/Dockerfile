# Tervo — Dockerfile (multi-stage, uv-powered).
#
# Stage builder   : install uv, sync production deps, copy source
# Stage runtime   : minimal python:3.11-slim, only .venv + app code
#
# Usage:
#   docker build --build-arg VCS_REF="$(git rev-parse HEAD)" \
#     -t tervo-backend:local -f backend/Dockerfile backend/
#   docker run --env-file backend/.env -p 127.0.0.1:8000:8000 \
#     -v tervo-uploads:/app/uploads tervo-backend:local


# ── Stage 1: Builder ──────────────────────────────────────
FROM python:3.11-slim@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce AS builder

# Exact published uv version compatible with the committed lockfile.
RUN pip install --no-cache-dir uv==0.11.24

WORKDIR /app

# Never download a different Python interpreter during dependency installation.
ENV UV_PYTHON_DOWNLOADS=never

# Layer 1: dependencies only (cached until pyproject / lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync \
    --no-group dev \
    --frozen \
    --no-install-project

# Layer 2: application source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini main.py ./


# ── Stage 2: Runtime ──────────────────────────────────────
FROM python:3.11-slim@sha256:0dd364ba7e10242f07755449e3a3d0e35f9efd987952737b90def6709ab0c5ce AS runtime

ARG VCS_REF=unknown
LABEL org.opencontainers.image.revision="${VCS_REF}"

# WeasyPrint libraries; retain the existing cairo/pixbuf stack.
# Debian package versions remain mutable despite the pinned Python base.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libharfbuzz-subset0 \
        libgdk-pixbuf-2.0-0 \
        shared-mime-info \
        libffi8 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the prepared virtual environment (keeps image small)
COPY --from=builder /app/.venv /app/.venv

# Copy only the code needed at runtime
COPY --from=builder /app/app        /app/app
COPY --from=builder /app/alembic    /app/alembic
COPY --from=builder /app/alembic.ini /app/
COPY --from=builder /app/main.py    /app/

# Make venv binaries available
ENV PATH="/app/.venv/bin:$PATH"

# Create the uploads directory expected by the app
RUN mkdir -p /app/uploads/photos
VOLUME ["/app/uploads"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
