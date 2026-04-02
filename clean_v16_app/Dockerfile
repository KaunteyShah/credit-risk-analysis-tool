# Optimized multi-stage build for better performance
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies with optimizations
COPY requirements.txt requirements.txt
# Install CPU-only torch first to avoid downloading 2GB+ of CUDA libraries
# (sentence-transformers depends on torch but only needs CPU inference on ACI)
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Set optimized environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV DATABASE_TYPE=files
ENV PORT=8000
# Performance optimizations
ENV MALLOC_ARENA_MAX=2
ENV PYTHONHASHSEED=random
ENV WORKERS=4
# Gunicorn timeout — must be long enough for a 200-page PDF download + OCR + embed.
# 900 s (15 min) gives ample headroom; the heartbeat keeps users informed throughout.
ENV GUNICORN_TIMEOUT=900

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY . .

# Create logs directory and optimize permissions
RUN mkdir -p logs && \
    chmod +x startup.py && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Make sure user local bin is in PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE $PORT

# Optimized health check
HEALTHCHECK --interval=15s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run with optimized gunicorn configuration
CMD ["sh", "-c", "gunicorn --bind=0.0.0.0:${PORT:-8000} --workers=${WORKERS:-4} --worker-class=gthread --threads=4 --worker-connections=1000 --max-requests=500 --max-requests-jitter=50 --preload --timeout=${GUNICORN_TIMEOUT:-900} --graceful-timeout=30 --keep-alive=5 startup:app"]