# Anthropic Proxy

OpenAI-compatible proxy for using z.ai's Anthropic GLM‑4.5 endpoints with developer tools (Roo, Kilo, Cline) — With automatic content-based routing, configurable token scaling, and structured logging.

## Why This Proxy (and what it fixes)

- **Content-Based Routing**: Single model with automatic endpoint selection based on content type
- **Configurable Token Scaling**: Token scaling between different context windows with customizable limits
- **Path to GLM‑4.5**: Access both text and vision models from z.ai via a unified OpenAI-compatible interface
- **Normalized Token Counting**: Fixes token usage counting that some tools misinterpret when pointed directly at z.ai
- **Drop-in Replacement**: Works as OpenAI-compatible endpoint with transparent routing and scaling
- **Vision Support**: Seamless handling of images with automatic endpoint selection and proper token scaling
- **Production Ready**: Structured logging, error handling, and testing coverage

## Quick Start with Docker (Recommended)

Get up and running in under 30 seconds:

```bash
# Clone and start
git clone <repository-url>
cd anthropic-proxy
docker-compose up -d

# That's it! Server runs on http://localhost:5000
```

**No configuration required** - the proxy forwards your API keys automatically.

Tip: Most OpenAI-compatible clients require the base URL to include the path prefix `/v1`.

## Using with OpenAI-compatible Clients

Point your OpenAI provider at this base URL (note the `/v1`):

```
http://localhost:5000/v1
```

## Alternative: Python Setup

```bash
# Clone and setup
git clone <repository-url>
cd anthropic-proxy

# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start server
./start.sh
```

## Configuration (Optional)

The proxy works out-of-the-box by forwarding client API keys. For advanced setups:

```bash
# Create configuration file
cp .env.example .env
# Edit .env with your preferences
```

Key settings:
```bash
# API key for server authentication (optional when FORWARD_CLIENT_KEY=true)
SERVER_API_KEY=your-api-key-here

# Upstream endpoints
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4

# Forward client keys upstream (default: true)
FORWARD_CLIENT_KEY=true

# Default models for auto-selection
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5v

# Token scaling configuration
ANTHROPIC_EXPECTED_TOKENS=200000
OPENAI_EXPECTED_TOKENS=131072
REAL_TEXT_MODEL_TOKENS=131072
REAL_VISION_MODEL_TOKENS=65536
```

## Image Routing & Token Scaling

The proxy automatically handles different model types and context windows:

### Automatic Endpoint Routing
- **Text Models** (`glm-4.5`): Route to Anthropic endpoint → 200k context
- **Vision Models** (`glm-4.5v`): Route to OpenAI endpoint → 64k context  
- **Image Content**: Any request with images routes to OpenAI endpoint

### Token Scaling
The proxy scales token counts based on endpoint expectations and real model contexts:
- **Anthropic Endpoints**: Expect 200k context (configurable), scale to real model context size
- **OpenAI Endpoints**: Expect 131k context (configurable), scale from real model context size
- **Text Models**: Anthropic (200k) ↔ OpenAI (131k) scaling
- **Vision Models**: Real vision context (configurable) ↔ Expected context scaling
- **Configurable Limits**: All context sizes can be customized via environment variables

**Example Token Scaling:**
- Anthropic text → Client: 200k tokens scaled down to 131k (ratio: ~0.656)
- OpenAI vision → Client: 65k tokens scaled up to 131k (ratio: ~2.0)
- OpenAI text → Client: No scaling needed (both 131k)

This ensures your applications see consistent token counts regardless of which upstream service handles the request.

Restart after changes:
```bash
docker-compose restart
```

Note: The proxy forwards API keys from client requests by default. You only need `SERVER_API_KEY` as a fallback.

## Authentication

The proxy supports flexible authentication options:

**When FORWARD_CLIENT_KEY=true (default):**
- Clients should send their own API key via Authorization header or x-api-key
- `SERVER_API_KEY` is optional and used only as fallback when client doesn't send a key
- Recommended for production deployments

**When FORWARD_CLIENT_KEY=false:**
- `SERVER_API_KEY` is required and used for all upstream requests
- Clients don't need to provide API keys
- Useful for controlled environments or testing

Example `.env` configuration:
```bash
# Option 1: Forward client keys (SERVER_API_KEY optional)
FORWARD_CLIENT_KEY=true
SERVER_API_KEY=fallback-key-here  # Optional

# Option 2: Use server key only (SERVER_API_KEY required)
FORWARD_CLIENT_KEY=false  
SERVER_API_KEY=your-zai-api-key-here  # Required
```

## Usage Examples

The proxy runs on `http://localhost:5000` with OpenAI-compatible endpoints at `/v1/*`.

Supported today: Chat Completions (`POST /v1/chat/completions`) and related helpers (models, count tokens). Some OpenAI endpoints may not behave identically; integrations should target chat completions.

### Text Chat
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-anthropic-api-key" \
  -d '{
    "model": "glm-4.5",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### Vision Chat
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-anthropic-api-key" \
  -d '{
    "model": "glm-4.5",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What do you see?"},
        {"type": "image_url", {"image_url": {"url": "data:image/jpeg;base64,..."}}}
      ]
    }],
    "max_tokens": 100
  }'```

**Note**: The proxy exposes `glm-4.5` with smart content-based routing, automatically handling vision requests by routing them to the appropriate endpoint and model behind the scenes.

## How model auto‑switching works

The proxy automatically routes requests based on content analysis:

### Content-Based Routing (`glm-4.5`)
- **Client View**: Single `glm-4.5` model exposed via `/v1/models` endpoint
- **Automatic Routing**: 
  - Text-only requests → Anthropic endpoint with `glm-4.5`
  - Image requests → OpenAI endpoint with `glm-4.5v` (internal)
  - Vision models → OpenAI endpoint with `glm-4.5v` (internal)
- **Token Scaling**: Proper scaling based on endpoint expectations and real context sizes

This behavior applies to both message creation and token counting. The routing happens transparently based on content analysis.

## Available Models

The proxy exposes a single universal model:

- **glm-4.5**: Universal model that handles both text and vision requests
  - Text requests: Routed to Anthropic endpoint with proper token scaling  
  - Image requests: Automatically routed to OpenAI vision endpoint with proper token scaling
  - Provides consistent interface regardless of content type

**Note**: The proxy automatically uses the appropriate backend model (`glm-4.5` or `glm-4.5v`) and endpoint routing based on request content.

## API Endpoints

- `POST /v1/chat/completions` - OpenAI-compatible chat completions
- `GET /v1/models` - List available models  
- `POST /v1/messages/count_tokens` - Count tokens in messages
- `POST /v1/messages` - Direct Anthropic API endpoint
- `GET /health` - Health check

## Docker Management

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart after config changes
docker-compose restart

# Update to latest version
git pull
docker-compose up -d --build
```

## Testing

Run the comprehensive test suite to verify all functionality:

```bash
# Run all tests (requires proxy to be running and .env configured)
python test_direct_model.py

# Run other test categories
python test_api.py              # Basic API functionality
python test_image_routing.py    # Image model routing  
python test_image_processing.py # Image processing endpoints
python simple_test.py           # Quick functionality check
```

**Test Coverage**: The test suite validates:
- ✅ Server health and API availability
- ✅ Single model exposure (`glm-4.5` only)
- ✅ Content-based routing (text → Anthropic, images → OpenAI)
- ✅ Token counting with proper scaling
- ✅ Authentication with real API keys
- ✅ All major endpoints (`/v1/models`, `/v1/chat/completions`, `/v1/messages/count_tokens`)

**Note**: Tests require a valid `SERVER_API_KEY` in your `.env` file to pass authentication.

## Status & Health

Check if the service is running:
```bash
curl http://localhost:5000/health
```

View API documentation: `http://localhost:5000/docs`

Note: This project is maintained and tested. The single-model approach with configurable token scaling provides reliable operation.

## Documentation

- **[API Documentation](API_DOCUMENTATION.md)** - Complete API reference and examples
- **[Development Guide](DEVELOPMENT.md)** - Development setup, scripts, and troubleshooting
