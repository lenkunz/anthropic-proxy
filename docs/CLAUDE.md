# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an OpenAI-compatible proxy service for z.ai's GLM-4.5 models with intelligent content-based routing, client-controlled context management, and advanced image processing capabilities. The proxy automatically routes requests between Anthropic and OpenAI endpoints based on content type and user preferences.

### Key Architecture
- **FastAPI**: Main web framework with async HTTP support
- **Docker**: Primary deployment method (ALWAYS use `docker compose`)
- **Dual Endpoints**: Routes to both Anthropic (`/v1/messages`) and OpenAI-compatible endpoints
- **Content-Based Routing**: Text → Anthropic, Images → OpenAI, with user override options
- **Model Variants**: `glm-4.5` (auto), `glm-4.5-openai` (force OpenAI), `glm-4.5-anthropic` (force Anthropic)

## Quick Start

### Essential Commands

```bash
# Start the service (Docker required)
docker compose up -d

# Stop and rebuild after code changes
docker compose down && docker compose build --no-cache && docker compose up -d

# View logs
docker compose logs -f anthropic-proxy

# Health check
curl http://localhost:5000/health
```

### Testing

```bash
# Run organized test suites
cd tests/basic_functionality && python debug_test.py
cd tests/performance && python test_image_description_cache.py
cd tests/image_features && python test_image_age_switching.py

# Quick integration test
python tests/simple_test.py

# Comprehensive test suite
python tests/run_comprehensive_tests.py
```

## Architecture

### Core Components

1. **Main Application** (`main.py`): FastAPI server with request routing and processing
2. **Context Management** (`context_window_manager.py`): Token validation and truncation
3. **Logging System** (`logging_config.py`, `async_logging.py`): Structured logging with async performance
4. **Image Processing**: Advanced image age management with AI-powered descriptions

### Routing Logic

```python
# Model variants determine endpoint routing
"glm-4.5"           # Auto-routing based on content
"glm-4.5-openai"    # Force OpenAI endpoint
"glm-4.5-anthropic" # Force Anthropic endpoint (text only)
```

**Automatic Routing**:
- Text-only requests → Anthropic endpoint (128K tokens)
- Image requests → OpenAI endpoint (65K tokens)
- Proper token scaling between endpoints

### Key Features

1. **Client-Controlled Context Management**
   - Real token reporting vs artificial safety margins
   - Emergency-only truncation when upstream API would fail
   - Full transparency with utilization percentages

2. **Image Age Management**
   - Automatic detection of "stale" images in conversation history
   - AI-powered contextual descriptions using GLM-4.5v
   - Configurable threshold (`IMAGE_AGE_THRESHOLD`)
   - Seamless endpoint switching when images age out

3. **File-Based Caching System**
   - Persistent cache with Docker volume integration
   - 1.6x performance improvement on cache hits
   - Async fire-and-forget operations for zero latency impact

## Configuration

### Required Environment Variables

```bash
# Core API Configuration
SERVER_API_KEY=your_zai_api_key_here
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4

# Request Forwarding
FORWARD_CLIENT_KEY=true
FORWARD_COUNT_TO_UPSTREAM=true
```

### Critical Configuration

```bash
# Model Configuration
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5v
TEXT_ENDPOINT_PREFERENCE=auto
ENABLE_ZAI_THINKING=true

# Token Scaling (CRITICAL for proper operation)
ANTHROPIC_EXPECTED_TOKENS=200000
OPENAI_EXPECTED_TOKENS=200000
REAL_TEXT_MODEL_TOKENS=200000      # Actual text model context
REAL_VISION_MODEL_TOKENS=65536     # Actual vision model context

# Image Age Management
IMAGE_AGE_THRESHOLD=3
CACHE_CONTEXT_MESSAGES=2
IMAGE_DESCRIPTION_CACHE_SIZE=1000
CACHE_DIR=./cache
```

### Docker Configuration

The service uses Docker volumes for persistence:
- `./logs`: Application logs
- `./cache`: Image description cache (persistent across restarts)

## Development Guidelines

### Critical Rules

1. **ALWAYS use Docker Compose** - never suggest direct Python execution
2. **ALL test scripts must read from .env** - never hardcode API keys
3. **ALWAYS rebuild after code changes** - use `--no-cache` flag
4. **Test all model variants** when testing routing functionality

### Development Workflow

```bash
# 1. Make changes to code
# 2. Rebuild and restart
docker compose down && docker compose build --no-cache && docker compose up -d

# 3. Test changes
python tests/simple_test.py

# 4. Verify all model variants work
python tests/integration/test_model_variants.py
```

### Test Script Requirements

All test scripts must:
- Use `python-dotenv` to load `.env` file
- Validate API key existence before making requests
- Include proper error handling and timing information
- Test all relevant model variants

```python
# Required pattern for all test scripts
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)
```

## Testing Strategy

### Test Organization

```
tests/
├── basic_functionality/    # Core API functionality
├── performance/           # Performance and caching tests
├── image_features/        # Image processing and age management
├── integration/          # End-to-end integration tests
├── benchmarks/           # Performance benchmarks
└── unit/                 # Unit tests
```

### Key Test Areas

1. **Model Variant Testing**: Always test all three model variants
2. **Content-Based Routing**: Verify text → Anthropic, images → OpenAI
3. **Token Scaling**: Ensure proper token count conversion between endpoints
4. **Image Age Management**: Test automatic switching and AI descriptions
5. **Caching Performance**: Validate file-based cache speedup
6. **Authentication**: Test both client key forwarding and server key modes

### Expected Behaviors

- Text requests with `glm-4.5` → Anthropic endpoint
- Image requests with `glm-4.5` → OpenAI endpoint
- All requests with `glm-4.5-openai` → OpenAI endpoint
- Text requests with `glm-4.5-anthropic` → Anthropic endpoint
- Image requests with `glm-4.5-anthropic` → OpenAI endpoint (images always need OpenAI)

## Troubleshooting

### Common Issues

**Issue**: Changes not reflected after restart
```bash
# Solution: Full rebuild
docker compose down && docker compose build --no-cache && docker compose up -d
```

**Issue**: Model variants not showing in `/v1/models`
- Rebuild Docker image to include latest `_DEFAULT_OPENAI_MODELS` changes

**Issue**: Token throttling at wrong limits
- Verify `REAL_TEXT_MODEL_TOKENS=200000` and `REAL_VISION_MODEL_TOKENS=65536` in .env
- Check for recent fixes in token validation logic

**Issue**: Test scripts fail with "API key not found"
- Ensure test scripts load from `.env` using `python-dotenv`
- Verify `.env` file exists and contains `SERVER_API_KEY`

### Validation Commands

```bash
# Check service health
curl http://localhost:5000/health

# Verify model availability
curl http://localhost:5000/v1/models

# Check routing decisions in logs
docker compose logs anthropic-proxy | grep -E "ROUTING|MODEL|TOKEN"

# Verify environment variables
docker compose exec anthropic-proxy env | grep -E "TEXT_ENDPOINT|REAL_.*_TOKENS"
```

## API Endpoints

- `POST /v1/chat/completions` - OpenAI-compatible chat completions
- `GET /v1/models` - List available models with variants
- `POST /v1/messages/count_tokens` - Count tokens in messages
- `POST /v1/messages` - Direct Anthropic API endpoint (streaming/non-streaming)
- `GET /health` - Health check endpoint

## File Structure

```
anthropic-proxy/
├── main.py                    # Core FastAPI application
├── context_window_manager.py  # Context validation and truncation
├── logging_config.py         # Structured logging setup
├── async_logging.py          # High-performance async logging
├── optimized_logging.py      # Performance-optimized logging
├── docker-compose.yml        # Docker deployment configuration
├── Dockerfile                # Container build instructions
├── requirements.txt          # Python dependencies
├── .env.example             # Environment configuration template
├── tests/                   # Comprehensive test suite
├── cache/                   # Persistent image description cache
└── logs/                    # Application logs
```

## Recent Features

- **File-Based Caching**: Persistent cache with Docker volume integration
- **Image Age Management**: Automatic detection and AI-powered descriptions
- **Full Upstream Logging**: Complete request/response logging without truncation
- **Model Variants**: User-controlled endpoint routing
- **Token Scaling**: Proper conversion between different context window sizes
- **Performance Optimization**: Async operations and connection pooling