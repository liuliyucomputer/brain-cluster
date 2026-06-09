#!/bin/bash
# Brain Cluster Docker Entrypoint

set -e

echo "=== Brain Cluster v2.3.0 ==="
echo "Starting services in Docker..."

# Ensure data directories
mkdir -p /app/data /app/output/memory/daily /app/output/memory/weekly /app/output/memory/monthly /app/output/memory/vector

# Copy kanban.db if available from host mount
if [ -f /app/data/kanban.db ]; then
    export KANBAN_DB=/app/data/kanban.db
    echo "kanban.db found at /app/data/kanban.db"
else
    echo "Warning: kanban.db not found. Some features will be limited."
fi

# Start StarOfficeUI backend
echo "Starting StarOfficeUI Backend on :18791..."
cd /app/staroffice-ui/backend
python app.py &

# Wait for backend to be ready
sleep 2
echo "Services started. Health check: http://localhost:18791/health"

# Keep container running
wait
