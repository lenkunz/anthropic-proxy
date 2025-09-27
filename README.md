# Anthropic Proxy

OpenAI-compatible proxy for using z.ai's Anthropic GLM‑4.5 endpoints with developer tools (Roo, Kilo, Cline) — May faster than the Z.AI OpenAI compatible route, with adapted token usage mapping.

## Why This Proxy (and what it fixes)

- Path to Anthropic GLM‑4.5 from z.ai via OpenAI compaitble completion route.
- Normalizes token usage counting that some tools misinterpret when pointed directly at z.ai anthropic compatible endpoint (context size display and budgeting)
- Works as a drop-in OpenAI-compatible for completion endpoint. (Also implements Anthropic endspoint with auto model mapping so it can be use with Anthropic provider by excluding path `/v1`)

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

# Forward client keys upstream (default: true)
# Keep enabled for most setups
FORWARD_CLIENT_KEY=true

# Default models (used when request omits `model`)
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5
```

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

Note: If `glm-4.5v` returns access or model errors, your plan may not include vision. Use `glm-4.5` or upgrade your plan.

## How model auto‑switching works (AUTOVISION_MODEL)


The proxy can auto-select a model based on whether an image is present in the request body:


- If the request has no `model` field:
  - Uses `AUTOVISION_MODEL` when the payload contains images
  - Uses `AUTOTEXT_MODEL` otherwise
- If the request explicitly sets a model:
  - With images: `glm-4.5` (AUTOTEXT_MODEL) is transparently switched to `glm-4.5v` (AUTOVISION_MODEL)
  - Without images: `glm-4.5v` (AUTOVISION_MODEL) is transparently switched to `glm-4.5` (AUTOTEXT_MODEL) <-- (4.5v might not work, for stability, uses 4.5 instead.)

This behavior applies to both message creation and token counting. You can customize the defaults via `.env`:

```bash
AUTOTEXT_MODEL=glm-4.5
AUTOVISION_MODEL=glm-4.5
```

Defaults: Both text and vision defaults are `glm-4.5` for correct context sizing. If your plan includes vision and you want automatic vision routing, set `AUTOVISION_MODEL=glm-4.5v`.

Note: Vision (4.5v) availability depends on your plan. If unavailable, leave `AUTOVISION_MODEL=glm-4.5` so image requests do not switch to a non-allowed model.

### Vision Chat
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-anthropic-api-key" \
  -d '{
    "model": "glm-4.5v",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
      ]
    }],
    "max_tokens": 100
  }'
```

## Available Models

- **glm-4.5**: Advanced text model (128K context)
- **glm-4.5v**: Vision model with image understanding (65K context)
  - Note: 4.5v may not be available on Anthropic coding plans. If you encounter access/model errors, switch to `glm-4.5` or verify your plan includes vision.

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
