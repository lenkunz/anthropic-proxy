#!/usr/bin/env python3
"""Test text routing (should go to Anthropic)"""

import requests
import json

def test_text_routing():
    payload = {
        "model": "glm-4.5",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "max_tokens": 100,
        "stream": False
    }

    try:
        response = requests.post(
            "http://localhost:5000/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer dummy-key"
            },
            json=payload,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_text_routing()