#!/bin/bash

# FastAPI Server Stop Script
# This script stops the FastAPI server running in background

set -e

# Configuration
APP_NAME="anthropic-proxy"
PID_FILE="$APP_NAME.pid"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo "❌ PID file not found: $PID_FILE"
    echo "Server may not be running or was not started with start.sh"
    exit 1
fi

# Read PID from file
PID=$(cat "$PID_FILE")

# Check if process is actually running
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process with PID $PID is not running"
    echo "Removing stale PID file..."
    rm -f "$PID_FILE"
    exit 1
fi

echo "Stopping FastAPI server (PID: $PID)..."

# Try graceful shutdown first
kill "$PID" 2>/dev/null

# Wait for graceful shutdown
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Server stopped gracefully"
        rm -f "$PID_FILE"
        exit 0
    fi
    echo "Waiting for server to stop... ($i/10)"
    sleep 1
done

# Force kill if graceful shutdown failed
echo "⚠️  Graceful shutdown failed, forcing termination..."
kill -9 "$PID" 2>/dev/null

# Final check
if ps -p "$PID" > /dev/null 2>&1; then
    echo "❌ Failed to kill process $PID"
    exit 1
else
    echo "✅ Server force-killed successfully"
    rm -f "$PID_FILE"
    exit 0
fi