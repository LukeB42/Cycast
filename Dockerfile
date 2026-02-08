# Cycast Docker Image
# Multi-stage build for optimized image size

# Build stage - compile Cython extensions
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY *.py *.pyx setup.py ./

# Build Cython extensions
RUN python setup.py build_ext --inplace

# Runtime stage - minimal image
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 cycast && \
    mkdir -p /app/music /var/log/cycast && \
    chown -R cycast:cycast /app /var/log/cycast

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy application files
COPY --chown=cycast:cycast *.py ./
COPY --chown=cycast:cycast config.hcl ./

# Copy compiled Cython extensions from builder
COPY --from=builder --chown=cycast:cycast /build/*.so ./

# Switch to non-root user
USER cycast

# Expose ports
EXPOSE 8000 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/status')" || exit 1

# Default command
CMD ["python", "cycast_server.py"]
