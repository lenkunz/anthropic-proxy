
# Anthropic Proxy Service - API Documentation

## Overview

This Anthropic Proxy Service provides OpenAI-compatible access to z.ai's GLM-4.5 models with **client-controlled context management**, intelligent routing, and real token transparency.

**Key Features:**
- **Client-Controlled Context**: Real token reporting with emergency-only truncation
- **Context Transparency**: Full visibility into token usage and hard limits  
- **Content-Based Routing**: Text → Anthropic endpoint, Images → OpenAI endpoint
- **z.ai Thinking Parameter**: Automatic injection of `thinking: {"type": "enabled"}` for enhanced reasoning
- **Model Variants**: Control endpoint routing with `-openai`, `-anthropic` suffixes
- **OpenAI Compatibility**: Drop-in replacement for existing applications

## 🎯 Context Management

### Enhanced Response Format

All responses now include comprehensive context information:

```json
{
  "choices": [...],
  "usage": {
    "prompt_tokens": 1123,            // OpenAI-compatible count
    "completion_tokens": 100, 
    "total_tokens": 1223,
    "real_input_tokens": 1123,        // Actual token count
    "context_limit": 65536,           // Hard limit for this endpoint
    "context_utilization": "1.7%",    // Utilization percentage  
    "endpoint_type": "vision"         // Which endpoint was used
  },
  "context_info": {
    "real_input_tokens": 1123,
    "context_hard_limit": 65536,      // True model capacity
    "endpoint_type": "vision",
    "utilization_percent": 1.7,
    "available_tokens": 64413,        // Remaining space
    "truncated": false,               // Emergency truncation occurred?
    "note": "Use these values to manage context and avoid truncation"
  }
}
```

### Context Limits by Endpoint
- **Vision models** (with images): 65,536 tokens  
- **Text models** (text-only): 128,000 tokens
- **Auto-routing**: Determined by content type and model variant

### Emergency Truncation (Rare)
When hard limits are exceeded, responses include:
```json
{
  "context_info": {
    "truncated": true,
    "original_tokens": 80000,
    "real_input_tokens": 63000,
    "messages_removed": 15,
    "truncation_reason": "Hard context limit exceeded",
    "client_note": "Client should manage context to avoid this truncation"
  }
}
```

## Quick Start

### Basic Text Request (Routes to Anthropic)

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "glm-4.5",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "max_tokens": 100
  }'
```

### Basic Vision Request (Routes to OpenAI)

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "model": "glm-4.5v",
    "messages": [
      {
        "role": "user", 
        "content": [
          {"type": "text", "text": "What is in this image?"},
          {
            "type": "image_url",
            "image_url": {
              "url": "https://example.com/image.jpg"
            }
          }
        ]
      }
    ],
    "max_tokens": 100
  }'
```

## Image Age Management & Contextual Caching

The proxy features advanced image age management with AI-powered contextual descriptions and intelligent caching system.

### **Automatic Image Age Detection**

The proxy automatically manages image lifecycle in conversations:

- **Age Threshold**: Images older than `IMAGE_AGE_THRESHOLD` messages (default: 3) are automatically processed
- **Contextual Descriptions**: Old images are replaced with AI-generated contextual descriptions
- **Smart Routing**: Automatically switches from vision to text endpoints when images age out
- **Performance Caching**: Intelligent caching system provides up to 1.6x speedup on repeated operations

### **Caching System**

The proxy implements a high-performance caching system for image descriptions:

- **Context-Aware Keys**: Cache keys combine previous N messages + image hash for context sensitivity
- **Configurable Parameters**: `CACHE_CONTEXT_MESSAGES` (default: 2), `IMAGE_DESCRIPTION_CACHE_SIZE` (default: 1000)
- **Performance Metrics**: Up to 1.6x speedup on cache hits vs cache misses
- **Automatic Management**: LRU-style cleanup when cache size limits are reached

### **Configuration**

```bash
# Image age management
IMAGE_AGE_THRESHOLD=3              # Messages before images are considered "old"
CACHE_CONTEXT_MESSAGES=2           # Previous messages to include in cache key
IMAGE_DESCRIPTION_CACHE_SIZE=1000  # Maximum cache entries
```

### **API Behavior with Image Age Management**

When images exceed the age threshold:

1. **Automatic Processing**: System detects aged images without user intervention
2. **AI Description Generation**: Uses GLM-4.5v to generate contextual descriptions
3. **Seamless Replacement**: Images replaced with descriptive text in message history
4. **Endpoint Optimization**: Routes to text endpoint for better performance
5. **Cache Utilization**: Leverages cache for repeated image-context combinations

**Example Response with Age Management:**

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Based on the previous image (showing a cat in a garden setting with flowers and a wooden fence), and your question about dogs..."
    }
  }],
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 150,
    "total_tokens": 1400,
    "endpoint_type": "text"
  }
}
```

Note: The system automatically includes contextual information from aged images without requiring the full image data to be processed again.

## Available Models

The proxy supports multiple model variants that allow you to control routing behavior:

### Core Models

#### glm-4.5 (Auto-Routing Text Model)
- **Purpose**: Advanced text generation, reasoning, and conversation
- **Context Window**: 128,000 tokens  
- **Routing**: Auto-routing based on content type
  - Text-only requests → Anthropic endpoint
  - Requests with images → OpenAI endpoint
- **Best For**: General text tasks, coding, analysis, creative writing

#### glm-4.5v (Vision Model)
- **Purpose**: Text and image understanding with multimodal capabilities
- **Context Window**: 65,000 tokens
- **Routing**: Always uses OpenAI endpoint
- **Best For**: Image analysis, visual reasoning, document understanding

### Model Variants for Endpoint Control

Users can control which endpoint their requests route to by using model name suffixes:

#### glm-4.5-openai (Force OpenAI Endpoint)
- **Purpose**: Force routing to OpenAI-compatible endpoint
- **Behavior**: All requests (text and vision) use OpenAI endpoint
- **Use Case**: When you specifically need OpenAI endpoint features

#### glm-4.5-anthropic (Force Anthropic Endpoint)
- **Purpose**: Force routing to Anthropic-compatible endpoint  
- **Behavior**: Text requests use Anthropic endpoint (images still route to OpenAI)
- **Use Case**: When you specifically need Anthropic endpoint features

### Legacy Model Compatibility

The proxy maintains compatibility with common model names:
- `gpt-3.5-turbo`, `gpt-4`, etc. → Mapped to `glm-4.5` (auto-routing)
- `claude-3-sonnet-20240229`, `claude-3-haiku-20240307` → Mapped to `glm-4.5` (auto-routing)

## Authentication

The service requires authentication using your API key. You must include the API key in one of these formats:

### Method 1: Bearer Token (Recommended)
```bash
Authorization: Bearer YOUR_API_KEY
```

### Method 2: Custom Header
```bash
x-api-key: YOUR_API_KEY
```

### Method 3: Both Headers (Most Compatible)
```bash
Authorization: Bearer YOUR_API_KEY
x-api-key: YOUR_API_KEY
```

## API Endpoints

### OpenAI-Compatible Endpoints

#### 1. Chat Completions
**Endpoint**: `POST /v1/chat/completions`

**Description**: Creates a chat completion response. This endpoint is fully compatible with OpenAI's chat completions API.

**Request Body**:
```json
{
  "model": "glm-4.5",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "max_tokens": 100,
  "temperature": 0.7,
  "stream": false
}
```

**Response**:
```json
{
  "id": "chatcmpl_proxy",
  "object": "chat.completion",
  "created": 1634567890,
  "model": "glm-4.5",
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
    "prompt_tokens": 15,
    "completion_tokens": 10,
    "total_tokens": 25
  }
}
```

#### 2. Models List
**Endpoint**: `GET /v1/models`

**Description**: Retrieves a list of available models.

**Response**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "glm-4.5",
      "object": "model",
      "created": 1634567890,
      "owned_by": "proxy"
    },
    {
      "id": "glm-4.5v",
      "object": "model",
      "created": 1634567890,
      "owned_by": "proxy"
    }
  ]
}
```

#### 3. Token Counting
**Endpoint**: `POST /v1/messages/count_tokens`

**Description**: Counts tokens in a message payload. **Automatically uses text model for vision model requests** to ensure compatibility.

**Request Body**:
```json
{
  "model": "glm-4.5",
  "messages": [
    {"role": "user", "content": "Hello, how are you?"}
  ]
}
```

**Vision Model Fallback**: When called with vision models (e.g., `glm-4.5v`), automatically falls back to text model (`glm-4.5`) for token counting since vision models don't support this endpoint.

**Response**:
```json
{
  "input_tokens": 8,
  "token_count": 8,
  "input_token_count": 8,
  "proxy_estimate": true
}
```

**Note**: The proxy provides reliable token counting for both text and vision model requests.

### Anthropic Endpoints

#### 1. Messages
**Endpoint**: `POST /v1/messages`

**Description**: Direct Anthropic API endpoint for message creation. Supports both streaming and non-streaming responses.

**Request Body**:
```json
{
  "model": "glm-4.5",
  "max_tokens": 100,
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false
}
```

**Parameters**:
- `stream` (optional, boolean): When `true`, returns Server-Sent Events (SSE) streaming response. When `false` or omitted, returns a standard JSON response.

**Non-Streaming Response** (default when `stream` is `false` or omitted):
```json
{
  "id": "msg_123",
  "type": "message",
  "role": "assistant",
  "content": [{"type": "text", "text": "Hello! How can I help you?"}],
  "model": "glm-4.5",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 8,
    "output_tokens": 10
  }
}
```

**Streaming Response** (when `stream` is `true`):
Returns Server-Sent Events with `Content-Type: text/event-stream`. Each event contains incremental response data:
```
event: message_start
data: {"type": "message_start", "message": {"id": "msg_123", "type": "message", ...}}

event: content_block_start  
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}

event: message_stop
data: {"type": "message_stop"}
```

**Note**: This endpoint is compatible with both Anthropic's Claude CLI and other clients that expect proper JSON responses for non-streaming requests.

## Request Examples

### Text Chat Example

#### Python
```python
import requests

API_KEY = "YOUR_API_KEY"
BASE_URL = "http://localhost:5000"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "x-api-key": API_KEY
}

payload = {
    "model": "glm-4.5",
    "messages": [
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    "max_tokens": 200,
    "temperature": 0.7
}

response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                       json=payload, 
                       headers=headers)

print(response.json())
```

#### JavaScript
```javascript
const API_KEY = 'YOUR_API_KEY';
const BASE_URL = 'http://localhost:5000';

const response = await fetch(`${BASE_URL}/v1/chat/completions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`,
    'x-api-key': API_KEY
  },
  body: JSON.stringify({
    model: 'glm-4.5',
    messages: [
      { role: 'user', content: 'Explain quantum computing in simple terms.' }
    ],
    max_tokens: 200,
    temperature: 0.7
  })
});

const result = await response.json();
console.log(result);
```

### Vision Example

#### Python
```python
import requests

API_KEY = "YOUR_API_KEY"
BASE_URL = "http://localhost:5000"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "x-api-key": API_KEY
}

payload = {
    "model": "glm-4.5v",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What do you see in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.com/sample-image.jpg"
                    }
                }
            ]
        }
    ],
    "max_tokens": 150
}

response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                       json=payload, 
                       headers=headers)

print(response.json())
```

#### JavaScript
```javascript
const API_KEY = 'YOUR_API_KEY';
const BASE_URL = 'http://localhost:5000';

const response = await fetch(`${BASE_URL}/v1/chat/completions`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${API_KEY}`,
    'x-api-key': API_KEY
  },
  body: JSON.stringify({
    model: 'glm-4.5v',
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: 'What do you see in this image?' },
          {
            type: 'image_url',
            image_url: {
              url: 'https://example.com/sample-image.jpg'
            }
          }
        ]
      }
    ],
    max_tokens: 150
  })
});

const result = await response.json();
console.log(result);
``

## Common Errors and Troubleshooting

### 1. Unknown Model Error

**Error Message**: 
```json
{
  "error": {
    "message": "Unknown model: gpt-3.5-turbo",
    "type": "invalid_request_error"
  }
}
```

**Cause**: The proxy only supports specific models. Using unsupported model names will result in this error.

**Solution**: Use only the supported models:
- `glm-4.5` for text generation
- `glm-4.5v` for vision tasks

**Incorrect**:
```json
{
  "model": "gpt-3.5-turbo"
}
```

**Correct**:
```json
{
  "model": "glm-4.5"
}
```

### 2. Authentication Errors

**Error Message**: 
```json
{
  "detail": "Not authenticated"
}
```

**Cause**: Missing or invalid API key in request headers.

**Solution**: Include proper authentication headers:
```bash
Authorization: Bearer YOUR_API_KEY
x-api-key: YOUR_API_KEY
```

### 3. Missing Required Fields

**Error Message**: 
```json
{
  "detail": "Field required"
}
```

**Cause**: Required fields are missing from the request body.

**Solution**: Ensure all required fields are included:
- `model`: Must be a supported model name
- `messages`: At least one message is required
- `max_tokens`: Maximum tokens for the response

### 4. Invalid Image Format

**Error Message**: 
```json
{
  "error": "Invalid image format"
}
```

**Cause**: The image URL or base64 data is malformed or unsupported.

**Solution**: Use valid image formats:
- Supported formats: JPEG, PNG, GIF, WebP
- Maximum size: 10MB per image
- Valid URL formats or base64 encoding

## Best Practices

### 1. Model Selection
- Use `glm-4.5` for text-only tasks (larger context window)
- Use `glm-4.5v` when processing images or visual content
- Always specify the model explicitly in your requests

### 2. Token Management
- Monitor token usage with the `/v1/messages/count_tokens` endpoint
- Set appropriate `max_tokens` limits to control response length
- Be aware of context window limits (128K for text, 65K for vision)

### 3. Error Handling
- Always check response status codes
- Implement retry logic for transient errors
- Validate model names before making requests

### 4. Performance Optimization
- Use streaming responses for long conversations
- Batch multiple messages when possible
- Cache frequently used prompts
- **Leverage Image Caching**: Repeated image contexts benefit from 1.6x speedup
- **Optimize Image Age Settings**: Adjust `IMAGE_AGE_THRESHOLD` based on conversation patterns
- **Monitor Cache Performance**: Use context-aware caching for better hit rates

## Complete Example: Chat Application

Here's a complete example of a simple chat application using the proxy:

```python
import requests
import json

class AnthropicProxyClient:
    def __init__(self, api_key, base_url="http://localhost:5000"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "x-api-key": api_key
        }
    
    def chat(self, messages, model="glm-4.5", max_tokens=1000, temperature=0.7):
        """Send a chat completion request"""
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            headers=self.headers
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.text}")
        
        return response.json()
    
    def chat_with_image(self, messages, image_url, max_tokens=1000):
        """Send a chat completion request with an image"""
        # Add image to the last user message
        if messages and messages[-1]["role"] == "user":
            if isinstance(messages[-1]["content"], str):
                messages[-1]["content"] = [
                    {"type": "text", "text": messages[-1]["content"]}
                ]
            messages[-1]["content"].append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })
        
        return self.chat(messages, model="glm-4.5v", max_tokens=max_tokens)
    
    def count_tokens(self, messages, model="glm-4.5"):
        """Count tokens in a message"""
        payload = {
            "model": model,
            "
            "messages": messages
        }
        
        response = requests.post(
            f"{self.base_url}/v1/messages/count_tokens",
            json=payload,
            headers=self.headers
        )
        
        return response.json()

# Usage Example
if __name__ == "__main__":
    # Initialize client
    client = AnthropicProxyClient("YOUR_API_KEY")
    
    # Simple text chat
    messages = [
        {"role": "user", "content": "Hello! Can you help me with Python programming?"}
    ]
    
    response = client.chat(messages)
    print("Assistant:", response["choices"][0]["message"]["content"])
    
    # Chat with image
    image_messages = [
        {"role": "user", "content": "What's in this image?"}
    ]
    
    vision_response = client.chat_with_image(
        image_messages, 
        "https://example.com/sample-image.jpg"
    )
    print("Vision Analysis:", vision_response["choices"][0]["message"]["content"])
```

## Configuration

The proxy service can be configured through environment variables:

### Key Configuration Options

- `UPSTREAM_BASE`: Base URL for the upstream Anthropic API (default: `https://api.z.ai/api/anthropic`).
- `OPENAI_UPSTREAM_BASE`: Base URL for the upstream OpenAI API (default: `https://api.z.ai/api/coding/paas/v4`).
- `SERVER_API_KEY`: Static API key supplied to upstream requests when the client does not provide credentials.
- `FORWARD_CLIENT_KEY`: When true (default), forwards incoming `Authorization`/`x-api-key` headers upstream.
- `ENABLE_ZAI_THINKING`: When true (default), automatically adds `"thinking": {"type": "enabled"}` parameter to OpenAI endpoint requests for enhanced reasoning.
- `AUTOTEXT_MODEL`: Default text model when the request omits `model` (default: `glm-4.5`).
- `AUTOVISION_MODEL`: Default multimodal model used for image payloads without an explicit `model` (default: `glm-4.5`).
- `MODEL_MAP_JSON`: JSON mapping that rewrites OpenAI-style model names to Anthropic identifiers.
- `OPENAI_MODELS_LIST_JSON`: Optional JSON array that overrides the payload returned by `GET /v1/models`.
- `FORWARD_COUNT_TO_UPSTREAM`: Enables proxying `/v1/messages/count_tokens` calls to the upstream API (default: true).
- `COUNT_SHAPE_COMPAT`: Returns token count metadata that matches OpenAI's response schema (default: true).
- `FORCE_ANTHROPIC_BETA`: Forces the `anthropic-beta` header on every upstream request.
- `DEFAULT_ANTHROPIC_BETA`: Value applied to the `anthropic-beta` header when beta support is enabled (default: `prompt-caching-2024-07-31`).

## Support

For issues or questions:
1. Check the error messages and troubleshooting section
2. Verify your API key and authentication headers
3. Ensure you're using supported model names
4. Review request format and required fields

## Version History

- **v1.0.0**: Initial release with OpenAI-compatible endpoints
- **v1.1.0**: Added vision model support and improved error handling
- **v1.2.0**: Enhanced token counting and streaming support
- **v1.3.0**: Added z.ai thinking parameter support and enhanced upstream request logging

---

*This documentation covers the Anthropic Proxy Service API. For the most up-to-date information, please refer to the source code and configuration files.*
