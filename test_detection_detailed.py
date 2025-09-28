#!/usr/bin/env python3
"""Test image detection with detailed logging"""

import requests
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def test_image_detection():
    """Test different types of image content to see what gets detected"""
    api_key = os.getenv("SERVER_API_KEY")
    
    # Small test image
    small_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yAAAAABJRU5ErkJggg=="
    
    test_cases = [
        {
            "name": "OpenAI image_url format",
            "payload": {
                "model": "gpt-4o",
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
            "name": "Anthropic image format",
            "payload": {
                "model": "claude-3-sonnet-20240229",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "What do you see?"
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": small_png_base64
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 100
            }
        },
        {
            "name": "Text only",
            "payload": {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, how are you?"
                    }
                ],
                "max_tokens": 100
            }
        },
        {
            "name": "Mixed format (string + list)",
            "payload": {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": "First message"
                    },
                    {
                        "role": "assistant", 
                        "content": "Response"
                    },
                    {
                        "role": "user",
                        "content": [
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
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"📤 Sending request...")
        
        try:
            response = requests.post(
                "http://localhost:5000/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=test_case["payload"],
                timeout=30
            )
            
            print(f"📥 Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"✅ Success! Model used: {response_data.get('model', 'unknown')}")
                except:
                    print(f"✅ Success! Response received")
            else:
                try:
                    error_data = response.json()
                    print(f"❌ Error: {json.dumps(error_data, indent=2)[:200]}...")
                except:
                    print(f"❌ Error: {response.text[:200]}...")
                    
        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_image_detection()