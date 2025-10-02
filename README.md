# Anthropic Proxy

A powerful proxy server that provides OpenAI-compatible API endpoints while routing requests to z.ai's GLM-4.6 models with intelligent content-based routing and advanced context management.

## 🚀 Features

- **OpenAI Compatibility**: Drop-in replacement for OpenAI API endpoints (`/v1/chat/completions`, `/v1/models`)
- **Anthropic Compatibility**: Native Anthropic API endpoints (`/v1/messages`, `/v1/messages/count_tokens`)
- **Intelligent Routing**: Automatic content-based routing (text → Anthropic, images → OpenAI)
- **Multi-Server Support**: Switch between CN (https://open.bigmodel.cn) and international (https://api.z.ai) endpoints
- **Advanced Context Management**: AI-powered message condensation and token optimization
- **Rich CLI Tool**: Comprehensive command-line interface for management and monitoring
- **Real-time Statistics**: Live usage monitoring and performance tracking
- **Environment Deduplication**: Automatic removal of redundant environment details
- **Image Age Management**: Smart handling of old images with contextual descriptions
- **Docker Support**: Easy deployment with Docker Compose

## 📋 Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd anthropic-proxy

# Configure your API key
cp .env.example .env
# Edit .env and add your SERVER_API_KEY

# Start the proxy
docker compose up -d --build

# Check status
curl http://localhost:5000/health
```

### Option 2: Using the CLI Tool

```bash
# Setup CLI environment
./setup-cli.sh

# Activate CLI environment
source venv/bin/activate-proxy

# Start the proxy with CLI
proxy-cli start

# View status
proxy-cli status

# Launch TUI (Terminal User Interface)
proxy-cli tui
```

### Option 3: Direct Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start the proxy
python src/main.py
```

## 🎮 CLI Tool Usage

The Anthropic Proxy CLI provides comprehensive management capabilities:

### Basic Commands

```bash
# Show proxy status
proxy-cli status

# Start proxy server
proxy-cli start

# Start with specific server
proxy-cli start --server cn
proxy-cli start --server international

# Stop proxy server
proxy-cli stop

# Switch between servers
proxy-cli switch cn
proxy-cli switch international

# View usage statistics
proxy-cli stats

# Show real-time statistics
proxy-cli stats --realtime

# List available servers
proxy-cli servers

# Show configuration
proxy-cli config
```

### Advanced Features

#### Terminal User Interface (TUI)

```bash
# Launch interactive TUI with real-time monitoring
proxy-cli tui

# Launch interactive menu
proxy-cli interactive
```

The TUI provides:
- **Real-time Status**: Live proxy status and statistics
- **Server Management**: Quick server switching
- **Performance Monitoring**: Request rates, response times, success rates
- **Interactive Controls**: Keyboard shortcuts for common actions

#### Configuration Management

```bash
# Show all configuration
proxy-cli config --list

# Get specific setting
proxy-cli config --get current_server

# Set configuration
proxy-cli config --set log_level DEBUG
proxy-cli config --set port 8080
```

#### Statistics and Analytics

```bash
# Show last 24 hours statistics
proxy-cli stats

# Show custom time range
proxy-cli stats --hours 168  # Last 7 days

# Real-time monitoring
proxy-cli stats --realtime
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with your configuration:

```bash
# Core Configuration
SERVER_API_KEY=your_z_ai_api_key
HOST=0.0.0.0
PORT=5000

# Server Endpoints
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4

# Model Configuration
AUTOTEXT_MODEL=glm-4.6
AUTOVISION_MODEL=glm-4.6v
TEXT_ENDPOINT_PREFERENCE=auto

# Feature Flags
ENABLE_ZAI_THINKING=true
ENABLE_ACCURATE_TOKEN_COUNTING=true
ENABLE_ENVIRONMENT_DEDUPLICATION=true
ENABLE_MESSAGE_CONDENSATION=true

# Image Management
IMAGE_AGE_THRESHOLD=3
GENERATE_IMAGE_DESCRIPTIONS=true
IMAGE_DESCRIPTION_MAX_TOKENS=200

# Performance Settings
REQUEST_TIMEOUT=300
STREAM_TIMEOUT=300
CONNECT_TIMEOUT=10

# Logging
LOG_LEVEL=INFO
ENABLE_STRUCTURED_LOGGING=true
```

### CLI Configuration

The CLI stores configuration in `~/.anthropic-proxy/`:

- `config.yaml` - Main CLI settings
- `servers.yaml` - Server endpoint configurations  
- `stats/` - Usage statistics storage

#### Server Configuration

Edit `~/.anthropic-proxy/servers.yaml`:

```yaml
cn:
  name: "cn"
  endpoint: "https://open.bigmodel.cn"
  region: "China"
  api_key: "your-cn-api-key"
  latency_ms: 150.0

international:
  name: "international"
  endpoint: "https://api.z.ai"
  region: "International"
  api_key: "your-international-api-key"
  latency_ms: 80.0
```

## 📊 API Endpoints

### OpenAI Compatible Endpoints

#### `POST /v1/chat/completions`

OpenAI-compatible chat completions endpoint with automatic routing.

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "glm-4.6",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 1000,
    "temperature": 0.7
  }'
```

#### `GET /v1/models`

List available models:

```bash
curl http://localhost:5000/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Anthropic Compatible Endpoints

#### `POST /v1/messages`

Native Anthropic messages endpoint:

```bash
curl -X POST http://localhost:5000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "model": "glm-4.6",
    "max_tokens": 1000,
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

#### `POST /v1/messages/count_tokens`

Count tokens in messages:

```bash
curl -X POST http://localhost:5000/v1/messages/count_tokens \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "model": "glm-4.6",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

### Health Check

#### `GET /health`

Basic health check endpoint:

```bash
curl http://localhost:5000/health
```

## 🔄 Model Variants and Routing

The proxy supports multiple model variants for endpoint control:

- **`glm-4.6`** (default): Auto-routing based on content type
  - Text requests → Anthropic endpoint
  - Image requests → OpenAI endpoint

- **`glm-4.6-openai`**: Force OpenAI endpoint for all requests

- **`glm-4.6-anthropic`**: Force Anthropic endpoint for text, OpenAI for images

### Smart Routing Logic

1. **Image Detection**: Automatically detects image content
2. **Model Selection**: Routes based on model variant suffix
3. **Auto-switching**: Text uses Anthropic, images use OpenAI
4. **Performance Optimization**: Minimizes latency and maximizes throughput

## 🖼️ Image Handling

### Smart Image Management

- **Automatic Detection**: Identifies image content in requests
- **Age-based Processing**: Removes old images after threshold (default: 3 messages)
- **AI Descriptions**: Generates contextual descriptions for removed images
- **File-based Caching**: Persistent cache for image descriptions
- **Dynamic Token Calculation**: Accurate token counting for images

### Image Processing Flow

1. **Detection**: Automatically finds images in message history
2. **Age Analysis**: Checks if images are older than threshold
3. **Description Generation**: Uses GLM-4.5v to create descriptions
4. **Cache Storage**: Saves descriptions in file-based cache
5. **Context Replacement**: Replaces old images with descriptive text

## 📈 Performance Features

### Token Optimization

- **Accurate Counting**: tiktoken-based precise token calculation
- **Environment Deduplication**: Removes redundant environment details
- **Context Management**: AI-powered message condensation
- **Real-time Scaling**: Dynamic token scaling for different endpoints

### Caching and Performance

- **File-based Cache**: Persistent caching for image descriptions
- **Async Operations**: Non-blocking cache operations
- **Connection Pooling**: HTTP connection reuse
- **Log Rotation**: Automatic log management and compression

## 🐳 Docker Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  anthropic-proxy:
    build: .
    ports:
      - "5000:5000"
    environment:
      - SERVER_API_KEY=${SERVER_API_KEY}
      - HOST=0.0.0.0
      - PORT=5000
    volumes:
      - ./logs:/app/logs
      - ./cache:/app/cache
    restart: unless-stopped
```

### Docker Commands

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f anthropic-proxy

# Stop and remove
docker compose down

# Rebuild without cache
docker compose down && docker compose build --no-cache && docker compose up -d
```

## 📚 Monitoring and Logging

### Log Management

- **Structured Logging**: JSON-formatted logs with request tracking
- **Log Rotation**: Automatic rotation and compression
- **Performance Logging**: Request timing and performance metrics
- **Upstream Logging**: Complete upstream request/response logging

### Statistics Collection

- **Request Metrics**: Count, success rate, response times
- **Token Usage**: Input/output tokens, costs
- **Server Performance**: Per-server statistics
- **Real-time Monitoring**: Live dashboard via CLI

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd anthropic-proxy

# Setup CLI
./setup-cli.sh

# Activate environment
source venv/bin/activate-proxy

# Run tests
pytest tests/

# Start development server
proxy-cli start --watch
```

### Project Structure

```
anthropic-proxy/
├── src/                    # Source code
│   ├── main.py            # FastAPI application
│   ├── config/            # Configuration modules
│   ├── logging/           # Logging system
│   └── ...
├── cli/                   # CLI tool
│   ├── main.py            # CLI entry point
│   ├── tui.py             # Terminal UI
│   ├── config.py          # Configuration management
│   ├── stats.py           # Statistics collection
│   ├── proxy.py           # Proxy management
│   └── utils.py           # Utility functions
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── api/               # API tests
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── logs/                  # Log files
├── cache/                 # Cache directory
└── docker-compose.yml     # Docker configuration
```

## 🔍 Troubleshooting

### Common Issues

1. **"Proxy is not running"**
   ```bash
   proxy-cli status
   proxy-cli start
   ```

2. **"Cannot connect to server"**
   ```bash
   proxy-cli servers
   proxy-cli config --get current_server
   ```

3. **"API key not found"**
   ```bash
   proxy-cli config --list
   # Edit ~/.anthropic-proxy/servers.yaml
   ```

4. **Docker issues**
   ```bash
   docker compose down
   docker compose up -d --build
   docker compose logs -f anthropic-proxy
   ```

### Debug Mode

Enable debug logging:

```bash
proxy-cli config --set log_level DEBUG
proxy-cli start
```

Or set environment variable:

```bash
export DEBUG=true
python src/main.py
```

## 📖 Documentation

- **[CLI Documentation](CLI_DOCUMENTATION.md)** - Comprehensive CLI guide
- **[API Documentation](API_DOCUMENTATION.md)** - API reference
- **[Development Guide](DEVELOPMENT.md)** - Development setup
- **[Architecture Guide](AGENTS.md)** - System architecture

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- **z.ai GLM-4.6** - The underlying model service
- **OpenAI API** - Compatible API specification
- **Anthropic API** - Native API support

---

**Built with ❤️ for the Anthropic Proxy community**