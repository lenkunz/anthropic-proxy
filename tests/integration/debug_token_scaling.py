#!/usr/bin/env python3
"""
Test token scaling bug with glm-4.5-anthropic model.
"""

import requests
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"

if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env")
    exit(1)

def test_token_scaling():
    """Test token scaling for glm-4.5-anthropic model"""
    print("🧪 Testing Token Scaling Bug with glm-4.5-anthropic")
    print("=" * 60)
    
    test_message = "Write a detailed explanation of quantum computing in exactly 50 words."
    
    # Test glm-4.5-anthropic (should route to Anthropic endpoint, return OpenAI format with scaled tokens)
    print("📤 Testing glm-4.5-anthropic model...")
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "glm-4.5-anthropic",
            "messages": [{"role": "user", "content": test_message}],
            "max_tokens": 100,
            "stream": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        usage = data.get("usage", {})
        
        print(f"✅ Response received")
        print(f"📊 Usage tokens:")
        print(f"   • Prompt tokens: {usage.get('prompt_tokens')}")
        print(f"   • Completion tokens: {usage.get('completion_tokens')}")
        print(f"   • Total tokens: {usage.get('total_tokens')}")
        
        # Check if tokens are around 200k (bug) or 131k (correct)
        total = usage.get('total_tokens', 0)
        if total > 180000:
            print(f"❌ BUG DETECTED: Total tokens ({total}) are ~200k range")
            print("   Expected: ~131k range (scaled down from Anthropic 200k)")
            print("   This indicates scaling is NOT being applied")
        elif total > 100000 and total < 140000:
            print(f"✅ SCALING WORKING: Total tokens ({total}) are in ~131k range")
            print("   This indicates proper scaling from Anthropic 200k → OpenAI 131k")
        else:
            print(f"🤔 UNEXPECTED: Total tokens ({total}) are in unexpected range")
        
        # Show the scaling math
        print(f"\n🧮 Expected scaling math:")
        print(f"   • Anthropic endpoint returns tokens based on 200k context")
        print(f"   • OpenAI client expects tokens based on 131k context")  
        print(f"   • Scale factor = 128000 / 200000 = 0.640")
        print(f"   • If Anthropic returned 200k tokens → Should show ~131k to client")
        
        return {"success": True, "tokens": total}
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(f"Error: {response.text}")
        return {"success": False, "error": response.text}

def main():
    try:
        # Check if proxy is running
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print(f"❌ Proxy not responding at {BASE_URL}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to proxy: {e}")
        return
    
    result = test_token_scaling()
    
    print(f"\n{'='*60}")
    if result["success"]:
        print("🎯 Test completed - check results above for bug detection")
    else:
        print("❌ Test failed - check proxy configuration and API keys")

if __name__ == "__main__":
    main()