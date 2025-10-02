#!/usr/bin/env python3
"""
Quick test to verify Anthropic image description functionality
"""

import os
import base64
import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")

def encode_image(image_path):
    """Encode image for Anthropic API"""
    with open(image_path, "rb") as f:
        image_data = f.read()
        return {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.b64encode(image_data).decode('utf-8')
        }

# Test Anthropic image description
image_data = encode_image("examples/pexels-photo-1108099.jpeg")

payload = {
    "model": "glm-4.6",
    "messages": [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail"},
                {"type": "image", "source": image_data}
            ]
        }
    ],
    "max_tokens": 500
}

headers = {
    "content-type": "application/json", 
    "x-api-key": API_KEY,
    "anthropic-version": "2023-06-01"
}

with httpx.Client(timeout=30.0) as client:
    response = client.post(
        "https://api.z.ai/api/anthropic/v1/messages",
        headers=headers,
        json=payload
    )

if response.status_code == 200:
    result = response.json()
    content = result["content"][0]["text"]
    print("✅ Anthropic image description working!")
    print(f"Response: {content[:200]}...")
else:
    print(f"❌ Failed: {response.status_code}")
    print(response.text)