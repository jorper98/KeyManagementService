#!/bin/bash
# stop-and-clean.sh - Stop and remove container

echo "🛑 Stopping API Keystore container..."
docker stop api-keystore 2>/dev/null || echo "Container not running"

echo "🗑️  Removing API Keystore container..."
docker rm api-keystore 2>/dev/null || echo "Container not found"

echo "✅ Cleanup complete!"
