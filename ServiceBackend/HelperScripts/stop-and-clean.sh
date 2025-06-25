#!/bin/bash
# stop-and-clean.sh - Stop, remove container, and optionally remove data volume

set -e # Exit immediately if a command exits with a non-zero status

echo "🛑 Stopping API Keystore container..."
docker stop api-keystore 2>/dev/null || echo "API Keystore container not running."

echo "🗑️ Removing API Keystore container..."
docker rm api-keystore 2>/dev/null || echo "API Keystore container not found."

echo "" # Newline for readability
echo "⚠️  WARNING: This script can also delete your persistent data volume ('keystore_data')."
echo "    This will permanently remove all API keys, users, and logs you have created."
read -p "    Do you want to delete the 'keystore_data' volume and all its data? (y/N): " -n 1 -r
echo    # (optional) move to a new line
if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    echo "🗑️ Deleting 'keystore_data' volume..."
    docker volume rm keystore_data 2>/dev/null || echo "Docker volume 'keystore_data' not found or already removed."
    echo "✅ Data volume removed."
else
    echo "⏩ Skipping data volume removal. Your data will persist."
fi

echo "✅ Cleanup complete!"
