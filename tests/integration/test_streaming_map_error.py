#!/usr/bin/env python3
"""
Test to reproduce the specific map() error scenario
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")

def test_streaming_response():
    """Test streaming response which might cause the map error"""
    url = "http://localhost:5000/v1/chat/completions"
    
    payload = {
        "model": "glm-4.5-anthropic",  # Force Anthropic endpoint  
        "messages": [{"role": "user", "content": "Tell me a short story"}],
        "max_tokens": 100,
        "stream": True  # This might be causing the issue
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    print("🧪 Testing streaming response with Anthropic endpoint...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("Response chunks:")
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        if data_str.strip() == '[DONE]':
                            print("✅ Stream completed normally")
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            print(f"  Chunk: {json.dumps(chunk_data, indent=2)}")
                            
                            # Check if chunk has proper structure
                            if 'choices' not in chunk_data:
                                print("❌ Missing choices in chunk - this could cause map() error!")
                                return
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ Invalid JSON in chunk: {data_str[:100]}...")
        else:
            print(f"❌ Error response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_non_streaming():
    """Test non-streaming response for comparison"""
    url = "http://localhost:5000/v1/chat/completions"
    
    payload = {
        "model": "glm-4.5-anthropic",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 50,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    print("\n🧪 Testing non-streaming response...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'choices' in data and isinstance(data['choices'], list):
                print("✅ Non-streaming has proper choices array")
            else:
                print("❌ Non-streaming missing choices array")
        else:
            print(f"❌ Error: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_non_streaming()
    test_streaming_response()