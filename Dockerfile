# ─────────────────────────────────────────────────────────────────────────────
# Stage 1: Builder
# Install build tools and create wheels from pyproject.toml
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build tooling
RUN pip install --upgrade pip build

# Copy only dependency files first (better layer caching)
COPY pyproject.toml README.md ./

# Copy source
COPY src/ ./src/

# Build the wheel from pyproject.toml
RUN python -m build --wheel --outdir /dist

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2: Runtime
# Minimal image — just install the built wheel
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

LABEL maintainer="Alexandre Delisle <oss@adelisle.com>"
LABEL description="GitHub Security Token Service (STS) - OIDC to GitHub token exchange"
# x-release-please-start-version
LABEL version="0.1.1"
# x-release-please-end

# Create a non-root user for security
RUN useradd --create-home appuser

# Copy only the built wheel from the builder stage (as root, before user switch)
COPY --from=builder /dist/*.whl /tmp/

# Install the wheel (no build deps needed at runtime)
RUN pip install --no-cache-dir /tmp/*.whl && rm -rf /tmp/*.whl

# Switch to non-root user
USER appuser
WORKDIR /home/appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health', timeout=2)" || exit 1

# Set the default command to run the FastAPI app with uvicorn
CMD ["python", "-m", "uvicorn", "github_sts.main:app", "--host", "0.0.0.0", "--port", "8080"]


