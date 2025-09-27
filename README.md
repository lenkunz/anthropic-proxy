# Anthropic Proxy - FastAPI Server

This is a FastAPI-based proxy service for Anthropic's API with OpenAI-compatible endpoints.

## Setup

### Prerequisites

- Python 3.8+
- Virtual environment

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables (see `.env` file)

## Server Management Scripts

### Overview

The project includes comprehensive server management scripts for both foreground and background execution. All scripts are executable and ready to use.

### Scripts Available

#### [`run.sh`](run.sh) - Main Runner Script
The primary script for running the server with flexible options.

**Usage:**
```bash
# Run in foreground (default)
./run.sh

# Run in background mode
./run.sh --background
./run.sh -b  # Short form

# Show help
./run.sh --help
./run.sh -h
```

**Features:**
- Foreground execution (default)
- Background execution with `--background` flag
- Automatic virtual environment checking
- Help documentation

#### [`start.sh`](start.sh) - Background Start Script
Starts the server in background mode with process management.

**Usage:**
```bash
./start.sh
```

**Features:**
- Background execution using `nohup`
- PID file management (`anthropic-proxy.pid`)
- Automatic log directory creation
- Process monitoring and validation
- Virtual environment checking
- Graceful startup verification

#### [`stop.sh`](stop.sh) - Background Stop Script
Stops the background server gracefully or forcefully.

**Usage:**
```bash
./stop.sh
```

**Features:**
- Graceful shutdown (SIGTERM)
- Force kill if graceful shutdown fails (SIGKILL)
- PID file cleanup
- Process validation
- Stale PID file handling

#### [`status.sh`](status.sh) - Status Check Script
Checks if the server is running and provides detailed information.

**Usage:**
```bash
./status.sh
```

**Features:**
- Process status checking
- Server responsiveness testing
- Process details (PID, command, start time)
- Log file information
- Stale PID file detection

#### [`restart.sh`](restart.sh) - Restart Script
Restarts the background server safely.

**Usage:**
```bash
./restart.sh
```

**Features:**
- Automatic server detection and stop
- Safe restart with delay
- Startup verification
- Error handling

### Background Execution

#### Log Management
- **Standard logs:** `logs/server.log`
- **Error logs:** `logs/server_error.log`
- **PID file:** `anthropic-proxy.pid`
- **Log rotation:** Manual (scripts show log file sizes)

#### Process Management
- **PID tracking:** All background processes use PID files
- **Graceful shutdown:** Attempts SIGTERM before SIGKILL
- **Automatic cleanup:** PID files removed on clean shutdown
- **Stale detection:** Identifies and handles orphaned PID files

### Common Workflows

#### Development (Foreground)
```bash
# Run in foreground for development
./run.sh

# Or use direct command
./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 5000
```

#### Production (Background)
```bash
# Start server in background
./start.sh

# Check status
./status.sh

# View logs
tail -f logs/server.log
tail -f logs/server_error.log

# Stop server
./stop.sh
```

#### Testing and Maintenance
```bash
# Quick restart
./restart.sh

# Check if server is responsive
./status.sh

# Monitor logs
tail -f logs/server.log
```

### Configuration

#### Server Settings
- **Host:** `0.0.0.0` (all interfaces)
- **Port:** `5000`
- **Application:** `main:app`
- **Command:** `./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 5000`

#### Environment Variables
Server configuration is managed through the `.env` file. Common options:

| Variable | Default | Description |
| --- | --- | --- |
| `SERVER_API_KEY` | empty | Static API key injected when client requests do not provide one. |
| `FORWARD_CLIENT_KEY` | `true` | When true, forwards incoming `Authorization`/`x-api-key` headers to the upstream service. |
| `FORWARD_COUNT_TO_UPSTREAM` | `true` | Enables proxying `/v1/messages/count_tokens` calls to the upstream API instead of using local estimates. |
| `UPSTREAM_BASE` | `https://api.z.ai/api/anthropic` | Base URL for Anthropic-compatible upstream requests. |
| `MODEL_MAP_JSON` | `{}` | JSON object mapping OpenAI model names to Anthropic model identifiers. |
| `OPENAI_MODELS_LIST_JSON` | `["glm-4.5","glm-4.5v"]` | Override the models returned by `GET /v1/models`. |
| `AUTOTEXT_MODEL` | `glm-4.5` | Default text model when requests omit `model`. |
| `AUTOVISION_MODEL` | `glm-4.5` | Default multimodal model used for image capable requests without an explicit `model`. |
| `FORCE_ANTHROPIC_BETA` | `false` | Forces the `anthropic-beta` header even if the client does not request it. |
| `DEFAULT_ANTHROPIC_BETA` | `prompt-caching-2024-07-31` | Value used for the `anthropic-beta` header when beta support is enabled. |
| `COUNT_SHAPE_COMPAT` | `true` | Aligns token counting responses with OpenAI's response shape. |

Add any custom values to `.env` and restart the service to apply changes.

### Troubleshooting

#### Common Issues

1. **Virtual environment not found:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Port already in use:**
   ```bash
   # Check what's using the port
   lsof -i :5000
   # Kill the process if needed
   kill -9 <PID>
   ```

3. **Stale PID file:**
   ```bash
   # Remove stale PID file
   rm -f anthropic-proxy.pid
   ```

4. **Server not responding:**
   ```bash
   # Check status
   ./status.sh
   # View error logs
   tail -f logs/server_error.log
   # Restart server
   ./restart.sh
   ```

#### Log Analysis

```bash
# View recent standard logs
tail -n 50 logs/server.log

# View recent error logs
tail -n 50 logs/server_error.log

# Follow logs in real-time
tail -f logs/server.log
tail -f logs/server_error.log

# Search for specific errors
grep "ERROR" logs/server_error.log
```

### API Access

Once the server is running, you can access:

- **API Documentation:** http://localhost:5000/docs
- **OpenAPI Schema:** http://localhost:5000/openapi.json
- **Health Check:** http://localhost:5000/

### Security Notes

- The server binds to `0.0.0.0` making it accessible from all network interfaces
- Consider firewall rules for production deployments
- Monitor log files for security events
- Regular backup of configuration files

### Script Dependencies

All scripts are self-contained and use only standard Unix/Linux commands:
- `bash` - Shell interpreter
- `ps` - Process status
- `kill` - Process termination
- `nohup` - Background execution
- `curl` - HTTP requests (status checking)
- `tail` - Log monitoring
- `mkdir` - Directory creation
- `rm` - File removal

No additional packages need to be installed for script functionality.
