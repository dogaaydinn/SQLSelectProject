# CUDA Analytics Service Dockerfile
# Multi-stage build with CUDA 12.x support

# ==========================================
# Stage 1: CUDA Runtime Base
# ==========================================
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 as base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CUDA_HOME=/usr/local/cuda \
    PATH=/usr/local/cuda/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    git \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3.11 -m pip install --upgrade pip setuptools wheel

# ==========================================
# Stage 2: Dependencies
# ==========================================
FROM base as dependencies

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# Note: cuPy and cuDF require CUDA to be installed
RUN pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 3: Application
# ==========================================
FROM dependencies as application

# Copy application code
COPY app /app/app

# Create non-root user for security
RUN useradd -m -u 1000 analytics && \
    chown -R analytics:analytics /app

USER analytics

# Expose ports
EXPOSE 8001 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command
CMD ["python3.11", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
