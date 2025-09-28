#!/usr/bin/env python3
"""
Quick test to verify thinking parameter is added by checking request payload
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"

# Simple test to trigger OpenAI endpoint and check logs
response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "model": "glm-4.5-openai",  # Force OpenAI endpoint
        "messages": [{"role": "user", "content": "Test thinking parameter"}],
        "max_tokens": 10
    }
)

print(f"Response status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    usage = data.get("usage", {})
    print(f"Endpoint type: {usage.get('endpoint_type', 'unknown')}")
    print("✅ Request completed - check Docker logs for thinking parameter debug message")
else:
    print(f"Error: {response.text}")