
#!/bin/bash
# backup-data.sh - Backup the keystore database

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="keystore_backup_${TIMESTAMP}.db"

mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup of keystore database..."
docker exec api-keystore cp /app/data/keystore.db /tmp/keystore_backup.db
docker cp api-keystore:/tmp/keystore_backup.db "${BACKUP_DIR}/${BACKUP_FILE}"

echo "✅ Backup created: ${BACKUP_DIR}/${BACKUP_FILE}"