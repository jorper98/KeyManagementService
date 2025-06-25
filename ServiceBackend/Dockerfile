# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# curl is added for healthcheck, gcc is for cryptography library
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better cachinga
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and static assets
COPY enhanced_keystore_service.py .
COPY keystore_web_frontend.html .
COPY style.css . 

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV FLASK_APP=enhanced_keystore_service.py
ENV FLASK_ENV=production
# This DATABASE path is critical for persistence, aligned with Docker volume
ENV DATABASE=/app/data/keystore.db 

# Expose port
EXPOSE 5000

# Create non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the application
CMD ["python", "enhanced_keystore_service.py"]
