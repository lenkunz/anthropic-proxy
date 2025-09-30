#!/usr/bin/env python3
"""
Quick Validation - Anthropic Proxy v1.6.0

Validates that all the v1.6.0 fixes are working correctly.
"""

import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def check_service():
    """Check if service is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_models_endpoint():
    """Test that model variants are available"""
    response = requests.get(f"{BASE_URL}/v1/models", headers=HEADERS)
    if response.status_code == 200:
        models = response.json()
        available = [m['id'] for m in models['data']]
        expected = ['glm-4.5', 'glm-4.5-openai', 'glm-4.5-anthropic']
        return all(model in available for model in expected)
    return False

def test_complex_message_conversion():
    """Test the message conversion fix"""
    payload = {
        "model": "glm-4.5-openai",
        "max_tokens": 50,
        "stream": False,
        "system": "You are helpful.",
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Hi there!"}]
            }
        ]
    }
    
    response = requests.post(f"{BASE_URL}/v1/messages", headers=HEADERS, json=payload)
    return response.status_code == 200

def test_streaming_no_errors():
    """Test that streaming doesn't return 500 errors"""
    payload = {
        "model": "glm-4.5",
        "max_tokens": 20,
        "stream": True,
        "messages": [{"role": "user", "content": "Hi"}]
    }
    
    response = requests.post(f"{BASE_URL}/v1/messages", headers=HEADERS, json=payload, stream=True)
    return response.status_code == 200

def main():
    print("🔍 Anthropic Proxy v1.6.0 - Quick Validation")
    print("=" * 45)
    
    # Service check
    print("1. Service Health... ", end="")
    if check_service():
        print("✅ Running")
    else:
        print("❌ Not available (run: docker compose up -d)")
        return
    
    # Models check
    print("2. Model Variants... ", end="")
    if test_models_endpoint():
        print("✅ Available")
    else:
        print("❌ Missing variants")
    
    # Message conversion check
    print("3. Message Conversion... ", end="")
    if test_complex_message_conversion():
        print("✅ Working")
    else:
        print("❌ Failed")
    
    # Streaming check
    print("4. Streaming Fix... ", end="")
    if test_streaming_no_errors():
        print("✅ No errors")
    else:
        print("❌ Still failing")
    
    print("\n🎯 v1.6.0 validation complete!")

if __name__ == "__main__":
    main()