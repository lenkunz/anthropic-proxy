
# Anthropic Proxy API Documentation

Complete API reference for the Anthropic Proxy service, providing OpenAI-compatible endpoints with advanced context management and intelligent routing.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URLs](#base-urls)
- [Available Models](#available-models)
- [Endpoints](#endpoints)
  - [Chat Completions](#chat-completions)
  - [Models](#models)
  - [Messages (Anthropic-compatible)](#messages-anthropic-compatible)
  - [Health Check](#health-check)
- [Model Variants](#model-variants)
- [Content-Based Routing](#content-based-routing)
- [Token Counting](#token-counting)
- [Error Handling](#error-handling)
- [Response Format](#response-format)
- [Streaming](#streaming)
- [Image Support](#image-support)
- [Context Management](#context-management)
- [Rate Limiting](#rate-limiting)

## Overview

The Anthropic Proxy provides OpenAI-compatible API endpoints that route requests to z.ai's GLM-4.6 models with intelligent features:

- **OpenAI-compatible endpoints** for seamless integration
- **Intelligent content-based routing** for optimal model selection
- **Advanced context management** with AI-powered condensation
- **Accurate token counting** with tiktoken integration
- **Environment deduplication** for token savings
- **Image support** with automatic routing
- **Performance monitoring** and debugging capabilities

## Authentication

### API Key Authentication

Include your API key in the `Authorization` header:

```bash
Authorization: Bearer YOUR_API_KEY
```

### Environment Variable Configuration

The proxy can be configured to forward client API keys or use a server-side key:

```bash
# Use server API key (recommended for production)
SERVER_API_KEY=your_zai_api_key

# Forward client API keys (for development)
FORWARD_CLIENT_KEYS=true
```

## Base URLs

- **Production**: `http://localhost:5000`
- **Development**: `http://localhost:5000`
- **Docker**: `http://localhost:5000`

## Available Models

### Primary Models

- `glm-4.6` - Auto-routing model (default)
- `glm-4.6-openai` - Forces OpenAI endpoint
- `glm-4.6-anthropic` - Forces Anthropic endpoint (text only)

### Model Capabilities

| Model | Text | Vision | Context | Auto-Routing |
|-------|------|--------|---------|--------------|
| glm-4.6 | ✅ | ✅ | 200K | ✅ |
| glm-4.6-openai | ✅ | ✅ | 200K | ❌ |
| glm-4.6-anthropic | ✅ | ❌ | 200K | ❌ |

## Endpoints

### Chat Completions

OpenAI-compatible chat completions endpoint.

**Endpoint**: `POST /v1/chat/completions`

#### Request Headers

```bash
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY
```

#### Request Body

```json
{
  "model": "glm-4.6",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "max_tokens": 1000,
  "temperature": 0.7,
  "stream": false,
  "top_p": 0.9,
  "frequency_penalty": 0,
  "presence_penalty": 0
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| model | string | Yes | Model ID to use |
| messages | array | Yes | Array of message objects |
| max_tokens | integer | No | Maximum tokens to generate (default: 1000) |
| temperature | number | No | Sampling temperature (0.0-2.0, default: 0.7) |
| stream | boolean | No | Enable streaming responses (default: false) |
| top_p | number | No | Nucleus sampling parameter (default: 0.9) |
| frequency_penalty | number | No | Frequency penalty (-2.0 to 2.0, default: 0) |
| presence_penalty | number | No | Presence penalty (-2.0 to 2.0, default: 0) |

#### Response Body (Non-Streaming)

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1699012345,
  "model": "glm-4.6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35,
    "context_utilization": 0.175,
    "cache_read_input_tokens": 0
  },
  "context_management": {
    "risk_level": "SAFE",
    "messages_processed": 2,
    "tokens_saved": 0,
    "condensation_applied": false
  }
}
```

#### Streaming Response

When `stream: true`, the response uses Server-Sent Events (SSE):

```bash
data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1699012345, "model": "glm-4.6", "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1699012345, "model": "glm-4.6", "choices": [{"index": 0, "delta": {"content": "Hello!"}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1699012345, "model

": null}]}

data: [DONE]
```

### Models

List available models and their capabilities.

**Endpoint**: `GET /v1/models`

#### Response Body

```json
{
  "object": "list",
  "data": [
    {
      "id": "glm-4.6",
      "object": "model",
      "created": 1699012345,
      "owned_by": "zai",
      "capabilities": {
        "text": true,
        "vision": true,
        "context_window": 200000,
        "auto_routing": true
      }
    },
    {
      "id": "glm-4.6-openai",
      "object": "model",
      "created": 1699012345,
      "owned_by": "zai",
      "capabilities": {
        "text": true,
        "vision": true,
        "context_window": 200000,
        "auto_routing": false,
        "endpoint": "openai"
      }
    },
    {
      "id": "glm-4.6-anthropic",
      "object": "model",
      "created": 1699012345,
      "owned_by": "zai",
      "capabilities": {
        "text": true,
        "vision": false,
        "context_window": 200000,
        "auto_routing": false,
        "endpoint": "anthropic"
      }
    }
  ]
}
```

### Messages (Anthropic-compatible)

Anthropic-compatible messages endpoint.

**Endpoint**: `POST /v1/messages`

#### Request Body

```json
{
  "model": "glm-4.6",
  "max_tokens": 1000,
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ],
  "system": "You are a helpful assistant.",
  "temperature": 0.7,
  "stream": false
}
```

#### Response Body

```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! I'm doing well, thank you for asking."
    }
  ],
  "model": "glm-4.6",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 20,
    "output_tokens": 15
  },
  "context_management": {
    "risk_level": "SAFE",
    "messages_processed": 1,
    "tokens_saved": 0,
    "condensation_applied": false
  }
}
```

### Health Check

Check the health and status of the proxy service.

**Endpoint**: `GET /health`

#### Response Body

```json
{
  "status": "healthy",
  "timestamp": "2025-10-01T14:00:00Z",
  "version": "1.7.1",
  "uptime": 3600,
  "services": {
    "api": "healthy",
    "cache": "healthy",
    "logging": "healthy"
  },
  "configuration": {
    "model": "glm-4.6",
    "context_management": true,
    "log_rotation": true,
    "cache_enabled": true
  }
}
```

## Model Variants

### glm-4.6 (Auto-routing)

Automatically routes requests based on content:
- **Text-only requests** → Anthropic endpoint
- **Image requests** → OpenAI endpoint
- **Best performance** and cost optimization

### glm-4.6-openai (OpenAI Endpoint)

Always routes to OpenAI-compatible endpoint:
- **Full feature support** including images
- **Consistent API format**
- **Thinking parameter support**

### glm-4.6-anthropic (Anthropic Endpoint)

Always routes to Anthropic endpoint:
- **Text-only requests** (images automatically routed to OpenAI)
- **Native Anthropic format**
- **Optimized for text processing**

## Content-Based Routing

The proxy automatically determines the optimal endpoint based on request content:

### Routing Logic

```python
def should_use_openai_endpoint(model: str, has_images: bool) -> bool:
    if model == "glm-4.6-openai":
        return True
    elif model == "glm-4.6-anthropic":
        return has_images  # Only images go to OpenAI
    else:  # glm-4.6 (auto-routing)
        return has_images  # Images go to OpenAI, text to Anthropic
```

### Routing Examples

```bash
# Text request with glm-4.6 → Anthropic endpoint
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "glm-4.6", "messages": [{"role": "user", "content": "Hello"}]}'

# Image request with glm-4.6 → OpenAI endpoint
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "glm-4.6", "messages": [{"role": "user", "content": [{"type": "text", "text": "What do you see?"}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}]}]}'

# Any request with glm-4.6-openai → OpenAI endpoint
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "glm-4.6-openai", "messages": [{"role": "user", "content": "Hello"}]}'
```

## Token Counting

The proxy provides accurate token counting using tiktoken:

### Token Usage Information

```json
{
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 50,
    "total_tokens": 200,
    "context_utilization": 0.1,
    "cache_read_input_tokens": 25
  }
}
```

### Context Utilization

Percentage of the model's context window being used:

- **< 60%**: Normal operation
- **60-80%**: Warning level
- **80-95%**: Critical level
- **> 95%**: Emergency condensation applied

### Cache Read Tokens

Tokens recovered from cache (environment deduplication, image descriptions):

```json
{
  "cache_read_input_tokens": 45,
  "tokens_saved": 45,
  "cache_hit_rate": 0.23
}
```

## Error Handling

The proxy provides comprehensive error handling with OpenAI-compatible error responses:

### Error Response Format

```json
{
  "error": {
    "message": "Invalid request: model not found",
    "type": "invalid_request_error",
    "param": "model",
    "code": "model_not_found"
  },
  "choices": []
}
```

### Common Error Codes

| Error Code | Description | HTTP Status |
|------------|-------------|-------------|
| `invalid_request_error` | Invalid request parameters | 400 |
| `authentication_error` | Invalid API key | 401 |
| `permission_denied_error` | Insufficient permissions | 403 |
| `not_found_error` | Resource not found | 404 |
| `rate_limit_error` | Rate limit exceeded | 429 |
| `api_error` | Upstream API error | 500 |
| `context_overflow_error` | Context exceeds limits | 400 |

## Context Management

The proxy provides intelligent context management to handle long conversations:

### Risk Levels

| Level | Threshold | Action |
|-------|-----------|--------|
| SAFE | < 60% | Normal processing |
| CAUTION | 60-80% | Warning logged |
| WARNING | 80-90% | Performance monitoring |
| CRITICAL | 90-95% | Emergency preparation |
| OVERFLOW | > 95% | Condensation applied |

### AI-Powered Condensation

When context exceeds critical thresholds:

```json
{
  "context_management": {
    "risk_level": "CRITICAL",
    "messages_processed": 25,
    "tokens_saved": 1500,
    "condensation_applied": true,
    "condensation_strategy": "ai_summarization"
  }
}
```

### Environment Details Deduplication

Automatic removal of redundant environment information:

```json
{
  "context_management": {
    "environment_deduplication": {
      "patterns_detected": 3,
      "tokens_saved": 85,
      "deduplication_applied": true
    }
  }
}
```

## Image Support

The proxy supports image processing with automatic routing:

### Image Formats

- **JPEG**, **PNG**, **GIF**, **WebP**
- **Base64 encoding** required
- **Maximum file size**: 20MB

### Image Request Example

```json
{
  "model": "glm-4.6",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What do you see in this image?"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
          }
        }
      ]
    }
  ]
}
```

### Image Age Management

Images older than configured threshold are automatically summarized:

```json
{
  "context_management": {
    "image_age_management": {
      "old_images_removed": 2,
      "descriptions_generated": 2,
      "tokens_saved": 150
    }
  }
}
```

## Rate Limiting

The proxy implements rate limiting to ensure fair usage:

### Default Limits

- **60 requests per minute** per API key
- **100 concurrent connections** per client
- **1MB maximum request size**

### Rate Limit Headers

```bash
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1699012400
```

### Rate Limit Error

```json
{
  "error": {
    "message": "Rate limit exceeded. Please try again later.",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  }
}
```

## Configuration

The proxy supports extensive configuration via environment variables:

### Key Configuration Options

```bash
# API Configuration
SERVER_API_KEY=your_api_key
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4

# Context Management
ENABLE_MESSAGE_CONDENSATION=true
CONDENSATION_WARNING_THRESHOLD=0.80
CONDENSATION_CRITICAL_THRESHOLD=0.90

# Token Counting
ENABLE_ACCURATE_TOKEN_COUNTING=true
TOKEN_COUNTING_MODEL=cl100k_base

# Cache Configuration
IMAGE_DESCRIPTION_CACHE_SIZE=1000
CACHE_DIR=./cache
CACHE_ENABLE_LOGGING=true

# Log Rotation
UPSTREAM_LOG_ROTATION=true
UPSTREAM_LOG_MAX_SIZE_MB=50
UPSTREAM_LOG_BACKUP_COUNT=10
```

For a complete configuration reference, see the `.env.example` file in the project root.

## Examples

### Basic Text Chat

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4.6",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100
  }'
```

### Streaming Response

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4.6",
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "stream": true
  }'
```

### Image Analysis

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4.6",
    "messages": [
      {
        "role": "user",
        "content": [
          {"type": "text", "text": "What do you see?"},
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
            }
          }
        ]
      }
    ],
    "max_tokens": 200
  }'
```

### Anthropic-Compatible Request

```bash
curl -X POST http://localhost:5000/v1/messages \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-4.6",
    "max_tokens": 100,
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

## Troubleshooting

### Common Issues

1. **Authentication errors**
   - Verify API key in `.env` file
   - Check `Authorization` header format

2. **Model not found**
   - Use supported model variants: `glm-4.6`, `glm-4.6-openai`, `glm-4.6-anthropic`

3. **Context limit exceeded**
   - Enable message condensation in configuration
   - Use shorter conversation history

4. **Image processing errors**
   - Verify base64 encoding
   - Check image size limits (20MB)

5. **Rate limiting**
   - Implement exponential backoff
   - Check rate limit headers

### Debug Logging

Enable debug logging for troubleshooting:

```bash
# Set log level to DEBUG
LOG_LEVEL=DEBUG

# Enable upstream logging
UPSTREAM_LOGGING=true

# Enable context performance logging
ENABLE_CONTEXT_PERFORMANCE_LOGGING=true
```

### Health Check

Monitor service health:

```bash
curl http://localhost:5000/health
```

For more detailed troubleshooting information, see the [TROUBLESHOOTING.md](TROUBLESHOOTING.md) file.
