#!/bin/bash
# generate-keys.sh - Generate secure keys for environment

echo "🔐 Generating secure keys for your keystore..."

SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

cat > .env << EOF
# Generated keys for API Keystore
SECRET_KEY=$SECRET_KEY
ENCRYPTION_KEY=$ENCRYPTION_KEY
DATABASE=/app/data/keystore.db
FLASK_ENV=production
EOF

echo "✅ Keys generated and saved to .env file"
echo "🔒 Keep these keys secure and never commit them to version control!"

