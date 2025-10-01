# Accurate Token Counting System

This document describes the implementation of the tiktoken-based accurate token counting system for the anthropic-proxy project.

## Overview

The accurate token counting system replaces the previous scaling-based token estimation with precise tiktoken-based counting while maintaining backward compatibility and endpoint scaling when necessary.

## Key Features

### 1. AccurateTokenCounter Class
- **Location**: [`accurate_token_counter.py`](accurate_token_counter.py:1)
- **Purpose**: Provides precise token counting using tiktoken encodings
- **Features**:
  - Support for both Anthropic and OpenAI token encodings
  - LRU caching for performance optimization
  - Dynamic image token calculation based on description length
  - Graceful fallbacks for error handling
  - Support for various message formats (text, images, tool calls)

### 2. Dynamic Image Token Calculation
- **Replaces**: Fixed 1000 tokens per image estimation
- **New Method**: Calculates tokens based on actual image description length
- **Configuration**: 
  - `BASE_IMAGE_TOKENS=85` (base tokens for image metadata)
  - `IMAGE_TOKENS_PER_CHAR=0.25` (tokens per character in description)

### 3. Performance Optimization
- **Caching**: LRU cache with configurable size (`TIKTOKEN_CACHE_SIZE=1000`)
- **Fire-and-forget**: Async operations that don't block API requests
- **Minimal overhead**: Optimized for frequent token counting operations

### 4. Backward Compatibility
- **Scaling Preserved**: Endpoint scaling functions maintained for compatibility
- **Fallback Support**: Graceful degradation if tiktoken fails
- **Configuration Control**: Can be disabled via `ENABLE_ACCURATE_TOKEN_COUNTING=false`

## Configuration

### New Environment Variables

```bash
# Enable/disable accurate token counting
ENABLE_ACCURATE_TOKEN_COUNTING=true

# Cache size for tiktoken results
TIKTOKEN_CACHE_SIZE=1000

# Enable detailed token counting logging
ENABLE_TOKEN_COUNTING_LOGGING=false

# Image token calculation settings
BASE_IMAGE_TOKENS=85
IMAGE_TOKENS_PER_CHAR=0.25
```

### Preserved Configuration

```bash
# Scaling configuration (still needed for endpoint compatibility)
ANTHROPIC_EXPECTED_TOKENS=200000
OPENAI_EXPECTED_TOKENS=200000
REAL_TEXT_MODEL_TOKENS=200000
REAL_VISION_MODEL_TOKENS=65536
SCALE_COUNT_TOKENS_FOR_VISION=true
```

## Implementation Details

### Core Classes and Functions

#### AccurateTokenCounter
```python
class AccurateTokenCounter:
    def count_message_tokens(self, message, endpoint_type="openai", image_descriptions=None)
    def count_messages_tokens(self, messages, endpoint_type="openai", system_message=None, image_descriptions=None)
    def validate_token_count(self, messages, max_tokens, endpoint_type="openai", system_message=None, image_descriptions=None)
```

#### Convenience Functions
```python
def count_tokens_accurate(messages, endpoint_type="openai", system_message=None, image_descriptions=None)
def get_token_counter() -> AccurateTokenCounter
```

#### Integration Functions
```python
def count_tokens_accurate_with_scaling(messages, upstream_endpoint, downstream_endpoint, is_vision=False, image_descriptions=None, system_message=None)
```

### Updated Functions

#### main.py Changes
- [`count_tokens_from_messages()`](main.py:851): Now supports `image_descriptions` parameter and uses accurate counting
- Added [`count_tokens_accurate_with_scaling()`](main.py:620): Combines accurate counting with endpoint scaling
- Added [`validate_token_usage()`](main.py:570): Validates token counting accuracy

#### context_window_manager.py Changes
- [`ContextWindowManager.estimate_message_tokens()`](context_window_manager.py:100): Now uses accurate counting
- [`ContextWindowManager.validate_context_window()`](context_window_manager.py:124): Supports image descriptions
- [`validate_and_truncate_context()`](context_window_manager.py:323): Updated with image descriptions support
- [`get_context_info()`](context_window_manager.py:341): Updated with image descriptions support

## Usage Examples

### Basic Token Counting
```python
from accurate_token_counter import count_tokens_accurate

messages = [
    {"role": "user", "content": "Hello, how are you?"},
    {"role": "assistant", "content": "I'm doing well, thank you!"}
]

token_count = count_tokens_accurate(messages, "openai")
print(f"Total tokens: {token_count}")
```

### Token Counting with Images
```python
messages = [
    {"role": "user", "content": [
        {"type": "text", "text": "What do you see in this image?"},
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
    ]}
]

image_descriptions = {
    0: "A diagram showing a web application architecture"
}

token_count = count_tokens_accurate(messages, "openai", None, image_descriptions)
print(f"Total tokens with image: {token_count}")
```

### Using with Scaling for Endpoint Compatibility
```python
from main import count_tokens_accurate_with_scaling

# Count tokens for Anthropic -> OpenAI endpoint routing
scaled_tokens = count_tokens_accurate_with_scaling(
    messages=messages,
    upstream_endpoint="anthropic",
    downstream_endpoint="openai",
    is_vision=True,
    image_descriptions=image_descriptions
)
```

### Context Window Management
```python
from context_window_manager import validate_and_truncate_context

# Validate and truncate if necessary
processed_messages, metadata = validate_and_truncate_context(
    messages=messages,
    is_vision=True,
    max_tokens=4000,
    image_descriptions=image_descriptions
)

print(f"Truncated: {metadata['truncated']}")
print(f"Original tokens: {metadata['original_tokens']}")
print(f"Final tokens: {metadata['final_tokens']}")
```

## Token Counting Strategy

### 1. Text Content
- Uses tiktoken's `cl100k_base` encoding (compatible with GPT-4 and modern models)
- Counts role names, formatting tokens, and message structure
- Handles both string and list content formats

### 2. Image Content
- Base tokens: 85 for image metadata
- Dynamic tokens: 0.25 tokens per character of description
- Example: 100-character description = 85 + (100 * 0.25) = 110 tokens

### 3. Tool Calls
- Counts function names, arguments, and formatting
- Handles both string and JSON argument formats
- Base overhead: 20 tokens for tool call structure

### 4. Message Metadata
- Counts role names, formatting, and other metadata
- Base overhead: 4-10 tokens per message depending on complexity

## Performance Considerations

### Caching Strategy
- **Text Caching**: LRU cache for frequently counted text content
- **Cache Size**: Configurable via `TIKTOKEN_CACHE_SIZE`
- **Cache Hit Ratio**: Monitor via `get_cache_stats()` method

### Optimization Tips
1. **Enable Logging**: Set `ENABLE_TOKEN_COUNTING_LOGGING=true` for debugging
2. **Monitor Cache**: Check cache statistics to optimize cache size
3. **Batch Operations**: Reuse token counter instances for multiple operations

## Error Handling

### Graceful Degradation
1. **tiktoken Import Failure**: Falls back to character-based estimation
2. **Encoding Errors**: Uses 1 token per 4 characters fallback
3. **Cache Errors**: Continues without caching
4. **Message Format Errors**: Best-effort counting with conservative estimates

### Logging
- Debug logging: Enable via `ENABLE_TOKEN_COUNTING_LOGGING=true`
- Error logging: Always enabled for critical failures
- Performance logging: Cache statistics and timing information

## Migration Guide

### From Scaling to Accurate Counting

1. **Configuration**: Add new environment variables to `.env`
2. **Dependencies**: Ensure `tiktoken>=0.5.0` is in `requirements.txt`
3. **Code Updates**: Existing code should work without changes
4. **Testing**: Run integration tests to verify functionality

### Backward Compatibility
- All existing scaling functions are preserved
- Endpoint compatibility maintained
- Configuration can disable accurate counting if needed

## Testing

### Integration Tests
```bash
# Run simple integration tests
python3 test_integration_simple.py

# Run comprehensive tests (requires Docker)
docker compose down && docker compose build --no-cache && docker compose up -d
python3 test_accurate_token_counter.py
```

### Test Coverage
- Configuration validation
- File structure verification
- Function signature validation
- Requirements checking
- Docker integration

## Monitoring

### Metrics to Monitor
1. **Token Count Accuracy**: Compare estimated vs actual tokens
2. **Cache Performance**: Hit ratio and cache size
3. **Performance Impact**: Latency measurements
4. **Error Rates**: Fallback frequency and types

### Debugging
```python
# Get cache statistics
from accurate_token_counter import get_token_counter
counter = get_token_counter()
stats = counter.get_cache_stats()
print(f"Cache hit ratio: {stats['text_cache_hit_ratio']:.2%}")

# Clear cache if needed
counter.clear_cache()
```

## Future Enhancements

### Potential Improvements
1. **Model-Specific Encodings**: Support for different tokenizer variants
2. **Streaming Token Counting**: Real-time token counting during generation
3. **Advanced Caching**: Persistent cache across restarts
4. **Token Budget Management**: Automatic context management based on token budgets

### Configuration Options
- Model-specific tokenizer selection
- Custom token calculation strategies
- Advanced caching policies
- Performance tuning parameters

## Troubleshooting

### Common Issues

1. **tiktoken Import Error**
   - Solution: Ensure `tiktoken>=0.5.0` is installed
   - Fallback: System will use character-based estimation

2. **High Memory Usage**
   - Solution: Reduce `TIKTOKEN_CACHE_SIZE`
   - Monitor: Check cache statistics regularly

3. **Performance Issues**
   - Solution: Enable logging to identify bottlenecks
   - Optimize: Adjust cache size and configuration

4. **Inaccurate Token Counts**
   - Solution: Enable logging to debug counting process
   - Validate: Compare with upstream API token counts

### Debug Commands
```bash
# Check configuration
grep -E "(ENABLE_ACCURATE_TOKEN_COUNTING|TIKTOKEN_)" .env

# Monitor logs
docker compose logs -f | grep TOKEN_COUNTER

# Test API token counting
curl -X POST "http://localhost:8000/v1/messages/count_tokens" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $SERVER_API_KEY" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

## Conclusion

The accurate token counting system provides precise token estimation while maintaining backward compatibility and performance. The implementation is designed to be robust, configurable, and easily extensible for future enhancements.

For questions or issues, refer to the test files and integration examples provided in this documentation.