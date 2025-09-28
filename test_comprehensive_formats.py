#!/usr/bin/env python3
"""Comprehensive test of different image formats with the upstream OpenAI endpoint"""

import requests
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def test_all_formats():
    """Test all possible image formats to see what the upstream actually accepts"""
    api_key = os.getenv("SERVER_API_KEY")
    openai_base = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
    
    print(f"📝 Testing OpenAI endpoint: {openai_base}")
    print(f"📝 Using API key: {api_key[:10]}...")
    
    # Create a small test image (1x1 pixel PNG)
    small_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yAAAAABJRU5ErkJggg=="
    
    test_cases = [
        {
            "name": "Standard OpenAI format with image_url",
            "payload": {
                "model": "glm-4.5v",
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
            "name": "Simple format (just base64 in content)",
            "payload": {
                "model": "glm-4.5v",
                "messages": [
                    {
                        "role": "user",
                        "content": f"What do you see in this image? data:image/png;base64,{small_png_base64}"
                    }
                ],
                "max_tokens": 100
            }
        },
        {
            "name": "Text at beginning + image_url",
            "payload": {
                "model": "glm-4.5v",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this:"
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
            "name": "Just image_url without text",
            "payload": {
                "model": "glm-4.5v",
                "messages": [
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
        },
        {
            "name": "Multiple images with text",
            "payload": {
                "model": "glm-4.5v",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Compare these images:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{small_png_base64}"
                                }
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
            "name": "Image with detail parameter",
            "payload": {
                "model": "glm-4.5v",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{small_png_base64}",
                                    "detail": "high"
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
        print(f"📤 Payload structure: {json.dumps(test_case['payload'], indent=2)[:200]}...")
        
        try:
            response = requests.post(
                f"{openai_base.rstrip('/')}/chat/completions",
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
                    print(f"✅ SUCCESS! Model: {response_data.get('model', 'unknown')}")
                    if 'choices' in response_data and response_data['choices']:
                        content = response_data['choices'][0].get('message', {}).get('content', '')[:150]
                        print(f"   Response: {content}...")
                except Exception as e:
                    print(f"✅ SUCCESS! (JSON parsing error: {e})")
            else:
                try:
                    error_data = response.json()
                    print(f"❌ FAILED: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"❌ FAILED: {response.text[:200]}...")
                    
        except Exception as e:
            print(f"❌ REQUEST FAILED: {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    test_all_formats()