#!/bin/bash

# FastAPI Server Restart Script
# This script restarts the FastAPI server running in background

set -e

# Configuration
APP_NAME="anthropic-proxy"
PID_FILE="$APP_NAME.pid"

echo "Restarting FastAPI server..."
echo "=========================="

# Check if server is running and stop it if it is
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Server is running (PID: $PID), stopping it first..."
        ./stop.sh
        echo "Server stopped successfully"
    else
        echo "Found stale PID file, removing it..."
        rm -f "$PID_FILE"
    fi
else
    echo "Server is not running"
fi

# Wait a moment before restarting
echo "Waiting 2 seconds before restart..."
sleep 2

# Start the server
echo "Starting server..."
./start.sh

# Check if server started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Server restarted successfully!"
    echo "Use './status.sh' to verify server is running properly"
else
    echo ""
    echo "❌ Failed to restart server"
    exit 1
fi