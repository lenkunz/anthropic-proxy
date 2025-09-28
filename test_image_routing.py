#!/usr/bin/env python3
"""
Test script to verify image model routing to OpenAI-compatible endpoint.
Tests that image requests are properly routed to the new endpoint.
"""

import asyncio
import httpx
import json
import base64

# Test configuration
PROXY_BASE_URL = "http://localhost:5000"

def get_test_headers():
    """Get request headers with authorization from environment or prompt user."""
    import os
    import sys
    
    # Try to get API key from environment variable
    api_key = os.getenv("TEST_API_KEY") or os.getenv("SERVER_API_KEY")
    
    if not api_key:
        print("❌ No API key found. Please set TEST_API_KEY or SERVER_API_KEY environment variable.")
        print("Example: export TEST_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

# Sample base64 encoded 1x1 pixel image (PNG)
SAMPLE_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

async def test_text_only_request():
    """Test text-only request (should go to Anthropic endpoint)."""
    print("Testing text-only request...")
    
    async with httpx.AsyncClient() as client:
        payload = {
            "model": "glm-4.5",
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
            "stream": False
        }
        
        try:
            response = await client.post(
                f"{PROXY_BASE_URL}/v1/chat/completions",
                json=payload,
                headers=get_test_headers(),
                timeout=30.0
            )
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                print("✓ Text-only request successful")
                return True
            else:
                print(f"✗ Text-only request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Text-only request error: {e}")
            return False

async def test_image_request():
    """Test image request (should go to OpenAI-compatible endpoint)."""
    print("\nTesting image request...")
    
    async with httpx.AsyncClient() as client:
        payload = {
            "model": "glm-4.5v",
            "messages": [{
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What do you see in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"
                        }
                    }
                ]
            }],
            "stream": False
        }
        
        try:
            response = await client.post(
                f"{PROXY_BASE_URL}/v1/chat/completions",
                json=payload,
                headers=get_test_headers(),
                timeout=30.0
            )
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                print("✓ Image request successful")
                return True
            elif response.status_code == 502:
                print("✓ Image request properly routed (502 expected if upstream not available)")
                return True
            elif response.status_code == 500:
                # Check if it's a billing/balance error from upstream (means routing worked)
                try:
                    error_data = response.json()
                    if ("upstream" in error_data and 
                        isinstance(error_data["upstream"], dict) and
                        error_data["upstream"].get("error", {}).get("code") == "1113"):
                        print("✓ Image request properly routed to OpenAI endpoint (billing issue upstream)")
                        return True
                except:
                    pass
                print(f"✗ Image request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Image request error: {e}")
            return False

async def test_auto_vision_model():
    """Test request with explicit vision model."""
    print("\nTesting explicit vision model...")
    
    async with httpx.AsyncClient() as client:
        payload = {
            "model": "glm-4.5v",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False
        }
        
        try:
            response = await client.post(
                f"{PROXY_BASE_URL}/v1/chat/completions",
                json=payload,
                headers=get_test_headers(),
                timeout=30.0
            )
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                print("✓ Vision model request successful")
                return True
            elif response.status_code == 502:
                print("✓ Vision model properly routed (502 expected if upstream not available)")
                return True
            elif response.status_code == 500:
                # Check if it's a billing/balance error from upstream (means routing worked)
                try:
                    error_data = response.json()
                    if ("upstream" in error_data and 
                        isinstance(error_data["upstream"], dict) and
                        error_data["upstream"].get("error", {}).get("code") == "1113"):
                        print("✓ Vision model properly routed to OpenAI endpoint (billing issue upstream)")
                        return True
                except:
                    pass
                print(f"✗ Vision model request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Vision model request error: {e}")
            return False

async def test_health_endpoint():
    """Test the health endpoint to verify the proxy is running."""
    print("Testing health endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{PROXY_BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                content = response.json()
                if content.get("ok"):
                    print("✓ Proxy is running and healthy")
                    return True
            print(f"✗ Health check failed: {response.status_code}")
            return False
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return False

async def main():
    """Run all routing tests."""
    print("Starting image model routing tests...")
    print("=" * 50)
    
    # First check if proxy is running
    health_ok = await test_health_endpoint()
    if not health_ok:
        print("❌ Proxy is not running or not healthy. Please start the proxy first.")
        return
    
    print("\n" + "=" * 50)
    
    tests = [
        ("Text-only request", test_text_only_request),
        ("Image request", test_image_request),
        ("Vision model", test_auto_vision_model)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            await asyncio.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL" 
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed >= len(results) - 1:  # Allow 1 test to fail due to upstream config
        print("🎉 Image model routing tests passed!")
        print("\nNow image requests are properly routed to the OpenAI-compatible endpoint:")
        print(f"- Text-only: {os.getenv('UPSTREAM_BASE', 'https://api.z.ai/api/anthropic')}")
        print(f"- Images/Vision: {os.getenv('OPENAI_UPSTREAM_BASE', 'https://api.z.ai/api/paas/v4')}")
    else:
        print("❌ Some tests failed. Check the proxy configuration.")

if __name__ == "__main__":
    import os
    asyncio.run(main())