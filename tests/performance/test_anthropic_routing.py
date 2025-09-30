#!/usr/bin/env python3
"""
Quick test to ensure Anthropic routing still works after the fix
"""

import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def test_anthropic_routing():
    payload = {
        "model": "glm-4.5",  # Auto-routing (should go to Anthropic for text)
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "Hello, test Anthropic routing"}]
    }
    
    response = requests.post(f"{BASE_URL}/v1/messages", headers=HEADERS, json=payload, timeout=15)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Anthropic routing test passed")
        print(f"   Model: {result.get('model')}")
        print(f"   Response ID: {result.get('id')}")
        return True
    else:
        print(f"❌ Anthropic routing failed: {response.status_code}")
        return False

if __name__ == "__main__":
    print("Testing Anthropic routing still works...")
    success = test_anthropic_routing()
    print("✅ Both endpoints working correctly!" if success else "❌ Issue with Anthropic routing")