#!/usr/bin/env python3
"""Simple test to check if image age auto-switching is working"""

import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")

# Test just the old_image_threshold_3 scenario 
SAMPLE_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAG/fzQhxQAAAABJRU5ErkJggg=="

test_messages = [
    {"role": "user", "content": [
        {"type": "text", "text": "Here's an image to analyze:"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
    ]},
    {"role": "assistant", "content": "I can see the image you shared."},
    {"role": "user", "content": "What do you think about it?"},
    {"role": "assistant", "content": "It's a simple image."},
    {"role": "user", "content": "Tell me more about machine learning."}
]

payload = {
    "model": "glm-4.5",
    "messages": test_messages,
    "max_tokens": 50,
    "temperature": 0.1
}

print("🧪 Testing old image threshold scenario")
print(f"Messages: {len(test_messages)}")
print("Expected: Auto-switch to text endpoint with truncation message")

response = requests.post(
    "http://localhost:5000/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json=payload
)

if response.status_code == 200:
    data = response.json()
    context_info = data.get("context_info", {})
    endpoint_type = context_info.get("endpoint_type", "unknown")
    
    response_text = data["choices"][0]["message"]["content"] if data.get("choices") else ""
    has_truncation_message = "image was provided earlier" in response_text.lower()
    
    print(f"✅ Status: {response.status_code}")
    print(f"📡 Endpoint: {endpoint_type}")
    print(f"🖼️ Truncation message: {has_truncation_message}")
    print(f"📝 Response: {response_text}")
    
    if endpoint_type == "anthropic" and has_truncation_message:
        print("🎉 SUCCESS: Auto-switching working!")
    else:
        print("❌ FAILURE: Auto-switching not working as expected")
else:
    print(f"❌ Error: {response.status_code} - {response.text}")