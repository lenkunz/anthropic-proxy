#!/usr/bin/env python3
"""
Compare streaming vs non-streaming responses
"""

import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def test_non_streaming():
    print("🧪 Non-streaming test...")
    
    payload = {
        "model": "glm-4.5-openai",
        "max_tokens": 50,
        "stream": False,  # Non-streaming
        "messages": [{"role": "user", "content": "Say hello"}]
    }
    
    response = requests.post(f"{BASE_URL}/v1/messages", headers=HEADERS, json=payload, timeout=15)
    
    print(f"📥 Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        content = result.get('content', [])
        if content and len(content) > 0:
            text = content[0].get('text', '') if content[0].get('type') == 'text' else ''
            print(f"✅ Non-streaming content: '{text[:100]}...'")
            return True
        else:
            print(f"❌ No content in non-streaming response")
            print(f"   Response: {json.dumps(result, indent=2)[:300]}...")
            return False
    else:
        print(f"❌ Non-streaming failed: {response.text}")
        return False

if __name__ == "__main__":
    print("🔍 Non-streaming vs Streaming Comparison")
    print("=" * 45)
    
    non_streaming_ok = test_non_streaming()
    
    if non_streaming_ok:
        print("\n💡 Non-streaming works, so the issue is specifically with streaming.")
        print("   The stream may be closing before content is sent.")
    else:
        print("\n💡 Both streaming and non-streaming have issues.")
        print("   This suggests a broader problem with the routing/conversion.")