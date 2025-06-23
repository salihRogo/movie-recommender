#!/bin/sh
set -e

# Start the backend API server in the background
echo "Starting FastAPI backend..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &

# Start the frontend server in the foreground
echo "Starting Node frontend server..."
node server.js
