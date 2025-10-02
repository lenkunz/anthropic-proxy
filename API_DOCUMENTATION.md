# Anthropic Proxy API Documentation

## Overview

The Anthropic Proxy provides a unified API interface for accessing multiple AI services with intelligent auto-switching, performance monitoring, and endpoint discovery capabilities.

## Base URL

```
http://localhost:5000
```

## Authentication

The proxy uses Bearer token authentication. Include your API key in the Authorization header:

```
Authorization: Bearer your-api-key
```

## Dual Endpoint Support

The proxy supports dual endpoints for different API types:

- **Anthropic Endpoint**: For Anthropic-compatible API requests
- **OpenAI Endpoint**: For OpenAI-compatible API requests (including vision models)

The proxy automatically routes requests to the appropriate endpoint based on the request type.

## Endpoints

### Health Check

#### GET /health

Check the health status of the proxy server.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-10-02T14:15:00Z",
  "uptime": 3600,
  "version": "1.0.0"
}
```

### Anthropic-Compatible API

#### POST /v1/messages

Create a message completion using Anthropic-compatible API.

**Request Body:**
```json
{
  "model": "claude-3-sonnet-20240229",
  "max_tokens": 1024,
  "messages": [
    {
      "role": "user",
      "content": "Hello, world!"
    }
  ]
}
```

**Response:**
```json
{
  "id": "msg_123456",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello! How can I help you today?"
    }
  ],
  "model": "claude-3-sonnet-20240229",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 25
  }
}
```

#### POST /v1/messages/batches

Create a batch of message completions.

**Request Body:**
```json
{
  "requests": [
    {
      "custom_id": "req-1",
      "model": "claude-3-sonnet-20240229",
      "max_tokens": 1024,
      "messages": [
        {
          "role": "user",
          "content": "What is the capital of France?"
        }
      ]
    }
  ]
}
```

#### GET /v1/messages/batches/{batch_id}

Retrieve the status of a message batch.

#### POST /v1/messages/batches/{batch_id}/cancel

Cancel a message batch.

### OpenAI-Compatible API

#### POST /v1/chat/completions

Create a chat completion using OpenAI-compatible API.

**Request Body:**
```json
{
  "model": "glm-4.6",
  "messages": [
    {
      "role": "user",
      "content": "Hello, world!"
    }
  ],
  "max_tokens": 1024,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "id": "chatcmpl-123456",
  "object": "chat.completion",
  "created": 1699012345,
  "model": "glm-4.6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 25,
    "total_tokens": 35
  }
}
```

#### POST /v1/completions

Create a text completion.

#### GET /v1/models

List available models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "glm-4.6",
      "object": "model",
      "created": 1699012345,
      "owned_by": "zai"
    },
    {
      "id": "glm-4.5v",
      "object": "model",
      "created": 1699012345,
      "owned_by": "zai"
    }
  ]
}
```

#### GET /v1/models/{model}

Retrieve information about a specific model.

### Vision API

#### POST /v1/chat/completions

Create a chat completion with vision support.

**Request Body:**
```json
{
  "model": "glm-4.5v",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What's in this image?"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
          }
        }
      ]
    }
  ],
  "max_tokens": 1024
}
```

### Statistics API

#### GET /stats

Get proxy statistics and performance metrics.

**Response:**
```json
{
  "uptime": 3600,
  "total_requests": 1250,
  "active_connections": 5,
  "requests_per_second": 2.5,
  "avg_response_time": 250,
  "servers": {
    "cn": {
      "latency_ms": 150,
      "success_rate": 0.98,
      "requests": 750
    },
    "inter": {
      "latency_ms": 200,
      "success_rate": 0.95,
      "requests": 500
    }
  }
}
```

#### GET /stats/performance

Get detailed performance metrics for all servers.

**Response:**
```json
{
  "servers": {
    "cn": {
      "endpoint": "https://open.bigmodel.cn/api/paas/v4",
      "latency_ms": 150,
      "status_code": 200,
      "success": true,
      "timestamp": 1699012345,
      "region": "China",
      "error": null
    },
    "inter": {
      "endpoint": "https://api.z.ai/api/anthropic",
      "latency_ms": 200,
      "status_code": 200,
      "success": true,
      "timestamp": 1699012345,
      "region": "International",
      "error": null
    }
  }
}
```

### Configuration API

#### GET /config

Get current proxy configuration.

**Response:**
```json
{
  "current_server": "cn",
  "servers": {
    "cn": {
      "endpoint": "https://open.bigmodel.cn/api/paas/v4",
      "region": "China",
      "latency_ms": 150
    },
    "inter": {
      "endpoint": "https://api.z.ai/api/anthropic",
      "region": "International",
      "latency_ms": 200
    }
  },
  "auto_switch_enabled": false,
  "auto_switch_interval": 60
}
```

#### POST /config/switch

Switch to a different server.

**Request Body:**
```json
{
  "server": "inter"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Switched to server: inter",
  "current_server": "inter"
}
```

#### POST /config/auto-switch

Enable or disable automatic server switching.

**Request Body:**
```json
{
  "enabled": true,
  "interval": 120
}
```

**Response:**
```json
{
  "success": true,
  "message": "Auto-switching enabled with 120s interval"
}
```

### Intelligent Auto-Switching API

#### POST /intelligent-switch

Trigger intelligent auto-switching with endpoint discovery.

**Response:**
```json
{
  "success": true,
  "message": "Intelligent auto-switching completed",
  "results": {
    "current_server": "inter",
    "performance": {
      "latency_ms": 200,
      "requests_per_second": 2.5,
      "avg_response_time": 250
    },
    "discovered_endpoints": 3,
    "best_endpoint": {
      "ip": "123.45.67.89",
      "latency_ms": 150,
      "success": true
    },
    "switched": true
  }
}
```

#### GET /endpoints/discover

Discover alternative endpoints for a domain.

**Query Parameters:**
- `domain` (string): Domain to discover endpoints for
- `max_nodes` (integer, optional): Maximum number of nodes to query (default: 3)

**Response:**
```json
{
  "domain": "api.z.ai",
  "endpoints": [
    {
      "ip": "123.45.67.89",
      "country": "United States",
      "city": "New York",
      "domain": "api.z.ai"
    },
    {
      "ip": "234.56.78.90",
      "country": "Germany",
      "city": "Frankfurt",
      "domain": "api.z.ai"
    }
  ]
}
```

#### POST /endpoints/test

Test a specific endpoint with a thinking prompt.

**Request Body:**
```json
{
  "ip": "123.45.67.89",
  "domain": "api.z.ai"
}
```

**Response:**
```json
{
  "ip": "123.45.67.89",
  "domain": "api.z.ai",
  "endpoint_url": "https://123.45.67.89/api/anthropic",
  "latency_ms": 150,
  "success": true,
  "error": null,
  "timestamp": 1699012345
}
```

## Error Handling

The API returns standard HTTP status codes and error messages in JSON format:

```json
{
  "error": {
    "type": "invalid_request_error",
    "message": "Invalid request format",
    "code": "invalid_format"
  }
}
```

### Common Error Codes

- `400 Bad Request`: Invalid request format or parameters
- `401 Unauthorized`: Invalid or missing API key
- `404 Not Found`: Endpoint not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `502 Bad Gateway`: Upstream server error
- `503 Service Unavailable`: Service temporarily unavailable

## Rate Limiting

The proxy implements rate limiting to ensure fair usage:

- Default rate limit: 100 requests per minute
- Burst limit: 10 requests per second
- Rate limit headers are included in responses:
  - `X-RateLimit-Limit`: Request limit per minute
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when rate limit window resets (Unix timestamp)

## Streaming

The proxy supports streaming responses for chat completions:

**Request:**
```json
{
  "model": "glm-4.6",
  "messages": [
    {
      "role": "user",
      "content": "Tell me a story"
    }
  ],
  "stream": true,
  "max_tokens": 1024
}
```

**Response:**
```
data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1699012345, "model": "glm-4.6", "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1699012345, "model": "glm-4.6", "choices": [{"index": 0, "delta": {"content": "Once"}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1699012345, "model": "glm-4.6", "choices": [{"index": 0, "delta": {"content": " upon"}, "finish_reason": null}]}

data: [DONE]
```

## Webhooks

The proxy supports webhooks for event notifications:

### Configure Webhook

#### POST /webhooks/configure

**Request Body:**
```json
{
  "url": "https://your-webhook-endpoint.com/events",
  "events": ["server_switch", "performance_alert", "error"],
  "secret": "your-webhook-secret"
}
```

**Response:**
```json
{
  "success": true,
  "webhook_id": "wh_123456",
  "status": "active"
}
```

### Webhook Events

#### Server Switch Event
```json
{
  "event": "server_switch",
  "timestamp": "2023-10-02T14:15:00Z",
  "data": {
    "from_server": "cn",
    "to_server": "inter",
    "reason": "performance_degradation",
    "latency_improvement": 50
  }
}
```

#### Performance Alert Event
```json
{
  "event": "performance_alert",
  "timestamp": "2023-10-02T14:15:00Z",
  "data": {
    "server": "cn",
    "metric": "latency",
    "value": 800,
    "threshold": 500,
    "severity": "warning"
  }
}
```

## SDKs and Libraries

### Python SDK

```python
from anthropic_proxy import AnthropicProxyClient

# Initialize client
client = AnthropicProxyClient(
    base_url="http://localhost:5000",
    api_key="your-api-key"
)

# Create message completion
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ]
)

print(response.content[0].text)
```

### JavaScript SDK

```javascript
import { AnthropicProxyClient } from 'anthropic-proxy-js';

// Initialize client
const client = new AnthropicProxyClient({
  baseURL: 'http://localhost:5000',
  apiKey: 'your-api-key'
});

// Create message completion
const response = await client.messages.create({
  model: 'claude-3-sonnet-20240229',
  maxTokens: 1024,
  messages: [
    { role: 'user', content: 'Hello, world!' }
  ]
});

console.log(response.content[0].text);
```

## Best Practices

1. **Use appropriate endpoints**: Use Anthropic endpoints for Claude models and OpenAI endpoints for other models.

2. **Implement retry logic**: Handle temporary failures with exponential backoff.

3. **Monitor performance**: Use the statistics API to monitor request performance and server health.

4. **Set reasonable timeouts**: Use appropriate timeout values based on your use case.

5. **Handle rate limits**: Respect rate limit headers and implement backoff when needed.

6. **Use streaming for long responses**: Enable streaming for responses that may take longer to generate.

7. **Secure your API keys**: Store API keys securely and don't expose them in client-side code.

## Troubleshooting

### Common Issues

#### Authentication Errors
- Verify your API key is correct and not expired
- Check that the Authorization header is properly formatted

#### Server Errors
- Check the proxy health endpoint: `GET /health`
- Review proxy logs for detailed error information

#### Performance Issues
- Use the statistics API to monitor performance metrics
- Consider enabling intelligent auto-switching for better performance

#### Endpoint Discovery Issues
- Verify the domain is correct and accessible
- Check network connectivity to the check-host.net API

### Debug Headers

The proxy includes debug headers in responses:

- `X-Proxy-Server`: The upstream server that handled the request
- `X-Proxy-Latency`: Latency to the upstream server in milliseconds
- `X-Proxy-Request-ID`: Unique request ID for tracing

Enable debug mode by setting the `X-Debug` header to `true` in your requests.

## Changelog

### Version 1.0.0
- Initial release with dual endpoint support
- Intelligent auto-switching with endpoint discovery
- Performance monitoring and statistics
- Webhook support for event notifications
- Python and JavaScript SDKs