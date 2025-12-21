# Multi-stage build for optimized Alpine image

# ============================================
# Stage 1: Builder - Compile dependencies
# ============================================
FROM python:3.13-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies for compiling Python packages
# gcc, musl-dev: C compiler and standard library
# libffi-dev: Foreign Function Interface (needed by cryptography)
# openssl-dev: SSL/TLS development files (needed by python-jose)
# cargo, rust: Rust toolchain (required by cryptography >= 3.4)
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CARGO_NET_GIT_FETCH_WITH_CLI=true

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================
# Stage 2: Runtime - Minimal production image
# ============================================
FROM python:3.13-alpine

# Set working directory
WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apk add --no-cache \
    libffi \
    openssl

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/install/bin:$PATH" \
    PYTHONPATH="/install/lib/python3.13/site-packages"

# Copy installed Python packages from builder
COPY --from=builder /install /install

# Copy only application code (exclude dev files via .dockerignore)
COPY main.py .
COPY app/ ./app/

# Expose port
EXPOSE 8080

# Run with gunicorn for production
CMD ["gunicorn", "main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8080", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
