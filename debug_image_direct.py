#!/usr/bin/env python3
"""Debug image payload to OpenAI endpoint"""

import requests
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def debug_image_payload():
    """Test what happens when we send an image to OpenAI endpoint"""
    api_key = os.getenv("SERVER_API_KEY")
    openai_base = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
    
    print(f"📝 Testing OpenAI endpoint with image: {openai_base}")
    
    # Create a small test image (1x1 pixel PNG)
    small_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yAAAAABJRU5ErkJggg=="
    
    # Test different image formats that might be supported
    test_payloads = [
        {
            "name": "OpenAI format with image_url",
            "payload": {
                "model": "glm-4.5",  # Using working model
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What do you see in this image?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{small_png_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 100
            }
        },
        {
            "name": "Simple image format",
            "payload": {
                "model": "glm-4.5",
                "messages": [
                    {
                        "role": "user", 
                        "content": f"data:image/png;base64,{small_png_base64}"
                    }
                ],
                "max_tokens": 100
            }
        },
        {
            "name": "Try glm-4.5v model with image_url format",
            "payload": {
                "model": "glm-4.5v",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What do you see?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{small_png_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 100
            }
        },
        {
            "name": "Try glm-4.5v with simple format",
            "payload": {
                "model": "glm-4.5v",
                "messages": [
                    {
                        "role": "user", 
                        "content": f"What do you see? data:image/png;base64,{small_png_base64}"
                    }
                ],
                "max_tokens": 100
            }
        }
    ]
    
    for test_case in test_payloads:
        print(f"\n🔍 Testing: {test_case['name']}")
        test_direct_openai(openai_base, test_case['payload'], api_key)

def test_direct_openai(base_url, payload, api_key):
    """Test direct request to OpenAI endpoint"""
    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
            timeout=30
        )
        
        print(f"  Status: {response.status_code}")
        try:
            response_data = response.json()
            if response.status_code == 200:
                print(f"  ✅ Success! Model: {response_data.get('model', 'unknown')}")
                if 'choices' in response_data and response_data['choices']:
                    content = response_data['choices'][0].get('message', {}).get('content', '')[:100]
                    print(f"  Response: {content}...")
            else:
                print(f"  ❌ Error: {json.dumps(response_data, indent=2)}")
        except:
            print(f"  Response (raw): {response.text[:300]}...")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    debug_image_payload()