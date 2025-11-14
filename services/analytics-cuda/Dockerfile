# Analytics CUDA Service Dockerfile
# Multi-stage build with optional CUDA support

# Base stage - CPU only
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]


# GPU stage (optional) - With CUDA support
FROM nvidia/cuda:12.0.0-runtime-ubuntu22.04 as gpu

WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install with CUDA support
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir cupy-cuda12x==12.3.0

# Copy application code
COPY app/ ./app/

# Set environment variables for GPU
ENV CUDA_VISIBLE_DEVICES=0
ENV ENABLE_CUDA=true

# Expose port
EXPOSE 8001

# Run application
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
