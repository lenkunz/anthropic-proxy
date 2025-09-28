#!/usr/bin/env python3
"""
Quick test to compare upstream endpoints directly
"""

import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

# Direct upstream endpoints
ANTHROPIC_UPSTREAM = "https://api.z.ai/api/anthropic"
OPENAI_UPSTREAM = "https://api.z.ai/api/coding/paas/v4"

def test_anthropic_quick():
    """Quick test of Anthropic endpoint"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "What is 2+2?"}]
    }
    
    print("📤 Testing Anthropic endpoint...")
    try:
        response = requests.post(f"{ANTHROPIC_UPSTREAM}/v1/messages", headers=headers, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            print(f"✅ Success - Input: {usage.get('input_tokens')}, Output: {usage.get('output_tokens')}")
            return usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_openai_quick():
    """Quick test of OpenAI endpoint"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5v",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": "What is 2+2?"}],
        "temperature": 0.0
    }
    
    print("📤 Testing OpenAI endpoint...")
    try:
        response = requests.post(f"{OPENAI_UPSTREAM}/chat/completions", headers=headers, json=payload, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            print(f"✅ Success - Prompt: {usage.get('prompt_tokens')}, Completion: {usage.get('completion_tokens')}, Total: {usage.get('total_tokens')}")
            return usage.get('total_tokens', 0)
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def main():
    print("🧪 Quick Upstream Endpoint Test")
    print("=" * 40)
    
    anthropic_tokens = test_anthropic_quick()
    print()
    openai_tokens = test_openai_quick()
    
    print(f"\n📊 Results:")
    print(f"Anthropic: {anthropic_tokens} tokens")
    print(f"OpenAI:    {openai_tokens} tokens")
    
    if anthropic_tokens and openai_tokens:
        ratio = anthropic_tokens / openai_tokens
        print(f"Ratio:     {ratio:.3f}")
        
        if abs(ratio - 1.0) < 0.1:
            print("✅ Very similar token counts")
        else:
            print("❓ Different token counting methods")

if __name__ == "__main__":
    main()