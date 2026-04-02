# Use Python 3.11 slim image for efficiency (AMD64 architecture)
FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV DATABASE_TYPE=files

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy .env file for environment variables
COPY .env .env

# Create logs directory
RUN mkdir -p logs

# Expose port 5000
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/modular/health || exit 1

# Run the FULL Credit Risk Analysis Tool
CMD ["python", "app.py"]