# Image Model Routing & Token Scaling

## Overview

The anthropic-proxy now automatically routes image/vision model requests to an OpenAI-compatible endpoint instead of the Anthropic endpoint. This allows the proxy to handle vision models that are only available through OpenAI-compatible APIs. Additionally, the proxy implements intelligent token scaling to handle different context window sizes between endpoints.

## Configuration

### Environment Variables

Add the following environment variable to configure the OpenAI-compatible endpoint:

```bash
# OpenAI-compatible endpoint for image/vision models
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4
```

The existing Anthropic endpoint configuration remains unchanged:

```bash
# Anthropic endpoint for text-only models (existing)
UPSTREAM_BASE=https://api.z.ai/api/anthropic
```

## Routing Logic

The proxy automatically determines which upstream endpoint to use based on:

### 1. **Model Type**
- **Vision Model**: If the model is `glm-4.6v` (or whatever is set in `AUTOVISION_MODEL`), route to OpenAI endpoint
- **Text Model**: All other models route to Anthropic endpoint

### 2. **Content Analysis** 
- **Has Images**: If the request contains image content (regardless of model), route to OpenAI endpoint
- **Text Only**: Text-only requests route to Anthropic endpoint

## Token Scaling System

The proxy implements comprehensive bidirectional token scaling to handle different context window sizes:

### Context Window Sizes
- **Anthropic Text Models**: 200,000 tokens
- **OpenAI Text Models**: 131,072 tokens (128k)
- **OpenAI Vision Models**: 65,535 tokens (64k)

### Scaling Rules
1. **OpenAI ↔ Anthropic** (text): Scale 131,072 ↔ 200,000
2. **OpenAI ↔ OpenAI** (vision): Scale 65,535 ↔ 131,072 (auto-switch scenario)
3. **Anthropic ↔ Anthropic** (text): No scaling applied
4. **Anthropic ↔ OpenAI** (vision): Scale 200,000 ↔ 65,535

## Examples

### Text-Only Request → Anthropic Endpoint
```json
{
  "model": "glm-4.6",
  "messages": [{"role": "user", "content": "Hello"}]
}
```
Routes to: `https://api.z.ai/api/anthropic/v1/messages`
Token scaling: Uses Anthropic's 200k context window

### Image Request → OpenAI Endpoint
```json
{
  "model": "glm-4.6",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "What do you see?"},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]
  }]
}
```
Routes to: `https://api.z.ai/api/coding/paas/v4/chat/completions`
Token scaling: Uses OpenAI's 64k vision context window (scaled to 128k for client compatibility)

### Vision Model → OpenAI Endpoint
```json
{
  "model": "glm-4.6v",
  "messages": [{"role": "user", "content": "Hello"}]
}
```
Routes to: `https://api.z.ai/api/coding/paas/v4/chat/completions`
Token scaling: Uses OpenAI's 64k vision context window (scaled to 128k for client compatibility)

## Technical Details

### Endpoint Handling

#### OpenAI-Compatible Endpoint
- **Request Format**: Uses original OpenAI request format (no conversion)
- **Response Format**: Forwards OpenAI response as-is (no conversion)
- **Headers**: Uses OpenAI-compatible headers (`authorization: Bearer <token>`)
- **Streaming**: Forwards SSE events directly from upstream

#### Anthropic Endpoint  
- **Request Format**: Converts OpenAI format to Anthropic format
- **Response Format**: Converts Anthropic response to OpenAI format
- **Headers**: Uses Anthropic headers (`x-api-key`, `anthropic-version`)
- **Streaming**: Converts Anthropic SSE to OpenAI SSE format

### Authentication

The proxy handles authentication automatically:

- **Client API Key**: Forwarded to appropriate upstream endpoint
- **Server API Key**: Used as fallback if client key not provided
- **Header Format**: Automatically adjusted for each endpoint type

## Debug Logging

Enable debug logging to see routing decisions:

```bash
DEBUG=true
```

Debug output shows which endpoint is selected:
```
[DEBUG] Routing to OpenAI endpoint for model glm-4.6v (has_images: True)
[DEBUG] Routing to Anthropic endpoint for model glm-4.6
```

## Testing

Run the routing test script to verify configuration:

```bash
python3 tests/integration/test_image_routing.py
```

This tests:
1. Text-only requests → Anthropic endpoint
2. Image requests → OpenAI endpoint  
3. Vision model requests → OpenAI endpoint

## Migration

### From Previous Version

No changes required for existing clients. The routing is transparent:

- **Existing text requests**: Continue working unchanged
- **New image requests**: Automatically routed to correct endpoint
- **API compatibility**: Full backward compatibility maintained

### Configuration Update

Just add the new environment variable:

```bash
# Add this line to your .env file
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4
```

## Token Scaling Details

### Automatic Scaling
The proxy automatically scales token counts in responses based on:
- **Upstream endpoint**: Which service provided the response
- **Downstream format**: OpenAI format expected by clients
- **Model type**: Text vs. Vision model differences
- **Content type**: Whether images are present in the request

### Scaling Examples

#### Anthropic Text → Client
- Upstream: 200,000 token context
- Scaled to: 131,072 tokens (OpenAI 128k standard)
- **Scaling factor**: 0.656

#### OpenAI Vision → Client  
- Upstream: 65,535 token context (vision model)
- Scaled to: 131,072 tokens (client expects 128k)
- **Scaling factor**: 2.000

#### OpenAI Text → Anthropic → Client
- Request: 131,072 token context
- Anthropic processing: 200,000 token context
- Response scaled back to: 131,072 tokens
- **Maintains consistency** across routing scenarios

## API Compatibility

The proxy exposes a single model (`glm-4.6`) via the `/v1/models` endpoint for client compatibility. However, the routing system automatically handles different model types behind the scenes:

- **Exposed Model**: `glm-4.6` (clients see this in model lists)
- **Internal Routing**: Automatic switching to appropriate models and endpoints based on content
- **Vision Support**: Image requests automatically use vision capabilities regardless of specified model

## Supported Image Formats

The proxy supports standard OpenAI image formats:

### Data URLs
```json
{
  "type": "image_url",
  "image_url": {
    "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB..."
  }
}
```

### HTTP URLs
```json
{
  "type": "image_url", 
  "image_url": {
    "url": "https://example.com/image.jpg"
  }
}
```

### Image Quality Settings
```json
{
  "type": "image_url",
  "image_url": {
    "url": "data:image/png;base64,...",
    "detail": "high"
  }
}
```

## Error Handling

### Connection Failures

Both endpoints have proper connection failure handling:
- **Timeout Detection**: Configurable timeouts for each endpoint
- **Error Propagation**: Connection failures are reported to clients immediately
- **Fallback Logic**: No automatic fallback between endpoints (by design)

### Routing Errors

If routing fails, the proxy logs the issue and returns appropriate HTTP status:
- **502 Bad Gateway**: Cannot connect to upstream
- **400 Bad Request**: Invalid image format or request structure

## Performance

### Latency Impact
- **Text requests**: No additional latency (same routing as before)
- **Image requests**: May have different latency characteristics depending on upstream endpoint performance

### Caching
- Each endpoint may have different caching behaviors
- Token counting and usage tracking works for both endpoint types

## Monitoring

Monitor both endpoints separately:
- **Anthropic endpoint**: Text model requests and responses
- **OpenAI endpoint**: Image/vision model requests and responses

Check logs for routing decisions and connection status to each upstream service.