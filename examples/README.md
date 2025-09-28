# Anthropic Proxy Examples

This directory contains example scripts demonstrating how to use the Anthropic Proxy API.

## 🚀 Quick Start

1. **Set up environment**: Ensure you have a `.env` file in the project root with:
   ```bash
   SERVER_API_KEY=your_api_key_here
   ```

2. **Start the proxy**:
   ```bash
   docker compose up -d
   ```

3. **Run examples**:
   ```bash
   python examples/example_usage.py
   python examples/example_model_variants.py
   python examples/example_messages_streaming.py
   ```

## 📁 Examples

### `example_usage.py`
Comprehensive demonstration of both OpenAI-compatible and Anthropic-native endpoints:
- `/v1/chat/completions` (OpenAI-style)
- `/v1/messages` (Anthropic-style)
- `/v1/models` (Model listing)
- Error handling examples

### `example_model_variants.py`
Shows how model variant routing works:
- `glm-4.5` - Auto-routing (text → Anthropic, images → OpenAI)
- `glm-4.5-openai` - Force OpenAI endpoint
- `glm-4.5-anthropic` - Force Anthropic endpoint for text

### `example_messages_streaming.py`
Demonstrates streaming vs non-streaming responses:
- Non-streaming mode (`stream=false`)
- Streaming mode (`stream=true`) with Server-Sent Events
- Performance comparison

## 🔧 Configuration

All examples automatically read configuration from the project root `.env` file:

```bash
# Required
SERVER_API_KEY=your_api_key_here

# Optional
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4
```

## 💡 Usage Tips

1. **API Keys**: Never hardcode API keys - always use environment variables
2. **Error Handling**: Examples include proper error handling patterns
3. **Rate Limiting**: Examples include appropriate delays between requests
4. **Timeouts**: All requests use reasonable timeout values
5. **Response Validation**: Examples show how to validate API responses

## 🐛 Troubleshooting

- **"API key not found"**: Check your `.env` file exists and contains `SERVER_API_KEY`
- **"Connection refused"**: Ensure the proxy is running with `docker compose up -d`
- **"Timeout errors"**: Check proxy logs with `docker compose logs anthropic-proxy`

---

For more detailed testing, see the `tests/` directory.