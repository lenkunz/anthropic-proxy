#!/usr/bin/env python3
"""
Shared test configuration and utilities for Anthropic Proxy tests.
This file provides common setup, constants, and helper functions for all test files.
"""

import os
import sys
import asyncio
import httpx
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Optional, Any

# Add project root to path so tests can import from parent directory
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment from project root .env file
load_dotenv(project_root / ".env")

# ---------------------- Test Configuration ----------------------

# API Configuration
PROXY_BASE_URL = "http://localhost:5000"
DIRECT_BASE_URL = os.getenv("UPSTREAM_BASE", "https://api.z.ai/api/anthropic")
API_KEY = os.getenv("SERVER_API_KEY")

# Test Data Configuration
TEST_MAX_TOKENS = 50  # Keep test responses short for speed
TEST_TIMEOUT = 60.0   # Timeout for test requests

# Test Models
TEST_MODELS = [
    "glm-4.5",           # Auto-routing
    "glm-4.5-openai",    # Force OpenAI endpoint  
    "glm-4.5-anthropic"  # Force Anthropic endpoint
]

# ---------------------- Test Helpers ----------------------

def validate_environment() -> bool:
    """Validate that required environment variables are set."""
    if not API_KEY:
        print("❌ ERROR: SERVER_API_KEY not found in .env file")
        print("   Please ensure .env file exists in project root with:")
        print("   SERVER_API_KEY=your_api_key_here")
        return False
    return True

def get_proxy_headers() -> Dict[str, str]:
    """Get standard headers for proxy requests."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }

def get_direct_headers() -> Dict[str, str]:
    """Get standard headers for direct API requests."""
    headers = get_proxy_headers()
    headers["anthropic-version"] = "2023-06-01"
    return headers

def create_test_payload(message: str = "Test message", model: str = "glm-4.5", max_tokens: int = None) -> Dict[str, Any]:
    """Create a standard test payload."""
    return {
        "model": model,
        "max_tokens": max_tokens or TEST_MAX_TOKENS,
        "messages": [{"role": "user", "content": message}]
    }

def create_image_test_payload(model: str = "glm-4.5", max_tokens: int = None) -> Dict[str, Any]:
    """Create a test payload with image."""
    # Simple 1x1 pixel PNG in base64
    tiny_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    return {
        "model": model,
        "max_tokens": max_tokens or TEST_MAX_TOKENS,
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{tiny_png}"}}
                ]
            }
        ]
    }

async def check_proxy_health() -> bool:
    """Check if the proxy service is running and healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PROXY_BASE_URL}/v1/models")
            return response.status_code == 200
    except Exception:
        return False

async def wait_for_proxy(max_wait: int = 30) -> bool:
    """Wait for proxy to become healthy."""
    print(f"⏳ Waiting for proxy to become healthy (max {max_wait}s)...")
    
    for i in range(max_wait):
        if await check_proxy_health():
            print("✅ Proxy is healthy")
            return True
        
        if i == 0:
            print("   Proxy not ready, waiting...")
        elif i % 5 == 0:
            print(f"   Still waiting... ({i}s elapsed)")
        
        await asyncio.sleep(1)
    
    print(f"❌ Proxy did not become healthy within {max_wait}s")
    print("   Try: docker compose up -d")
    return False

# ---------------------- Test Assertion Helpers ----------------------

def assert_response_structure(response_data: Dict[str, Any], endpoint_type: str = "messages"):
    """Assert that response has the expected structure."""
    if endpoint_type == "messages":
        # Anthropic-style response
        assert "id" in response_data, "Response missing 'id' field"
        assert "content" in response_data, "Response missing 'content' field"
        assert "role" in response_data, "Response missing 'role' field"
        assert response_data["role"] == "assistant", f"Expected role 'assistant', got {response_data['role']}"
        
    elif endpoint_type == "chat_completions":
        # OpenAI-style response
        assert "choices" in response_data, "Response missing 'choices' field"
        assert len(response_data["choices"]) > 0, "Response has no choices"
        
        choice = response_data["choices"][0]
        assert "message" in choice, "Choice missing 'message' field"
        assert choice["message"]["role"] == "assistant", f"Expected role 'assistant', got {choice['message']['role']}"

def assert_valid_streaming_chunk(chunk_data: Dict[str, Any], endpoint_type: str = "messages"):
    """Assert that streaming chunk has valid structure."""
    if endpoint_type == "messages":
        # Anthropic-style streaming
        assert "type" in chunk_data, "Chunk missing 'type' field"
        valid_types = ["message_start", "content_block_start", "content_block_delta", "content_block_stop", "message_stop"]
        assert chunk_data["type"] in valid_types, f"Invalid chunk type: {chunk_data['type']}"
        
    elif endpoint_type == "chat_completions":
        # OpenAI-style streaming
        assert "choices" in chunk_data, "Streaming chunk missing 'choices' field"

# ---------------------- Test Decorators ----------------------

def requires_proxy(func):
    """Decorator to ensure proxy is running before test."""
    async def wrapper(*args, **kwargs):
        if not validate_environment():
            return False
        
        if not await check_proxy_health():
            print("❌ Proxy is not running. Start with: docker compose up -d")
            return False
        
        return await func(*args, **kwargs)
    
    return wrapper

def skip_if_no_api_key(func):
    """Decorator to skip test if API key is not available."""
    async def wrapper(*args, **kwargs):
        if not validate_environment():
            print("⏭️  Skipping test - no API key")
            return True  # Return True to indicate test was skipped, not failed
        
        return await func(*args, **kwargs)
    
    return wrapper

# ---------------------- Performance Helpers ----------------------

class PerformanceTimer:
    """Context manager for timing operations."""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.duration = time.perf_counter() - self.start_time
        print(f"⏱️  {self.name}: {self.duration:.3f}s")

# ---------------------- Debug Helpers ----------------------

def print_test_header(test_name: str, description: str = ""):
    """Print a formatted test header."""
    print("\n" + "="*60)
    print(f"🧪 {test_name}")
    if description:
        print(f"   {description}")
    print("="*60)

def print_test_result(success: bool, details: str = ""):
    """Print formatted test result."""
    if success:
        print(f"✅ TEST PASSED")
        if details:
            print(f"   {details}")
    else:
        print(f"❌ TEST FAILED")
        if details:
            print(f"   {details}")
    print()

# ---------------------- Exports ----------------------

__all__ = [
    # Configuration
    'PROXY_BASE_URL', 'DIRECT_BASE_URL', 'API_KEY', 'TEST_MODELS',
    'TEST_MAX_TOKENS', 'TEST_TIMEOUT',
    
    # Helpers
    'validate_environment', 'get_proxy_headers', 'get_direct_headers',
    'create_test_payload', 'create_image_test_payload',
    'check_proxy_health', 'wait_for_proxy',
    
    # Assertions
    'assert_response_structure', 'assert_valid_streaming_chunk',
    
    # Decorators
    'requires_proxy', 'skip_if_no_api_key',
    
    # Performance
    'PerformanceTimer',
    
    # Debug
    'print_test_header', 'print_test_result'
]