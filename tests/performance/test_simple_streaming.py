#!/usr/bin/env python3
"""
Simple streaming test to verify content flow
"""

import json
import requests
from dotenv import load_dotenv
import os
import time

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def simple_streaming_test():
    print("🧪 Simple streaming test...")
    
    # Test with Anthropic routing first (known to work)
    payload = {
        "model": "glm-4.5",  # Should route to Anthropic
        "max_tokens": 50, 
        "stream": True,
        "messages": [{"role": "user", "content": "Count: 1, 2, 3"}]
    }
    
    print(f"📤 Testing Anthropic routing (glm-4.5)...")
    response = requests.post(f"{BASE_URL}/v1/messages", headers=HEADERS, json=payload, stream=True, timeout=15)
    
    print(f"📥 Status: {response.status_code}")
    
    content_found = False
    lines_received = 0
    
    for line in response.iter_lines(decode_unicode=True):
        if line:
            lines_received += 1
            print(f"   📦 Line {lines_received}: {line[:120]}...")
            if 'content' in line or 'text' in line:
                content_found = True
            if lines_received >= 5:  # Limit output
                break
    
    print(f"   Result: {'✅ Content found' if content_found else '❌ No content'}")
    
    return content_found

def test_openai_routing():
    print("\n🧪 OpenAI routing streaming test...")
    
    payload = {
        "model": "glm-4.5-openai",  # Force OpenAI routing
        "max_tokens": 30,
        "stream": True,
        "messages": [{"role": "user", "content": "Hello"}]
    }
    
    print(f"📤 Testing OpenAI routing (glm-4.5-openai)...")
    response = requests.post(f"{BASE_URL}/v1/messages", headers=HEADERS, json=payload, stream=True, timeout=15)
    
    print(f"📥 Status: {response.status_code}")
    
    content_found = False
    lines_received = 0
    
    for line in response.iter_lines(decode_unicode=True):
        if line:
            lines_received += 1
            print(f"   📦 Line {lines_received}: {line[:120]}...")
            if 'content' in line or 'text' in line:
                content_found = True
            if lines_received >= 5:
                break
    
    print(f"   Result: {'✅ Content found' if content_found else '❌ No content'}")
    
    return content_found

def main():
    print("🔍 Simple Streaming Content Test")
    print("=" * 40)
    
    anthropic_ok = simple_streaming_test()
    openai_ok = test_openai_routing()
    
    print(f"\n📊 Results:")
    print(f"   Anthropic streaming: {'✅ WORKING' if anthropic_ok else '❌ NO CONTENT'}")
    print(f"   OpenAI streaming: {'✅ WORKING' if openai_ok else '❌ NO CONTENT'}")
    
    if not anthropic_ok and not openai_ok:
        print("\n💡 Both endpoints show no content - this might be an upstream issue.")
    elif anthropic_ok and not openai_ok:
        print("\n💡 Anthropic works but OpenAI doesn't - message conversion issue.")
    elif openai_ok and not anthropic_ok:
        print("\n💡 OpenAI works but Anthropic doesn't - Anthropic endpoint issue.")
    else:
        print("\n✅ Both endpoints working - stream closure error is resolved!")

if __name__ == "__main__":
    main()