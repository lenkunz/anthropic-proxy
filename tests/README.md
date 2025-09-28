# Testing Guide for Anthropic Proxy

This directory contains all testing scripts, benchmarks, and examples for the Anthropic Proxy service.

## 📁 Directory Structure

```
tests/
├── README.md              # This file - comprehensive testing guide
├── unit/                  # Unit tests for specific functionality
├── integration/           # End-to-end integration tests
├── benchmarks/            # Performance benchmarking tools
└── conftest.py            # Shared test configuration
```

## 🚀 Quick Start

### Prerequisites

1. **Environment Setup**: Ensure you have a `.env` file in the project root with:
   ```bash
   SERVER_API_KEY=your_api_key_here
   UPSTREAM_BASE=https://api.z.ai/api/anthropic
   OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4
   ```

2. **Start the Proxy**: 
   ```bash
   docker compose up -d
   ```

3. **Verify Service**: Check that the proxy is running:
   ```bash
   curl http://localhost:5000/v1/models
   ```

### Running Tests

#### All Tests (Recommended)
```bash
# Run all tests with comprehensive output
python tests/run_all_tests.py
```

#### Individual Test Categories

**Unit Tests** (Fast, isolated functionality):
```bash
python tests/unit/test_model_variants.py
python tests/unit/test_image_detection.py
python tests/unit/test_conversion.py
```

**Integration Tests** (End-to-end API testing):
```bash
python tests/integration/test_messages_endpoint.py
python tests/integration/test_streaming.py
python tests/integration/test_error_handling.py
```

**Performance Benchmarks**:
```bash
# Quick performance check
python tests/benchmarks/quick_benchmark.py

# Comprehensive performance analysis
python tests/benchmarks/comprehensive_benchmark.py

# Detailed profiling
python tests/benchmarks/detailed_profiler.py
```

## 📊 Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests focusing on specific functionality:

- **`test_model_variants.py`** - Model variant routing logic
- **`test_image_detection.py`** - Image content detection
- **`test_conversion.py`** - OpenAI ↔ Anthropic format conversion
- **`test_token_scaling.py`** - Token count scaling logic

### Integration Tests (`tests/integration/`)

End-to-end tests that require running proxy service:

- **`test_messages_endpoint.py`** - `/v1/messages` endpoint functionality
- **`test_chat_completions.py`** - `/v1/chat/completions` endpoint
- **`test_streaming.py`** - Streaming response handling
- **`test_error_handling.py`** - Error response compatibility
- **`test_image_processing.py`** - Image upload and processing

### Benchmarks (`tests/benchmarks/`)

Performance testing and optimization tools:

- **`quick_benchmark.py`** - Fast performance validation (3 requests each)
- **`comprehensive_benchmark.py`** - Detailed performance analysis with concurrent load testing
- **`detailed_profiler.py`** - Low-level profiling to identify bottlenecks
- **`benchmark_proxy_overhead.py`** - Historical overhead analysis

## 🔧 Test Configuration

### Environment Variables

All test scripts automatically read from the `.env` file in the project root. Required variables:

```bash
# API Configuration
SERVER_API_KEY=your_api_key_here
UPSTREAM_BASE=https://api.z.ai/api/anthropic
OPENAI_UPSTREAM_BASE=https://api.z.ai/api/coding/paas/v4

# Optional Performance Tuning
HTTP_POOL_CONNECTIONS=20
HTTP_KEEPALIVE_CONNECTIONS=15
CONNECT_TIMEOUT=10.0
REQUEST_TIMEOUT=120.0
STREAM_TIMEOUT=300.0

# Debug Mode
DEBUG=false
```

### Test Data

Tests use minimal payloads for speed:
- **Text requests**: 50 tokens max
- **Image requests**: Small test images
- **Streaming**: Short responses for faster validation

## 📈 Performance Benchmarks

### Current Performance Metrics

Based on latest optimization (September 2025):

- **Proxy Overhead**: ~314ms (50% over direct API calls)
- **Improvement**: 78% reduction from initial 1400ms overhead
- **Connection Pooling**: ✅ Enabled and optimized
- **Function Caching**: ✅ LRU caches for hot paths

### Benchmark Interpretation

**Quick Benchmark Results**:
```
Proxy average:     ~900ms
Direct average:    ~600ms
Overhead:         +300ms (50%)
Status:           ✅ PRODUCTION READY
```

**Performance Expectations**:
- **< 100ms overhead**: Excellent
- **100-300ms overhead**: Good (current status)
- **> 500ms overhead**: Investigate optimization

## 🐛 Debugging Test Issues

### Common Problems

1. **"API key not found"**
   ```bash
   # Check .env file exists and contains SERVER_API_KEY
   ls -la .env
   grep SERVER_API_KEY .env
   ```

2. **"Connection refused"**
   ```bash
   # Ensure proxy is running
   docker compose ps
   curl http://localhost:5000/v1/models
   ```

3. **"Timeout errors"**
   ```bash
   # Check proxy logs
   docker compose logs anthropic-proxy
   ```

### Debug Mode

Enable detailed logging by setting in `.env`:
```bash
DEBUG=true
```

Then restart the proxy:
```bash
docker compose down && docker compose up -d
```

## 📝 Writing New Tests

### Test File Template

```python
#!/usr/bin/env python3
"""
Test description
"""

import asyncio
import os
from dotenv import load_dotenv
import httpx

# Load environment from project root
load_dotenv()

# Configuration
PROXY_BASE_URL = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY")

async def test_your_functionality():
    """Test function description"""
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    # Your test logic here
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{PROXY_BASE_URL}/your-endpoint",
            json={"your": "payload"},
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Add assertions
        
    return True

if __name__ == "__main__":
    result = asyncio.run(test_your_functionality())
    if result:
        print("✅ Test passed")
    else:
        print("❌ Test failed")
```

### Guidelines

1. **Always use async/await** for HTTP requests
2. **Load environment with `load_dotenv()`** at the top
3. **Validate API_KEY exists** before running tests
4. **Use clear test names** and descriptions
5. **Print progress and results** for user feedback
6. **Handle errors gracefully** with try/except

## 🔄 Continuous Testing

### Automated Test Running

Create a simple test runner in your workflow:

```bash
#!/bin/bash
# tests/run_quick_tests.sh

echo "🚀 Starting Anthropic Proxy Tests..."

# Start proxy if not running
if ! curl -s http://localhost:5000/v1/models > /dev/null; then
    echo "📦 Starting proxy..."
    docker compose up -d
    sleep 5
fi

# Run essential tests
echo "🧪 Running core functionality tests..."
python tests/integration/test_messages_endpoint.py
python tests/unit/test_model_variants.py

# Quick performance check
echo "📊 Running performance check..."
python tests/benchmarks/quick_benchmark.py

echo "✅ Test suite complete!"
```

### Performance Regression Detection

Monitor key metrics over time:
- Track proxy overhead percentage
- Alert if overhead > 100ms increase
- Validate connection pooling effectiveness

---

## 🆘 Support

- **Documentation**: See main project README.md and API_DOCUMENTATION.md
- **Issues**: Check Docker logs and enable DEBUG mode
- **Performance**: Run benchmarks to identify bottlenecks
- **Development**: Reference DEVELOPMENT.md for setup

**Happy Testing! 🎉**