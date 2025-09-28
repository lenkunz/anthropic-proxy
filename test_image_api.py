#!/usr/bin/env python3
"""Test image routing with a simple image"""

import requests
import json
import base64

def test_image_routing():
    # Create a simple test image (1x1 pixel PNG)
    test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x02\x8a\xb4y\x00\x00\x00\x00IEND\xaeB`\x82').decode()

    payload = {
        "model": "glm-4.5",
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What do you see in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{test_image_data}"}}
                ]
            }
        ],
        "max_tokens": 100,
        "stream": False
    }

    # Call the API
    try:
        response = requests.post(
            "http://localhost:5000/v1/chat/completions",
            headers={
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Image request was processed successfully!")
        else:
            print("❌ Request failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_image_routing()