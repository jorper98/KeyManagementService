#!/bin/bash
# build-and-run.sh - Build and run the container

set -e

echo "🔧 Building API Keystore Docker image..."
docker build -t api-keystore .

echo "🚀 Starting API Keystore container..."
docker run -d \
  --name api-keystore \
  -p 5000:5000 \
  -v keystore_data:/app/data \
  -e SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 32)}" \
  -e ENCRYPTION_KEY="${ENCRYPTION_KEY:-$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')}" \
  --restart unless-stopped \
  api-keystore

echo "✅ Container started successfully!"
echo "🌐 Access the web interface at: http://localhost:5000"
echo "📋 Default credentials:"
echo "   Admin: admin / admin123"
echo "   User:  user  / user123"

# Wait for health check
echo "⏳ Waiting for service to be ready..."
sleep 5

if curl -f http://localhost:5000/health >/dev/null 2>&1; then
    echo "✅ Service is healthy and ready!"
else
    echo "⚠️  Service might still be starting up. Check logs with: docker logs api-keystore"
fi