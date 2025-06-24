#!/bin/bash
# restore-data.sh - Restore the keystore database and .env file from a backup

set -e # Exit immediately if a command exits with a non-zero status

DB_BACKUP_FILE_ARG="$1" # The database backup file name passed as argument
ENV_BACKUP_FILE=""     # Will be derived from DB_BACKUP_FILE_ARG

# Check if a database backup file argument is provided
if [ -z "$DB_BACKUP_FILE_ARG" ]; then
    echo "Usage: $0 <database_backup_file>"
    echo "Available database backups:"
    ls -la ./backups/*.db 2>/dev/null || echo "    No .db backup files found in ./backups/"
    exit 1
fi

# Convert the provided backup file argument to an absolute path
# This is crucial for Docker to correctly resolve the host path.
HOST_ABS_DB_BACKUP_PATH=$(realpath "$DB_BACKUP_FILE_ARG")

# Validate if the database backup file exists using its absolute path on the host
if [ ! -f "$HOST_ABS_DB_BACKUP_PATH" ]; then
    echo "❌ Database backup file not found on host: $HOST_ABS_DB_BACKUP_PATH"
    exit 1
fi

# Derive the corresponding .env backup file name
TIMESTAMP_PART=$(echo "$DB_BACKUP_FILE_ARG" | sed -n 's/.*keystore_backup_\([0-9]\+_[0-9]\+\)\.db/\1/p')
if [ -n "$TIMESTAMP_PART" ]; then
    ENV_BACKUP_FILE="./backups/.env_backup_${TIMESTAMP_PART}.txt"
fi

echo "⚠️  This will replace the current database with data from $HOST_ABS_DB_BACKUP_PATH."
if [ -f "$ENV_BACKUP_FILE" ]; then
    echo "    It will also restore the associated .env file from $ENV_BACKUP_FILE."
else
    echo "    No corresponding .env backup file found. Your current .env file (if any) will remain."
    echo "    WARNING: If encryption/secret keys in your current .env do not match the backup database,"
    echo "    your API keys might become unreadable and JWT tokens invalid."
fi

read -p "    Are you sure you want to proceed with this restore? (y/N): " -n 1 -r
echo # (optional) move to a new line
if [[ ! "$REPLY" =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 1
fi

echo "🔄 Stopping API Keystore container (if running) for safe restore..."
# Stop the container if it's running
docker stop api-keystore 2>/dev/null || echo "API Keystore container not running."

echo "📥 Restoring database backup to persistent volume using Docker's bind mount copy mechanism..."

# Use a temporary busybox container to:
# 1. Mount the persistent 'keystore_data' volume to /volume_data
# 2. Mount the *specific database backup file* from the host (now an absolute path) to /tmp/backup.db (read-only)
# 3. Copy the database file from /tmp/backup.db to /volume_data/keystore.db
# 4. Set correct ownership (appuser:appuser, uid 1001) for the copied file within the volume
# All operations are now combined into a single sh -c command for atomicity and path consistency.
docker run --rm \
    -v keystore_data:/volume_data \
    -v "$HOST_ABS_DB_BACKUP_PATH:/tmp/backup.db:ro" \
    busybox \
    sh -c "cp /tmp/backup.db /volume_data/keystore.db && \
           chown 1001:1001 /volume_data/keystore.db"

echo "✅ Database restored to volume."

# Restore the .env file if the backup exists
if [ -f "$ENV_BACKUP_FILE" ]; then
    echo "📥 Restoring .env file from backup..."
    ENV_TARGET_PATH="./.env" # Assuming .env is in the same directory as script execution (app root)
    cp "$ENV_BACKUP_FILE" "$ENV_TARGET_PATH"
    echo "✅ .env file restored."
fi

echo "🚀 Starting API Keystore container..."
# Start the container (it will now use the restored database)
docker start api-keystore

echo "✅ Restore complete! Please allow a few seconds for the service to become healthy."
echo "    NOTE: If you restored the .env file, you may need to reload your shell or VS Code terminal"
echo "    if you intend to use helper scripts that rely on environment variables (like build-and-run.sh)."
