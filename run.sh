#!/bin/bash

# FastAPI Server Run Script
# This script runs the FastAPI server in foreground or background mode
# Usage: ./run.sh [--background|-b] [--help|-h]

set -e

# Configuration
PYTHON_CMD="./venv/bin/python"
UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port 5000"
LOG_DIR="logs"
APP_NAME="anthropic-proxy"
PID_FILE="$APP_NAME.pid"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to show help
show_help() {
    echo "FastAPI Server Run Script"
    echo "========================"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --background, -b    Run server in background mode"
    echo "  --help, -h          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                  Run in foreground (default)"
    echo "  $0 --background     Run in background"
    echo "  $0 -b               Run in background (short form)"
    echo ""
    echo "Background Management Scripts:"
    echo "  ./start.sh          Start server in background"
    echo "  ./stop.sh           Stop background server"
    echo "  ./status.sh         Check server status"
    echo "  ./restart.sh        Restart server"
    echo ""
}

# Parse command line arguments
BACKGROUND=false
for arg in "$@"; do
    case $arg in
        --background|-b)
            BACKGROUND=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            show_help
            exit 1
            ;;
    esac
done

# Check if virtual environment exists
if [ ! -f "$PYTHON_CMD" ]; then
    echo "Error: Virtual environment not found at $PYTHON_CMD"
    echo "Please create virtual environment first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

if [ "$BACKGROUND" = true ]; then
    echo "Starting FastAPI server in background mode..."
    # Use start.sh script for background mode
    ./start.sh
else
    echo "Starting FastAPI server in foreground mode..."
    echo "Press Ctrl+C to stop the server"
    echo ""
    echo "Server will be available at: http://localhost:5000"
    echo "Documentation at: http://localhost:5000/docs"
    echo ""
    
    # Run in foreground
    exec "$PYTHON_CMD" -m uvicorn main:app --host 0.0.0.0 --port 5000
fi