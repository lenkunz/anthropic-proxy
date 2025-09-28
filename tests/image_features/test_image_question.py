#!/usr/bin/env python3
"""Test image question answering functionality"""

import json
import urllib.request
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

SAMPLE_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAG/fzQhxQAAAABJRU5ErkJggg=="

# Test where we ask about the image after it should be truncated
test_messages = [
    {"role": "user", "content": [
        {"type": "text", "text": "Here's an important image:"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
    ]},
    {"role": "assistant", "content": "I can see the image you shared."},
    {"role": "user", "content": "What do you think about it?"},
    {"role": "assistant", "content": "It's a simple image."},
    {"role": "user", "content": "What was in the image I showed you earlier?"}  # This should reveal if truncation message is working
]

payload = {
    "model": "glm-4.5",
    "messages": test_messages,
    "max_tokens": 150,
    "temperature": 0.1
}

print("🧪 Testing image truncation with explicit image question")
print(f"Messages: {len(test_messages)}")
print("Expected: AI should mention that image was truncated")

try:
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        "http://localhost:5000/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        response_data = json.loads(response.read().decode('utf-8'))
        
        context_info = response_data.get("context_info", {})
        endpoint_type = context_info.get("endpoint_type", "unknown")
        
        response_text = response_data["choices"][0]["message"]["content"] if response_data.get("choices") else ""
        
        print(f"✅ Status: {response.status}")
        print(f"📡 Endpoint: {endpoint_type}")
        print(f"📝 Full Response: {response_text}")
        
        # Look for indicators that the AI knows about the truncation
        truncation_indicators = [
            "truncated", "provided earlier", "conversation but", 
            "cannot see", "no longer", "removed", "not available"
        ]
        
        has_truncation_awareness = any(indicator in response_text.lower() for indicator in truncation_indicators)
        
        if endpoint_type == "anthropic" and has_truncation_awareness:
            print("🎉 SUCCESS: Image truncation working!")
        else:
            print("❌ Need to investigate further")
            print(f"   Endpoint correct: {endpoint_type == 'anthropic'}")
            print(f"   Truncation mentioned: {has_truncation_awareness}")

except Exception as e:
    print(f"❌ Error: {e}")