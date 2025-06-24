
#!/bin/bash
# restore-data.sh - Restore the keystore database

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la ./backups/
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  This will replace the current database. Are you sure? (y/N)"
read -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled."
    exit 1
fi

echo "🔄 Stopping container..."
docker stop api-keystore

echo "📥 Restoring backup..."
docker cp "$BACKUP_FILE" api-keystore:/app/data/keystore.db

echo "🚀 Starting container..."
docker start api-keystore

echo "✅ Restore complete!"