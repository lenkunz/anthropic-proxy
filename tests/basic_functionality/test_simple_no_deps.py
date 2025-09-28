#!/usr/bin/env python3
"""Simple test without external dependencies"""

import json
import urllib.request
import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

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

try:
    # Create request
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        "http://localhost:5000/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )
    
    # Send request
    with urllib.request.urlopen(req, timeout=30) as response:
        response_data = json.loads(response.read().decode('utf-8'))
        
        context_info = response_data.get("context_info", {})
        endpoint_type = context_info.get("endpoint_type", "unknown")
        
        response_text = response_data["choices"][0]["message"]["content"] if response_data.get("choices") else ""
        has_truncation_message = "image was provided earlier" in response_text.lower()
        
        print(f"✅ Status: {response.status}")
        print(f"📡 Endpoint: {endpoint_type}")
        print(f"🖼️ Truncation message: {has_truncation_message}")
        print(f"📝 Response: {response_text[:100]}...")
        
        if endpoint_type == "anthropic" and has_truncation_message:
            print("🎉 SUCCESS: Auto-switching working!")
        else:
            print("❌ FAILURE: Auto-switching not working as expected")

except Exception as e:
    print(f"❌ Error: {e}")