#!/usr/bin/env python3

import requests
import json
import os
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load test image
with open('pexels-photo-1108099.jpeg', 'rb') as f:
    image_data = f.read()
    image_b64 = base64.b64encode(image_data).decode()

# Simple test payload
test_payload = {
    "model": "claude-3.5-sonnet",
    "max_tokens": 100,
    "temperature": 0.7,
    "messages": [
        {
            "role": "user", 
            "content": "Hello, how are you?"
        }
    ]
}

api_key = os.getenv("SERVER_API_KEY")
if not api_key:
    print("❌ No SERVER_API_KEY environment variable found")
    exit(1)

print("🧪 Testing simple text request (no images)")

response = requests.post(
    "http://localhost:5000/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json=test_payload,
    timeout=30
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✅ Text request succeeded")
    print(f"Response: {response.json()}")
else:
    print("❌ Text request failed")
    print(f"Response: {response.text}")