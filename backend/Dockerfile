# ResQ — Dockerfile (multi-stage, uv-powered).
#
# Stage builder   : install uv, sync production deps, copy source
# Stage runtime   : minimal python:3.11-slim, only .venv + app code
#
# Usage:
#   docker build -t resq-backend:latest -f backend/Dockerfile backend/
#   docker run -p 8000:8000 resq-backend:latest


# ── Stage 1: Builder ──────────────────────────────────────
FROM python:3.11-slim AS builder

# Install uv (Astral's fast Python package manager)
RUN pip install --no-cache-dir uv

WORKDIR /app

# Layer 1: dependencies only (cached until pyproject / lock change)
COPY pyproject.toml uv.lock ./
RUN uv sync \
    --no-group dev \
    --frozen \
    --no-install-project

# Layer 2: application source
COPY . .

# Final sync — install the project itself into .venv
RUN uv sync \
    --no-group dev \
    --frozen


# ── Stage 2: Runtime ──────────────────────────────────────
FROM python:3.11-slim AS runtime

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

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
