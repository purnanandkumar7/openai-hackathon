# ============================================================================
# Stage 1 – dependency builder
# ============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps required for asyncpg, cryptography, and weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pip and build tooling
RUN pip install --no-cache-dir --upgrade pip hatchling

# Copy only dependency manifests first for better layer caching
COPY pyproject.toml ./

# Install all production dependencies into a target directory
RUN pip install --no-cache-dir --prefix=/install ".[standard]" || \
    pip install --no-cache-dir --prefix=/install .


# ============================================================================
# Stage 2 – runtime image
# ============================================================================
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.title="Atlas AI Backend"
LABEL org.opencontainers.image.description="Multi-agent incident response platform"
LABEL org.opencontainers.image.version="0.1.0"

# Minimal system runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango1.0-0 \
    libgdk-pixbuf2.0-0 \
    curl \
    kubectl \
    && rm -rf /var/lib/apt/lists/* \
    # Install kubectl
    && KUBECTL_VERSION=$(curl -sL https://dl.k8s.io/release/stable.txt) \
    && curl -sLO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# Non-root user for security
RUN groupadd --gid 1001 atlas && \
    useradd --uid 1001 --gid atlas --shell /bin/bash --create-home atlas

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application source
COPY app/ ./app/

# Ensure the non-root user owns the app directory
RUN chown -R atlas:atlas /app

USER atlas

# Expose the application port
EXPOSE 8000

# Healthcheck – poll the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fs http://localhost:8000/health || exit 1

# Default command – can be overridden via docker-compose / Kubernetes
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--log-config", "/dev/null"]
