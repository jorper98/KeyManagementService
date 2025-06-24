#!/bin/bash
# backup-data.sh - Backup the keystore database and .env file to the persistent Docker volume

set -e # Exit immediately if a command exits with a non-zero status

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="keystore_backup_${TIMESTAMP}.db"
ENV_BACKUP_FILE=".env_backup_${TIMESTAMP}.txt" # New: Backup file for .env

# Create the backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup of keystore database from persistent volume..."

# Find the mount point of the Docker volume on the host
VOLUME_MOUNT_PATH=$(docker volume inspect keystore_data --format '{{ .Mountpoint }}' 2>/dev/null)

if [ -z "$VOLUME_MOUNT_PATH" ]; then
    echo "❌ Error: Docker volume 'keystore_data' not found. Is your service running or has the volume been removed?"
    echo "    Cannot back up database. Continuing with .env backup only if found."
    DB_BACKUP_SUCCESS=false
else
    DB_PATH_IN_VOLUME="${VOLUME_MOUNT_PATH}/keystore.db"
    TARGET_DB_BACKUP_FILE="${BACKUP_DIR}/${DB_BACKUP_FILE}"

    # Check if the database file exists in the volume
    if [ ! -f "$DB_PATH_IN_VOLUME" ]; then
        echo "⚠️ Warning: keystore.db not found in the volume at $DB_PATH_IN_VOLUME. Database might not be initialized yet."
        echo "    A database backup file will still be created, but it might be empty or contain only default data."
        touch "$TARGET_DB_BACKUP_FILE" # Create empty file to indicate backup attempt
    else
        # Copy the database file from the volume's mount point to the backup directory
        cp "$DB_PATH_IN_VOLUME" "$TARGET_DB_BACKUP_FILE"
    fi
    echo "✅ Database backup created: ${TARGET_DB_BACKUP_FILE}"
    DB_BACKUP_SUCCESS=true
fi

echo "🔐 Backing up .env file..."
ENV_FILE="./.env" # Corrected path: assuming .env is in the same directory as script execution (app root)
TARGET_ENV_BACKUP_FILE="${BACKUP_DIR}/${ENV_BACKUP_FILE}"

if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$TARGET_ENV_BACKUP_FILE"
    echo "✅ .env file backup created: ${TARGET_ENV_BACKUP_FILE}"
else
    echo "⚠️ Warning: .env file not found at ${ENV_FILE}. Cannot back up encryption/secret keys."
    echo "    To restore data to another server, these keys are CRITICAL. Ensure you back them up manually."
fi

if $DB_BACKUP_SUCCESS; then
    echo "✅ Full backup process complete!"
else
    echo "⚠️ Backup process completed with warnings (database not backed up)."
fi
