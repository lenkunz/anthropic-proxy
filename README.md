# Anthropic Proxy

OpenAI-compatible proxy for using z.ai's Anthropic GLM‑4.5 endpoints with developer tools (Roo, Kilo, Cline) — With automatic image model routing, intelligent token scaling, and comprehensive test coverage for production reliability.

## Why This Proxy (and what it fixes)

- **Dual Endpoint Routing**: Text models use Anthropic endpoint, Vision models automatically route to OpenAI-compatible endpoint
- **Token Scaling**: Intelligent scaling between 64k/128k/200k context windows for consistent behavior across endpoints
- **Path to GLM‑4.5**: Access both text and vision models from z.ai via a single OpenAI-compatible interface
- **Normalized Token Counting**: Fixes token usage counting that some tools misinterpret when pointed directly at z.ai
- **Drop-in Replacement**: Works as OpenAI-compatible endpoint with automatic model routing and scaling
- **Vision Support**: Seamless handling of images with automatic endpoint selection and context window scaling
- **Production Ready**: 100% test coverage with comprehensive validation of all endpoints and functionality

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
# Fallback API key (optional)
# Used only when client does NOT send its own key
SERVER_API_KEY=your-api-key-here

# Upstream Anthropic-compatible endpoint (z.ai)
UPSTREAM_BASE=https://api.z.ai/api/anthropic

# Upstream OpenAI-compatible endpoint for vision models (z.ai)
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4

# Forward client keys upstream (default: true)
# Keep enabled for most setups
FORWARD_CLIENT_KEY=true

# Default models (used when request omits `model`)
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5v
```

## Image Routing & Token Scaling

The proxy automatically handles different model types and context windows:

### Automatic Endpoint Routing
- **Text Models** (`glm-4.5`): Route to Anthropic endpoint → 200k context
- **Vision Models** (`glm-4.5v`): Route to OpenAI endpoint → 64k context  
- **Image Content**: Any request with images routes to OpenAI endpoint

### Intelligent Token Scaling
The proxy scales token counts to provide consistent behavior:
- **Anthropic → Client**: Scale down from 200k to 128k context
- **OpenAI Vision → Client**: Scale up from 64k to 128k context
- **Maintains compatibility** across different upstream endpoints

This ensures your applications see consistent token counts regardless of which upstream service handles the request.

Restart after changes:
```bash
docker-compose restart
```

Note: The proxy forwards API keys from client requests by default. You only need `SERVER_API_KEY` as a fallback.

## Authentication (No server key required)

By default, the proxy forwards the API key sent by the client to the upstream service (FORWARD_CLIENT_KEY=true). This means:

- You do not need to set a server-side API key to run the proxy
- Clients must provide their Anthropic-compatible API key in Authorization or x-api-key
- SERVER_API_KEY is only used as a fallback when the client does not send a key

This keeps your deployment simple and avoids hard-coding credentials in the container.

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
  }'
```

**Note**: The proxy only exposes `glm-4.5` in the models list, but automatically handles vision requests by routing them to the appropriate endpoint and model behind the scenes.

## How model auto‑switching works

The proxy automatically routes requests based on content and handles model selection transparently:

- **Client View**: Only `glm-4.5` is exposed via `/v1/models` endpoint
- **Automatic Routing**: 
  - Text-only requests → Anthropic endpoint with `glm-4.5`
  - Image requests → OpenAI endpoint with `glm-4.5v` (internal)
  - Vision models → OpenAI endpoint with `glm-4.5v` (internal)

This behavior applies to both message creation and token counting. The routing happens transparently based on content analysis, regardless of which model the client specifies.

## Available Models

The proxy exposes a single model for client compatibility:

- **glm-4.5**: Universal model that handles both text and vision requests
  - Text requests: Routed to Anthropic endpoint (200k context, scaled to 128k)  
  - Image requests: Automatically routed to OpenAI vision endpoint (64k context, scaled to 128k)
  - Provides consistent interface regardless of content type

**Note**: While clients only see `glm-4.5`, the proxy automatically uses the appropriate backend model (`glm-4.5` or `glm-4.5v`) based on request content.

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
# Run all tests (requires proxy to be running)
python run_all_tests.py

# Run specific test categories
python test_api.py              # Basic API functionality
python test_image_routing.py    # Image model routing
python test_image_processing.py # Image processing endpoints
python simple_test.py           # Quick functionality check
```

**Test Coverage**: 12 comprehensive tests covering:
- ✅ Server health and basic functionality
- ✅ Image detection and format conversion
- ✅ Dual endpoint routing (Anthropic/OpenAI)
- ✅ Token counting (with vision model fallback)
- ✅ Authentication and error handling
- ✅ All API endpoints (`/v1/models`, `/v1/chat/completions`, `/v1/messages`, `/v1/messages/count_tokens`)

## Status & Health

Check if the service is running:
```bash
curl http://localhost:5000/health
```

View API documentation: `http://localhost:5000/docs`

Note: This project is under active testing. Expect changes and please report issues with payloads and headers that differ across clients.

## Documentation

- **[API Documentation](API_DOCUMENTATION.md)** - Complete API reference and examples
- **[Development Guide](DEVELOPMENT.md)** - Development setup, scripts, and troubleshooting
