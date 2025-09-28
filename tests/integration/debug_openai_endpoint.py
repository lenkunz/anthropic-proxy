#!/usr/bin/env python3
"""Debug what payload is sent to OpenAI endpoint"""

import requests
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def debug_openai_payload():
    """Test what happens when we send a minimal request to OpenAI endpoint"""
    api_key = os.getenv("SERVER_API_KEY")
    openai_base = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
    
    print(f"📝 Testing OpenAI endpoint: {openai_base}")
    print(f"📝 Using API key: {api_key[:10]}...")
    
    # Test 1: Simple text request to OpenAI endpoint directly
    print("\n🔍 Testing direct OpenAI endpoint with text...")
    simple_payload = {
        "model": "glm-4.5",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 10
    }
    
    test_direct_openai(openai_base, simple_payload, api_key)
    
    # Test 2: Try different model names that might be supported
    print("\n🔍 Testing different model names...")
    for model_name in ["gpt-4", "gpt-4o", "glm-4v", "claude-3-sonnet", "claude-3-haiku"]:
        test_payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        }
        print(f"  Testing model: {model_name}")
        test_direct_openai(openai_base, test_payload, api_key, silent=True)

def test_direct_openai(base_url, payload, api_key, silent=False):
    """Test direct request to OpenAI endpoint"""
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
            timeout=10
        )
        
        if not silent:
            print(f"  Status: {response.status_code}")
            try:
                response_data = response.json()
                print(f"  Response: {json.dumps(response_data, indent=2)[:300]}...")
            except:
                print(f"  Response (raw): {response.text[:300]}...")
        
        if response.status_code == 200:
            if not silent:
                print(f"  ✅ Request successful!")
            return True
        elif response.status_code == 400:
            if not silent:
                print(f"  ❌ Bad request - check parameters")
            return False
        else:
            if not silent:
                print(f"  ⚠️  Status {response.status_code}")
            return False
            
    except Exception as e:
        if not silent:
            print(f"  ❌ Error: {e}")
        return False

if __name__ == "__main__":
    debug_openai_payload()