# ── BUILDER STAGE ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency manifests first to maximise layer cache reuse
COPY pyproject.toml uv.lock ./

# Install production-only dependencies into the project venv
RUN uv sync --no-dev --frozen

# Copy application source and alembic migration files
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini


# ── RUNTIME STAGE ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user for secure process execution (T-07-01)
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy only the venv and application source from builder (no build tools)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

# Create image cache directory and set ownership before switching to non-root
RUN mkdir -p /images && chown appuser:appuser /images

# Add venv binaries to PATH and set Python source root
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Run as non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "carpix_images.main:app", "--host", "0.0.0.0", "--port", "8000"]
