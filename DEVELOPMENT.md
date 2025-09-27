# Development Guide

This guide covers the technical details for developing, deploying, and maintaining the Anthropic Proxy service.

## Prerequisites

- Python 3.8+
- Virtual environment
- Git

## Development Setup

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd anthropic-proxy
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Server Management Scripts

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
./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload
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

## Configuration

### Server Settings
- **Host:** `0.0.0.0` (all interfaces)
- **Port:** `5000`
- **Application:** `main:app`
- **Command:** `./venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 5000`

### Environment Variables

Server configuration is managed through the `.env` file. Complete configuration options:

| Variable | Default | Description |
|----------|---------|-------------|
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

### Example .env File

```bash
# Required: Your API key
SERVER_API_KEY=your-api-key-here

# Optional: Custom upstream URL
UPSTREAM_BASE=https://api.z.ai/api/anthropic

# Optional: Client key forwarding
FORWARD_CLIENT_KEY=true

# Optional: Token counting
FORWARD_COUNT_TO_UPSTREAM=true
COUNT_SHAPE_COMPAT=true

# Optional: Model configuration
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5
OPENAI_MODELS_LIST_JSON=["glm-4.5","glm-4.5v"]
MODEL_MAP_JSON={}

# Optional: Anthropic Beta features
FORCE_ANTHROPIC_BETA=false
DEFAULT_ANTHROPIC_BETA=prompt-caching-2024-07-31
```

## Docker Development

### Building the Image

```bash
# Build the Docker image
docker build -t anthropic-proxy .

# Run with Docker
docker run -d \
  --name anthropic-proxy \
  -p 5000:5000 \
  --env-file .env \
  anthropic-proxy
```

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Development with Docker

```bash
# Build and run in development mode
docker-compose -f docker-compose.dev.yml up --build

# Run with volume mounts for live reloading
docker run -d \
  -p 5000:5000 \
  -v $(pwd):/app \
  --env-file .env \
  anthropic-proxy
```

## Testing

### Running Tests

```bash
# Run the simple test
python simple_test.py

# Run API tests
python test_api.py

# Run image processing tests
python test_image_processing.py
```

### Manual Testing

```bash
# Health check
curl http://localhost:5000/health

# List models
curl http://localhost:5000/v1/models

# Test chat completion
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "glm-4.5",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

## Troubleshooting

### Common Issues

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

5. **Permission denied on scripts:**
   ```bash
   chmod +x *.sh
   ```

6. **Dependencies not found:**
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

### Log Analysis

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

# Monitor API calls
grep "POST\|GET" logs/server.log

# Check authentication issues
grep "401\|403" logs/server_error.log
```

### Debug Mode

Run the server in debug mode for development:

```bash
# With debug logging
export PYTHONPATH=.
python -m uvicorn main:app --host 0.0.0.0 --port 5000 --reload --log-level debug

# Or modify the script temporarily
DEBUG=1 ./run.sh
```

### Performance Monitoring

```bash
# Monitor system resources
htop
# or
top

# Monitor network connections
netstat -tulpn | grep :5000

# Check disk usage for logs
du -sh logs/

# Monitor memory usage
ps aux | grep python
```

## Architecture

### Components

- **FastAPI Application** (`main.py`): Core proxy server
- **HTTP Client** (`httpx`): Upstream API communication
- **SSE Support** (`httpx-sse`): Server-sent events for streaming
- **Token Encoding** (`tiktoken`): Token counting utilities
- **Environment Config** (`python-dotenv`): Configuration management

### Request Flow

1. Client sends OpenAI-format request to proxy
2. Proxy validates and transforms request to Anthropic format
3. Proxy forwards request to upstream Anthropic API
4. Proxy receives response and transforms back to OpenAI format
5. Proxy returns response to client

### Key Features

- **Model Auto-switching**: Automatically selects vision model for image requests
- **Token Counting**: Accurate token estimation with upstream validation
- **Error Handling**: Robust error handling with fallback mechanisms
- **Streaming Support**: Server-sent events for real-time responses
- **Authentication**: Flexible API key handling and forwarding

### Anthropic endpoints and model mapping

In addition to the OpenAI-compatible chat completions, the proxy exposes Anthropic-compatible endpoints for tools that speak Anthropic natively:

- `POST /v1/messages`
- `POST /v1/messages/count_tokens`
- `GET /v1/models`

Model aliasing is controlled via `MODEL_MAP_JSON` (see Configuration above). The proxy rewrites incoming model names to your configured upstream identifiers and still applies automatic text/vision switching when images are present (based on `AUTOTEXT_MODEL`/`AUTOVISION_MODEL`). For quick-start examples and client usage notes, see the "Anthropic endpoint exposure and model mapping" section in README.

## Security Considerations

### Network Security

- The server binds to `0.0.0.0` making it accessible from all network interfaces
- Consider firewall rules for production deployments
- Use reverse proxy (nginx/Apache) for HTTPS termination
- Implement rate limiting for production use

### API Key Security

- Never commit API keys to version control
- Use environment variables for sensitive configuration
- Rotate API keys regularly
- Monitor log files for security events
- Consider using vault systems for key management

### Logging Security

- Logs may contain sensitive information
- Regular log rotation and cleanup
- Secure log file permissions (600 or 640)
- Consider log aggregation systems for production

## Production Deployment

### Recommended Setup

```bash
# Use a process manager like systemd
sudo cp anthropic-proxy.service /etc/systemd/system/
sudo systemctl enable anthropic-proxy
sudo systemctl start anthropic-proxy

# Or use Docker with restart policies
docker run -d \
  --name anthropic-proxy \
  --restart unless-stopped \
  -p 5000:5000 \
  --env-file .env \
  anthropic-proxy
```

### System Requirements

- **CPU**: 2+ cores recommended
- **Memory**: 512MB minimum, 1GB+ recommended
- **Storage**: 100MB for application, additional for logs
- **Network**: Reliable internet connection for upstream API

### Monitoring

```bash
# Health check endpoint
curl http://localhost:5000/health

# Process monitoring
ps aux | grep uvicorn

# Log monitoring
tail -f logs/server.log | grep ERROR

# Disk space monitoring
df -h
du -sh logs/
```

## Script Dependencies

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

## Contributing

### Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Add docstrings for functions and classes
- Keep functions focused and small

### Testing

- Add tests for new features
- Ensure existing tests pass
- Test both success and error scenarios
- Include integration tests for API endpoints

### Documentation

- Update this guide for new features
- Update API documentation for endpoint changes
- Add examples for new functionality
- Keep README focused on end users