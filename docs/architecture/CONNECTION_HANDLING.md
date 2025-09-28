# Connection Handling Improvements

## Overview

This document describes the connection handling improvements made to the anthropic-proxy to better detect and propagate upstream connection failures to clients.

## Problem Statement

Previously, when the upstream server connection was cut or lost, clients could hang indefinitely waiting for a response. The proxy did not properly detect connection failures and propagate them to connected clients, leading to poor user experience.

## Solution

### 1. Connection Timeout Configuration

Added configurable timeout settings to prevent hanging connections:

```python
# Environment variables for timeout configuration
STREAM_TIMEOUT = 300.0      # 5 minutes for streaming connections
REQUEST_TIMEOUT = 120.0     # 2 minutes for regular requests  
CONNECT_TIMEOUT = 10.0      # 10 seconds to establish connection
```

### 2. Enhanced Error Propagation

#### Streaming Endpoints (`/v1/chat/completions` and `/v1/messages`)

- **Connection Loss Detection**: Wrap SSE iteration in try-catch to detect `httpx.TimeoutException`, `httpx.ConnectError`, and `httpx.NetworkError`
- **Graceful Error Response**: When connection is lost, emit proper SSE error event and close stream cleanly
- **Client Notification**: Clients receive structured error messages instead of hanging

Example error response for streaming:
```
data: {"error": {"message": "Connection to upstream server lost", "type": "connection_error"}, "id": "chatcmpl_proxy", "object": "chat.completion.chunk", "model": "gpt-4"}

data: [DONE]
```

#### Non-Streaming Endpoints

- **HTTP 502 Response**: Connection failures return proper 502 Bad Gateway status
- **Structured Error**: JSON error response with connection details

Example error response for non-streaming:
```json
{
  "error": {
    "message": "Failed to connect to upstream server",
    "type": "connection_error"
  }
}
```

### 3. Connection Error Types

The improved proxy handles these connection failure scenarios:

1. **Initial Connection Failure**: Cannot establish connection to upstream server
2. **Streaming Connection Loss**: Connection dropped during SSE streaming
3. **Timeout Errors**: Request/response timeouts during communication
4. **Network Errors**: General network connectivity issues

### 4. Fallback Mechanisms

#### SSE Fallback Chain
1. **Primary**: Attempt SSE streaming connection
2. **Fallback**: If SSE fails, attempt regular HTTP request and synthesize streaming response
3. **Error**: If both fail, return structured error to client

#### Retry Logic
- **Automatic Retries**: Use existing `_post_with_retries` function with connection error detection
- **ConnectionLostError**: Custom exception type to indicate unrecoverable connection loss
- **Backoff Strategy**: Exponential backoff for transient failures

### 5. Debug Logging

Enhanced debug logging helps troubleshoot connection issues:

```python
if DEBUG:
    print(f"[DEBUG] Stream connection lost: {stream_err}")
    print(f"[DEBUG] Initial connection failed: {conn_err}")
    print(f"[DEBUG] Fallback connection lost: {fallback_err}")
```

## Configuration

### Environment Variables

Add these environment variables to customize connection handling:

```bash
# Connection timeouts (in seconds)
STREAM_TIMEOUT=300.0        # Streaming connection timeout
REQUEST_TIMEOUT=120.0       # Regular request timeout  
CONNECT_TIMEOUT=10.0        # Connection establishment timeout

# Enable debug logging for connection issues
DEBUG=true
```

### Default Values

If not specified, the proxy uses these default timeout values:
- **Streaming**: 5 minutes (300 seconds)
- **Regular requests**: 2 minutes (120 seconds) 
- **Connection**: 10 seconds

## Testing

Use the provided test script to verify connection handling:

```bash
# Make the test script executable
chmod +x tests/integration/test_connection_simple.py

# Run connection handling tests
python3 tests/integration/test_connection_simple.py
```

The test script verifies:
1. Invalid upstream server handling
2. Messages endpoint connection failures
3. Non-streaming connection timeouts
4. Proper error propagation

## Benefits

1. **No More Hanging**: Clients receive errors instead of hanging indefinitely
2. **Fast Failure Detection**: Connection issues detected within seconds (not minutes)
3. **Graceful Degradation**: Proper error messages help clients handle failures
4. **Improved Reliability**: Better timeout configuration prevents resource exhaustion
5. **Better Observability**: Enhanced logging helps diagnose connection issues

## Backward Compatibility

These changes are fully backward compatible:
- Existing client code continues to work unchanged
- Default timeout values are reasonable for most use cases
- Error responses follow standard HTTP/SSE conventions
- All existing functionality remains intact

## Migration

No migration steps required. The improvements are automatic and use sensible defaults. Optionally:

1. Set custom timeout values via environment variables if needed
2. Enable `DEBUG=true` for detailed connection logging
3. Run the test script to verify your specific setup

## Examples

### Client-Side Error Handling

#### JavaScript (Streaming)
```javascript
const response = await fetch('/v1/chat/completions', {
  method: 'POST',
  body: JSON.stringify({stream: true, ...}),
  headers: {'Content-Type': 'application/json'}
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      if (data === '[DONE]') break;
      
      try {
        const parsed = JSON.parse(data);
        if (parsed.error) {
          console.error('Connection error:', parsed.error.message);
          // Handle connection failure gracefully
          break;
        }
      } catch (e) {
        // Handle parse errors
      }
    }
  }
}
```

#### Python (Non-Streaming)
```python
import httpx

async with httpx.AsyncClient() as client:
    try:
        response = await client.post('/v1/chat/completions', json={...})
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 502:
            error_data = e.response.json()
            if error_data.get('error', {}).get('type') == 'connection_error':
                print("Upstream server connection failed")
                # Handle connection failure
    except httpx.TimeoutException:
        print("Request timed out")
        # Handle timeout
```