#!/bin/bash

# FastAPI Server Background Start Script
# This script starts the FastAPI server in background mode

set -e

# Configuration
APP_NAME="anthropic-proxy"
PID_FILE="$APP_NAME.pid"
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/server.log"
ERROR_LOG_FILE="$LOG_DIR/server_error.log"
PYTHON_CMD="./venv/bin/python"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Check if server is already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Server is already running with PID: $PID"
        exit 1
    else
        echo "Stale PID file found. Removing..."
        rm -f "$PID_FILE"
    fi
fi

# Check if virtual environment exists
if [ ! -f "$PYTHON_CMD" ]; then
    echo "Error: Virtual environment not found at $PYTHON_CMD"
    echo "Please create virtual environment first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "Starting FastAPI server in background..."

# Start server in background with nohup
nohup "$PYTHON_CMD" -m uvicorn main:app --host 0.0.0.0 --port 5000 > "$LOG_FILE" 2> "$ERROR_LOG_FILE" &

# Get the PID of the background process
PID=$!
echo $PID > "$PID_FILE"

# Wait a moment to check if server started successfully
sleep 2

if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo "   PID: $PID"
    echo "   Log file: $LOG_FILE"
    echo "   Error log: $ERROR_LOG_FILE"
    echo "   PID file: $PID_FILE"
    echo ""
    echo "To stop the server: ./stop.sh"
    echo "To check status: ./status.sh"
    echo "To view logs: tail -f $LOG_FILE"
else
    echo "❌ Failed to start server"
    echo "Check error log: $ERROR_LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi