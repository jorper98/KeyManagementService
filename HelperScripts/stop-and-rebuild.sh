#!/bin/bash
# stop-and-rebuild.sh - Stop, rebuild image, and start container (preserving data)

set -e # Exit immediately if a command exits with a non-zero status

echo "🔄 Stopping and removing existing API Keystore container (preserving data volume)..."
# Stop the container if it's running
docker stop api-keystore 2>/dev/null || echo "API Keystore container not running."
# Remove the container instance (this does NOT delete the 'keystore_data' volume)
docker rm api-keystore 2>/dev/null || echo "API Keystore container not found."

echo "🔧 Building API Keystore Docker image..."
# Build the Docker image from the current directory's Dockerfile
# Ensure you are running this script from your project's root directory or adjust the path.
docker build -t api-keystore .

# Source the .env file to load SECRET_KEY and ENCRYPTION_KEY into the shell's environment
# This assumes .env is in the parent directory if this script is in HelperScripts
if [ -f "../.env" ]; then
    echo "🔑 Sourcing .env file for environment variables..."
    source ../.env
elif [ -f ".env" ]; then
    echo "🔑 Sourcing .env file for environment variables (local)..."
    source .env
else
    echo "⚠️ .env file not found. Ensure SECRET_KEY and ENCRYPTION_KEY are set in your environment."
    # The docker run command below will generate defaults if env vars are not set
fi

echo "🚀 Starting new API Keystore container..."
# Run the new container, reusing the 'keystore_data' volume
# The -e flags use the environment variables sourced above. If they are not set,
# the default values (using openssl and python3) will be generated.
docker run -d \
  --name api-keystore \
  -p 5000:5000 \
  -v keystore_data:/app/data \
  -e SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 32)}" \
  -e ENCRYPTION_KEY="${ENCRYPTION_KEY:-$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')}" \
  --restart unless-stopped \
  api-keystore

echo "✅ Container rebuilt and started successfully!"
echo "🌐 Access the web interface at: http://localhost:5000"
echo "📋 Default credentials (if database was initialized fresh):"
echo "   Admin: admin / admin123"
echo "   User:  user  / user123"

# Wait for health check
echo "⏳ Waiting for service to be ready..."
sleep 5

if curl -f http://localhost:5000/health >/dev/null 2>&1; then
    echo "✅ Service is healthy and ready!"
else
    echo "⚠️  Service might still be starting up or encountered an issue. Check logs with: ./HelperScripts/logs.sh"
fi
