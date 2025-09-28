#!/usr/bin/env python3
"""
Test script to reproduce the Claude client error with Anthropic endpoint
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

API_BASE = "http://localhost:5000"

def test_anthropic_endpoint_error():
    """Test to reproduce the map error with Anthropic endpoint"""
    url = f"{API_BASE}/v1/chat/completions"
    
    # Test with a request that might cause an error
    payload = {
        "model": "glm-4.5-anthropic",  # Force Anthropic endpoint
        "messages": [
            {"role": "user", "content": "This is a test message that might cause an error"}
        ],
        "max_tokens": 100,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    print("🧪 Testing Anthropic endpoint for potential map() error...")
    print(f"URL: {url}")
    print(f"Model: {payload['model']}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"JSON Response: {json.dumps(response_json, indent=2)}")
            
            # Check if response has proper structure
            if "choices" in response_json:
                print("✅ Response has choices array")
                choices = response_json["choices"]
                if isinstance(choices, list):
                    print(f"✅ Choices is a list with {len(choices)} items")
                else:
                    print(f"❌ Choices is not a list: {type(choices)}")
            else:
                print("❌ Response missing choices array")
                
            if "error" in response_json:
                print(f"⚠️ Response contains error: {response_json['error']}")
                
        except Exception as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"Raw response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_various_anthropic_scenarios():
    """Test various scenarios that might cause the map error"""
    
    test_cases = [
        {
            "name": "Normal request",
            "payload": {
                "model": "glm-4.5-anthropic",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 50
            }
        },
        {
            "name": "Very long request", 
            "payload": {
                "model": "glm-4.5-anthropic",
                "messages": [{"role": "user", "content": "This is a very long message that might exceed token limits. " * 100}],
                "max_tokens": 50
            }
        },
        {
            "name": "Invalid max_tokens",
            "payload": {
                "model": "glm-4.5-anthropic", 
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": -1  # Invalid value
            }
        },
        {
            "name": "Empty messages",
            "payload": {
                "model": "glm-4.5-anthropic",
                "messages": [],
                "max_tokens": 50
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"🧪 Test: {test_case['name']}")
        print(f"{'='*60}")
        
        url = f"{API_BASE}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "x-api-key": API_KEY
        }
        
        try:
            response = requests.post(url, json=test_case["payload"], headers=headers, timeout=30)
            
            print(f"Status: {response.status_code}")
            
            try:
                response_json = response.json()
                
                # Check structure
                if "choices" in response_json:
                    choices = response_json["choices"]
                    print(f"✅ Choices present: {type(choices)} with {len(choices) if isinstance(choices, list) else 'N/A'} items")
                else:
                    print("❌ No choices in response")
                    print(f"Response keys: {list(response_json.keys())}")
                    
            except Exception as e:
                print(f"❌ JSON parse error: {e}")
                print(f"Raw response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"❌ Request error: {e}")

if __name__ == "__main__":
    print("🌟 DEBUGGING ANTHROPIC ENDPOINT MAP() ERROR")
    print("="*80)
    
    test_anthropic_endpoint_error()
    test_various_anthropic_scenarios()
    
    print("\n" + "="*80) 
    print("💡 If you see 'Cannot read properties of undefined (reading 'map')',")
    print("   it means the response doesn't have the expected OpenAI structure.")
    print("   The client is trying to call .map() on response.choices, but")
    print("   choices is undefined or null.")