#!/usr/bin/env python3
"""Test image routing with a simple image"""

import requests
import json
import base64
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_image_routing():
    # Get API key from environment
    api_key = os.getenv("SERVER_API_KEY")
    if not api_key:
        print("❌ No SERVER_API_KEY found in .env file")
        return
    
    print(f"📝 Using API key: {api_key[:10]}...")
    
    # Create a simple test image (1x1 pixel PNG)
    test_image_data = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x02\x8a\xb4y\x00\x00\x00\x00IEND\xaeB`\x82').decode()

    # Test 1: Image request (should route to OpenAI endpoint)
    print("\n🖼️  Testing IMAGE request routing...")
    image_payload = {
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
    
    test_request("Image Request", image_payload, api_key)
    
    # Test 2: Text-only request (should route to Anthropic endpoint)  
    print("\n📝 Testing TEXT request routing...")
    text_payload = {
        "model": "glm-4.5",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "max_tokens": 100,
        "stream": False
    }
    
    test_request("Text Request", text_payload, api_key)

def test_request(test_name, payload, api_key):
    """Helper function to test a request and analyze the response"""
    try:
        response = requests.post(
            "http://localhost:5000/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=payload,
            timeout=10
        )
        
        print(f"  Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"  Response: {json.dumps(response_data, indent=2)[:200]}...")
        except:
            print(f"  Response (raw): {response.text[:200]}...")
        
        if response.status_code == 200:
            print(f"  ✅ {test_name} was processed successfully!")
        elif response.status_code == 401:
            print(f"  🔑 {test_name} failed due to authentication")
        elif response.status_code == 500:
            print(f"  ⚠️  {test_name} reached upstream but encountered an error")
        else:
            print(f"  ❌ {test_name} failed with status {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ {test_name} error: {e}")

if __name__ == "__main__":
    test_image_routing()