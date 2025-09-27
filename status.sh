#!/bin/bash

# FastAPI Server Status Check Script
# This script checks if the FastAPI server is running

set -e

# Configuration
APP_NAME="anthropic-proxy"
PID_FILE="$APP_NAME.pid"
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/server.log"
ERROR_LOG_FILE="$LOG_DIR/server_error.log"
SERVER_URL="http://localhost:5000"

# Function to check if process is running
is_process_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            return 1
        fi
    else
        return 1
    fi
}

# Function to check if server is responding
is_server_responding() {
    if curl -s -f "$SERVER_URL/docs" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Check status
echo "Checking FastAPI server status..."
echo "================================="

if is_process_running; then
    PID=$(cat "$PID_FILE")
    echo "✅ Process is running (PID: $PID)"
    
    # Check process details
    echo "   Process details:"
    ps -p "$PID" -o pid,ppid,cmd --no-headers
    
    # Check if server is responding
    if is_server_responding; then
        echo "✅ Server is responding at $SERVER_URL"
        
        # Show uptime
        START_TIME=$(ps -p "$PID" -o lstart --no-headers)
        echo "   Started: $START_TIME"
        
        # Show log file info
        if [ -f "$LOG_FILE" ]; then
            LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
            echo "   Log file: $LOG_FILE ($LOG_SIZE)"
        fi
        
        if [ -f "$ERROR_LOG_FILE" ]; then
            ERROR_LOG_SIZE=$(du -h "$ERROR_LOG_FILE" | cut -f1)
            echo "   Error log: $ERROR_LOG_FILE ($ERROR_LOG_SIZE)"
        fi
        
        exit 0
    else
        echo "⚠️  Process is running but server is not responding"
        echo "   Server might be starting up or having issues"
        echo "   Check logs: tail -f $LOG_FILE"
        exit 1
    fi
else
    echo "❌ Server is not running"
    
    # Check for stale PID file
    if [ -f "$PID_FILE" ]; then
        echo "⚠️  Found stale PID file: $PID_FILE"
        echo "   You may want to remove it: rm $PID_FILE"
    fi
    
    # Check recent log files
    echo ""
    echo "Recent log files:"
    if [ -d "$LOG_DIR" ]; then
        ls -la "$LOG_DIR"/*.log 2>/dev/null | head -5 || echo "   No log files found"
    fi
    
    exit 1
fi