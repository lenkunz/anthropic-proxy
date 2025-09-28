# Logging System Improvements

## Summary

Successfully upgraded the anthropic-proxy application from scattered print/debug statements to a comprehensive structured logging system. The logs are now organized, trackable, and easy to analyze.

## What Was Improved

### Before
- Mixed print statements and debug output
- Incomplete logging scattered throughout the code
- Hard to track requests and debug issues
- Log output mixed with console output

### After
- **Structured logging system** with proper log levels and formatting
- **Organized log files** with separate categories:
  - `access.log` - HTTP requests and responses
  - `application.log` - General application events
  - `errors.log` - Error messages and stack traces
  - `debug.log` - Debug information when DEBUG mode is enabled
  - `api_requests.json` - Structured API request logs (JSON format)
  - `performance.json` - Performance metrics and timing data
- **Request correlation** with unique request IDs
- **Proper log rotation** to prevent log files from growing too large
- **Easy log analysis** with the `log_analyzer.py` utility

## New Files Created

1. **`logging_config.py`** - Central logging configuration with:
   - Multi-level logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
   - File rotation and size management
   - Request context tracking
   - Structured JSON output for API logs

2. **`log_analyzer.py`** - Log analysis utility with features:
   - List all log files
   - Tail log files in real-time
   - Search through log files
   - Filter by log level or date

## How to Use

### Running the Application
```bash
# Start with Docker Compose (recommended)
docker compose up -d --build

# Or run directly
python3 main.py
```

### Analyzing Logs
```bash
# Make the analyzer executable
chmod +x log_analyzer.py

# List all log files
./log_analyzer.py list

# Tail access log in real-time
./log_analyzer.py tail access.log

# Search for errors
./log_analyzer.py search errors.log "ERROR"

# Search with case-insensitive pattern
./log_analyzer.py search application.log "test" --ignore-case
```

### Log File Organization

All logs are stored in the `logs/` directory with clear naming:

- **access.log**: HTTP requests with timestamps, methods, URLs, and response codes
- **application.log**: General application events and info messages
- **errors.log**: Error messages with full stack traces
- **debug.log**: Detailed debug information (only when DEBUG=true)
- **api_requests.json**: Structured API request/response data in JSON format
- **performance.json**: Performance metrics and timing information

## Request Tracking

Each HTTP request now gets a unique request ID that appears in all related log entries, making it easy to trace a single request through the entire system:

```
2025-09-28 09:48:55 | INFO | ffc8dc30 | POST http://127.0.0.1:5000/v1/chat/completions
```

The `ffc8dc30` is the request ID that will appear in all logs related to this specific request.

## Configuration

The logging system can be configured via environment variables:
- `DEBUG=true` - Enable debug logging
- Log levels and file locations can be adjusted in `logging_config.py`

## Benefits

1. **Easier Debugging** - Clear, organized logs with request correlation
2. **Better Monitoring** - Separate log files for different types of events
3. **Performance Tracking** - Dedicated performance logging
4. **Scalable** - Log rotation prevents disk space issues
5. **Developer Friendly** - Easy-to-use log analysis tools

## Testing Verified

✅ Application starts without errors  
✅ HTTP requests are properly logged  
✅ Error handling works correctly  
✅ Log files are created and organized  
✅ Docker deployment works  
✅ Log analyzer utility functions properly  

The application now provides comprehensive, organized logging that makes tracking and debugging much easier than the previous scattered print/debug statements.