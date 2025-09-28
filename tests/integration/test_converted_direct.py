#!/usr/bin/env python3
"""Test converted payload with upstream"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def test_converted_payload():
    """Test the converted payload format with upstream"""
    api_key = os.getenv("SERVER_API_KEY")
    openai_base = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
    
    small_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yAAAAABJRU5ErkJggg=="
    
    # Test the converted format that our conversion function produces
    converted_payload = {
        "model": "glm-4.5v",
        "messages": [
            {
                "role": "user",
                "content": f"What do you see in this image? data:image/png;base64,{small_png_base64}"
            }
        ],
        "max_tokens": 100
    }
    
    print("🔄 Testing converted payload format:")
    print(json.dumps(converted_payload, indent=2))
    
    try:
        response = requests.post(
            f"{openai_base.rstrip('/')}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=converted_payload,
            timeout=30
        )
        
        print(f"\n📤 Status: {response.status_code}")
        try:
            response_data = response.json()
            if response.status_code == 200:
                print(f"✅ Success!")
                print(f"Model: {response_data.get('model', 'unknown')}")
                if 'choices' in response_data and response_data['choices']:
                    content = response_data['choices'][0].get('message', {}).get('content', '')[:200]
                    print(f"Response: {content}...")
            else:
                print(f"❌ Error: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response (raw): {response.text[:300]}...")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_converted_payload()