# Anthropic Proxy

OpenAI-compatible proxy for z.ai's GLM‑4.5 models with **client-controlled context management**, automatic content-based routing, and real token transparency.

## 🎯 Key Features

### **Client-Controlled Context Management**
- **Real token reporting** - See actual usage vs artificial safety margins
- **Context limit transparency** - Know hard limits and utilization percentages  
- **Emergency-only truncation** - Only acts when upstream API would fail
- **Smart conversation preservation** - Keeps system messages and recent context

### **Content-Based Routing & Scaling**
- **Automatic endpoint selection** - Text → Anthropic, Images → OpenAI
- **Token scaling normalization** - Fixes token counting across different contexts
- **Model variant control** - `glm-4.5`, `glm-4.5-openai`, `glm-4.5-anthropic`
- **Vision support** - Seamless image handling with proper routing

### **z.ai Integration Features**
- **Thinking parameter support** - Automatic `thinking: {"type": "enabled"}` injection for OpenAI endpoints
- **Enhanced upstream logging** - Full request/response payload logging for debugging
- **Configurable thinking mode** - Enable/disable thinking parameter via environment variable

### **Production Ready**
- **Drop-in OpenAI replacement** - Works with Roo, Kilo, Cline, and other tools
- **Structured logging** - Performance monitoring and debugging
- **Comprehensive testing** - 100% success rate across all functionality
- **Docker deployment** - Up and running in 30 seconds

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

# z.ai thinking parameter support (default: true)
# Automatically adds "thinking": {"type": "enabled"} to OpenAI endpoint requests
ENABLE_ZAI_THINKING=true

# Default models for auto-selection
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5v

# Token scaling configuration
ANTHROPIC_EXPECTED_TOKENS=200000
OPENAI_EXPECTED_TOKENS=128000
REAL_TEXT_MODEL_TOKENS=128000
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
- **OpenAI Endpoints**: Expect 128k context (configurable), scale from real model context size
- **Text Models**: Anthropic (200k) ↔ OpenAI (128k) scaling
- **Vision Models**: Real vision context (configurable) ↔ Expected context scaling
- **Configurable Limits**: All context sizes can be customized via environment variables

**Example Token Scaling:**
- Anthropic text → Client: 200k tokens scaled down to 128k (ratio: ~0.64)
- OpenAI vision → Client: 65k tokens scaled up to 128k (ratio: ~1.97)
- OpenAI text → Client: No scaling needed (both 128k)

This ensures your applications see consistent token counts regardless of which upstream service handles the request.

## 🧠 Context Management & Client Transparency

The proxy provides full context visibility and client-controlled management:

### **Real Token Reporting**
Every response includes comprehensive context information:

```json
{
  "choices": [...],
  "usage": {
    "prompt_tokens": 40195,           // OpenAI-compatible  
    "completion_tokens": 100,
    "total_tokens": 40295,
    "real_input_tokens": 40195,       // Actual token count
    "context_limit": 65536,           // Hard limit for endpoint
    "context_utilization": "61.3%",   // Utilization percentage
    "endpoint_type": "vision"         // Which endpoint handled request
  },
  "context_info": {
    "real_input_tokens": 40195,
    "context_hard_limit": 65536,      // True model limit
    "endpoint_type": "vision", 
    "utilization_percent": 61.3,
    "available_tokens": 25341,        // Remaining capacity
    "truncated": false,               // Whether emergency truncation occurred
    "note": "Use these values to manage context and avoid truncation"
  }
}
```

### **Client-Controlled Context**
- **No artificial safety margins** - Use full model capacity (65K/128K tokens)
- **Emergency-only truncation** - Only when upstream API would reject
- **Utilization warnings** - 🟡 >60% warning, 🔴 >80% critical
- **Proactive management** - Clients see limits before hitting them

### **Smart Emergency Truncation** 
When hard limits are exceeded (rare), the proxy:
- **Preserves system messages** - Keeps important context
- **Maintains conversation pairs** - Recent user/assistant exchanges  
- **Full transparency** - Reports what was truncated and why
- **Minimal intervention** - Only removes what's absolutely necessary

### **Context Limits by Endpoint**
- **Vision models** (`glm-4.5` with images): 65,536 tokens
- **Text models** (`glm-4.5` text-only): 128,000 tokens
- **Model variants**: Force specific endpoints with `-openai` or `-anthropic` suffixes

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

### User-Controlled Endpoint Selection
Users can override auto-routing by using model name suffixes:

- **`glm-4.5`** - Auto-routing (default behavior)
- **`glm-4.5-openai`** - Force OpenAI endpoint for all requests
- **`glm-4.5-anthropic`** - Force Anthropic endpoint (text only, images still go to OpenAI)

This behavior applies to both message creation and token counting. The routing happens transparently based on content analysis and user preference.

## Available Models

The proxy exposes model variants for endpoint control:

- **glm-4.5**: Universal model with auto-routing
  - Text requests: Routed to Anthropic endpoint with proper token scaling  
  - Image requests: Automatically routed to OpenAI vision endpoint with proper token scaling
  - Provides consistent interface regardless of content type

- **glm-4.5-openai**: Force OpenAI endpoint
  - All requests (text and vision) use OpenAI endpoint
  - Use when you need OpenAI-specific features or behavior

- **glm-4.5-anthropic**: Force Anthropic endpoint  
  - Text requests use Anthropic endpoint
  - Image requests still automatically route to OpenAI (required for vision)
  - Use when you need Anthropic-specific features for text

**Note**: The proxy automatically uses the appropriate backend model (`glm-4.5` or `glm-4.5v`) and endpoint routing based on request content and user model selection.

## API Endpoints

- `POST /v1/chat/completions` - OpenAI-compatible chat completions
- `GET /v1/models` - List available models  
- `POST /v1/messages/count_tokens` - Count tokens in messages
- `POST /v1/messages` - Direct Anthropic API endpoint (supports streaming and non-streaming)
- `GET /health` - Health check

**Note**: The `/v1/messages` endpoint has been optimized for compatibility with Anthropic's Claude CLI and other clients. It properly handles both streaming (`stream=true`) and non-streaming (`stream=false` or omitted) requests, returning appropriate content types for each mode.

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
python tests/integration/test_direct_model.py

# Run other test categories  
python tests/integration/test_api.py              # Basic API functionality
python tests/integration/test_image_routing.py    # Image model routing
python tests/integration/test_image_processing.py # Image processing endpoints
python simple_test.py                             # Quick functionality check

# Test model variants (recommended after any routing changes)
python tests/integration/test_model_variants.py   # All model variants
```

**Test Coverage**: The test suite validates:
- ✅ Server health and API availability
- ✅ **Model variants for endpoint control** (`glm-4.5`, `glm-4.5-openai`, `glm-4.5-anthropic`) - **Fixed in latest version**
- ✅ Content-based routing (text → Anthropic, images → OpenAI)
- ✅ Token counting with proper scaling
- ✅ Authentication with real API keys
- ✅ All major endpoints (`/v1/models`, `/v1/chat/completions`, `/v1/messages`, `/v1/messages/count_tokens`)
- ✅ **OpenAI endpoint format compatibility** - **Fixed in latest version**

**Recent Fixes (Latest Version)**:
- 🔧 **Fixed OpenAI routing bug**: Model variants like `glm-4.5-openai` now properly strip endpoint suffixes before sending to upstream APIs
- 🔧 **Fixed /v1/messages endpoint**: Now properly handles model variant routing and OpenAI response format conversion
- 🔧 **Enhanced error handling**: Both endpoints now return proper OpenAI-compatible error structures

**Note**: Tests require a valid `SERVER_API_KEY` in your `.env` file to pass authentication.

## Status & Health

Check if the service is running:
```bash
curl http://localhost:5000/health
```

View API documentation: `http://localhost:5000/docs`

Note: This project is maintained and tested. The single-model approach with configurable token scaling provides reliable operation.

## Documentation

### Core Documentation
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference and examples
- **[Development Guide](docs/development/DEVELOPMENT.md)** - Development setup, scripts, and troubleshooting
- **[Documentation Index](docs/README.md)** - Organized guide to all documentation

### Performance & Architecture
- **[Performance Analysis](docs/performance/OPTIMIZATION_SUMMARY.md)** - Current performance status and optimization results
- **[Architecture Guides](docs/architecture/)** - Image routing, connection handling, and system architecture

### For AI Agents
- **[AGENTS.md](AGENTS.md)** - Essential context for AI development on this project
