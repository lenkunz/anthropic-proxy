#!/usr/bin/env python3

"""
Test token validation functionality with configurable thresholds
Tests both OpenAI and Anthropic endpoints with proper scaling
"""

import json
import time
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"

if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_token_validation_openai():
    """Test token validation on OpenAI endpoint (returns real tokens)"""
    print("\n🧪 Testing token validation - OpenAI endpoint (glm-4.5-openai)")
    
    # Use a consistent test message for predictable token count
    payload = {
        "model": "glm-4.5-openai",
        "messages": [
            {"role": "user", "content": "Hello! This is a test message for token validation. Please respond briefly."}
        ],
        "max_tokens": 50,
        "temperature": 0
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions", 
        headers=headers, 
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        print(f"✅ Request successful")
        print(f"📊 Usage: {prompt_tokens} prompt + {completion_tokens} completion = {usage.get('total_tokens', 0)} total")
        print(f"🔍 Input tokens should be tiktoken estimate (accurate)")
        
        # Check if input tokens are reasonable (tiktoken estimates are usually accurate)
        if 15 <= prompt_tokens <= 30:  # Expected range for our test message
            print(f"✅ Input token count looks accurate: {prompt_tokens}")
        else:
            print(f"⚠️  Input token count seems off: {prompt_tokens} (expected ~20)")
    else:
        print(f"❌ Request failed: {response.text}")

def test_token_validation_anthropic():
    """Test token validation on Anthropic endpoint (returns scaled tokens, should be converted back)"""
    print("\n🧪 Testing token validation - Anthropic endpoint (glm-4.5-anthropic)")
    
    # Use the same test message
    payload = {
        "model": "glm-4.5-anthropic",
        "messages": [
            {"role": "user", "content": "Hello! This is a test message for token validation. Please respond briefly."}
        ],
        "max_tokens": 50,
        "temperature": 0
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions", 
        headers=headers, 
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        print(f"✅ Request successful")
        print(f"📊 Usage: {prompt_tokens} prompt + {completion_tokens} completion = {usage.get('total_tokens', 0)} total")
        print(f"🔍 Input tokens should be tiktoken estimate with Anthropic scaling applied")
        
        # With Anthropic scaling (200k/128k ≈ 1.56x), expect higher values
        if 20 <= prompt_tokens <= 50:  # Expected range after scaling
            print(f"✅ Input token count looks scaled correctly: {prompt_tokens}")
        else:
            print(f"⚠️  Input token count scaling seems off: {prompt_tokens} (expected ~30 after scaling)")
    else:
        print(f"❌ Request failed: {response.text}")

def test_token_validation_anthropic_messages():
    """Test token validation on /v1/messages Anthropic endpoint"""
    print("\n🧪 Testing token validation - /v1/messages Anthropic endpoint")
    
    payload = {
        "model": "glm-4.5",
        "messages": [
            {"role": "user", "content": "Hello! This is a test message for token validation. Please respond briefly."}
        ],
        "max_tokens": 50
    }
    
    headers_anthropic = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/messages", 
        headers=headers_anthropic, 
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        print(f"✅ Request successful")
        print(f"📊 Usage: {input_tokens} input + {output_tokens} output tokens")
        print(f"🔍 Input tokens should be tiktoken estimate (scaled for Anthropic format)")
        
        # For /v1/messages returning Anthropic format, expect tiktoken estimate
        if 15 <= input_tokens <= 30:
            print(f"✅ Input token count looks accurate: {input_tokens}")
        else:
            print(f"⚠️  Input token count seems off: {input_tokens} (expected ~20)")
    else:
        print(f"❌ Request failed: {response.text}")

def main():
    print("🚀 Token Validation Test Suite")
    print("=" * 50)
    
    print(f"🔧 Configuration:")
    print(f"   Base URL: {BASE_URL}")
    print(f"   API Key: {'*' * (len(API_KEY) - 4) + API_KEY[-4:] if len(API_KEY) > 4 else 'Set'}")
    
    # Test different endpoints
    test_token_validation_openai()
    test_token_validation_anthropic() 
    test_token_validation_anthropic_messages()
    
    print("\n" + "=" * 50)
    print("🎯 Summary:")
    print("   • OpenAI endpoint should return accurate tiktoken estimates")
    print("   • Anthropic endpoint should return scaled tiktoken estimates") 
    print("   • /v1/messages should return tiktoken estimates in Anthropic format")
    print("   • All validation should happen against real tokens (scaled down for comparison)")

if __name__ == "__main__":
    main()