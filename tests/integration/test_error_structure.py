#!/usr/bin/env python3
"""
Quick test to verify the error response structure
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")

# Test case that should cause an error
response = requests.post("http://localhost:5000/v1/chat/completions", 
    json={
        "model": "glm-4.5-anthropic",
        "messages": [],  # Empty messages should cause error
        "max_tokens": 50
    },
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
)

print(f"Status: {response.status_code}")
response_json = response.json()
print(f"Response structure:")
print(f"  - id: {response_json.get('id', 'missing')}")
print(f"  - object: {response_json.get('object', 'missing')}")
print(f"  - choices: {type(response_json.get('choices', 'missing'))}")
print(f"  - error: {'present' if 'error' in response_json else 'missing'}")

if 'choices' in response_json and isinstance(response_json['choices'], list):
    print(f"✅ Choices array available for client .map() method")
    if len(response_json['choices']) > 0:
        choice = response_json['choices'][0]
        print(f"  - Choice content: {choice.get('message', {}).get('content', 'N/A')}")
else:
    print(f"❌ No choices array - would cause map() error")