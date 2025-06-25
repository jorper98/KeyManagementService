#!/bin/bash
# check-data.sh - Display environment variables, Docker health status, and database counts in the API Keystore container

echo "🔍 Running data checks on API Keystore container..."

# Check if the container is running and get its ID
CONTAINER_ID=$(docker ps --filter "name=api-keystore" --format "{{.ID}}")

if [ -z "$CONTAINER_ID" ]; then
    echo "❌ Error: API Keystore container is not running. Please start it first (e.g., with ./HelperScripts/build-and-run.sh or ./HelperScripts/stop-and-rebuild.sh)."
    exit 1
fi

echo "--- Container Status ---"
echo "✅ API Keystore container is running."

# Check Docker's internal health status
HEALTH_STATUS=$(docker inspect --format='{{json .State.Health}}' "$CONTAINER_ID" 2>/dev/null)

if [ -n "$HEALTH_STATUS" ]; then
    STATUS=$(echo "$HEALTH_STATUS" | grep -o '"Status":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    echo "🩺 Docker Health Check Status: $STATUS"
    if [ "$STATUS" = "unhealthy" ]; then
        echo "⚠️  Details: $(echo "$HEALTH_STATUS" | grep -o '"Log":\[[^]]*\]' | sed 's/{"ExitCode":.*,"Output":"//g;s/"}//g;s/\\n/\n        /g' | tail -n 1)"
    fi
else
    echo "❔ Docker Health Check Status: Not configured or unavailable."
fi

echo "--- Environment Variables ---"
echo "🌐 All environment variables inside the container:"
docker exec "$CONTAINER_ID" printenv

echo ""
echo "📦 Specific 'DATABASE' environment variable inside the container:"
docker exec "$CONTAINER_ID" printenv DATABASE

echo ""
echo "🐍 Python's view of 'DATABASE' environment variable inside the container:"
docker exec "$CONTAINER_ID" python3 -c "import os; print(os.environ.get('DATABASE', 'NOT_SET'))"

echo "--- Database Counts ---"
echo "👤 Total users in database:"
docker exec "$CONTAINER_ID" python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/keystore.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM users'); count = cursor.fetchone()[0]; conn.close(); print(f'Total users in database: {count}')"

echo ""
echo "🔑 Total API keys in database:"
docker exec "$CONTAINER_ID" python3 -c "import sqlite3; conn = sqlite3.connect('/app/data/keystore.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM api_keys'); count = cursor.fetchone()[0]; conn.close(); print(f'Total API keys in database: {count}')"

echo "--- Checks Complete ---"
