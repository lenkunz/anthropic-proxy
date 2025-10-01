#!/usr/bin/env python3
"""
Example usage of the Anthropic Proxy API endpoints.
Demonstrates both OpenAI-compatible and Anthropic-native endpoints.
"""

import asyncio
import httpx
import json
import os
import requests
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path and load environment from project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

# Configuration
BASE_URL = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY", "your-api-key-here")

def test_text_completion():
    """Example: Text completion using glm-4.6"""
    print("🔤 Testing text completion...")
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "glm-4.6",
            "messages": [
                {"role": "user", "content": "Write a haiku about programming."}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        
        print(f"✅ Text completion successful")
        print(f"   Content: {content}")
        print(f"   Tokens: {usage.get('prompt_tokens')} + {usage.get('completion_tokens')} = {usage.get('total_tokens')}")
        print(f"   → Routed to: Anthropic endpoint (text model)")
        return True
    else:
        print(f"❌ Text completion failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def test_vision_request():
    """Example: Vision request with image (routes to OpenAI endpoint)"""
    print("🖼️  Testing vision request...")
    
    # Create a simple test image (1x1 pixel PNG)
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "glm-4.6",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What do you see in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{test_image_b64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 100
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        
        print(f"✅ Vision request successful")
        print(f"   Content: {content[:100]}...")
        print(f"   Tokens: {usage.get('prompt_tokens')} + {usage.get('completion_tokens')} = {usage.get('total_tokens')}")
        print(f"   → Routed to: OpenAI endpoint (vision model)")
        return True
    else:
        print(f"❌ Vision request failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def test_token_counting():
    """Example: Token counting"""
    print("🔢 Testing token counting...")
    
    response = requests.post(
        f"{BASE_URL}/v1/messages/count_tokens",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "glm-4.6",
            "messages": [
                {"role": "user", "content": "How many tokens is this message?"}
            ]
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token_count = data.get("input_tokens", 0)
        
        print(f"✅ Token counting successful")
        print(f"   Token count: {token_count}")
        return True
    else:
        print(f"❌ Token counting failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def test_models_endpoint():
    """Example: List available models"""
    print("📋 Testing models endpoint...")
    
    response = requests.get(
        f"{BASE_URL}/v1/models",
        headers={"Authorization": f"Bearer {API_KEY}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        models = [model["id"] for model in data.get("data", [])]
        
        print(f"✅ Models endpoint successful")
        print(f"   Available models: {models}")
        print(f"   → Single unified model with smart routing")
        return True
    else:
        print(f"❌ Models endpoint failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def main():
    """Run all examples"""
    print("🚀 Anthropic Proxy Usage Examples")
    print("=" * 50)
    print(f"Using API Key: {API_KEY[:20]}..." if API_KEY and len(API_KEY) > 20 else f"Using API Key: {API_KEY}")
    print(f"Proxy URL: {BASE_URL}")
    print("=" * 50)
    
    examples = [
        ("Models List", test_models_endpoint),
        ("Text Completion", test_text_completion),
        ("Token Counting", test_token_counting),
        ("Vision Request", test_vision_request),
    ]
    
    passed = 0
    total = len(examples)
    
    for name, test_func in examples:
        print(f"\n🔍 {name}:")
        if test_func():
            passed += 1
        print("-" * 30)
    
    print(f"\n📊 Results: {passed}/{total} examples successful")
    
    if passed == total:
        print("🎉 All examples worked! Your proxy is ready to use.")
        print("\n💡 Key Features Demonstrated:")
        print("   • Single glm-4.6 model with content-based routing")
        print("   • Text requests → Anthropic endpoint")
        print("   • Image requests → OpenAI endpoint")
        print("   • Configurable token scaling and counting")
        print("   • OpenAI API compatibility")
    else:
        print(f"⚠️  {total - passed} example(s) failed. Check your configuration.")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure Docker container is running: docker compose up -d")
        print("   2. Check SERVER_API_KEY in .env file")
        print("   3. Verify z.ai API key is valid")

if __name__ == "__main__":
    main()