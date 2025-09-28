#!/usr/bin/env python3
"""
Test the /v1/messages endpoint directly to see what response structure it returns
"""

import requests
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path and load environment from project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

API_KEY = os.getenv("SERVER_API_KEY")

def test_messages_endpoint():
    """Test the /v1/messages endpoint that Claude CLI uses"""
    url = "http://localhost:5000/v1/messages"
    
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello, test message"}
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY,
        "anthropic-beta": "prompt-caching-2024-07-31"  # Same as Claude CLI uses
    }
    
    print("🧪 Testing /v1/messages endpoint structure...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\n📥 Response:")
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"\n📋 Response JSON:")
            print(json.dumps(response_json, indent=2))
            
            # Check if response has choices
            if "choices" in response_json:
                print(f"\n✅ Response has 'choices': {type(response_json['choices'])}")
                if isinstance(response_json['choices'], list):
                    print(f"   Choices length: {len(response_json['choices'])}")
                else:
                    print(f"   ❌ Choices is not a list!")
            else:
                print(f"\n❌ Response missing 'choices' field")
                print(f"   Available fields: {list(response_json.keys())}")
                
                # This is likely what's causing the map() error!
                print(f"\n🚨 This response would cause 'Cannot read properties of undefined (reading map)' error!")
                print(f"    Claude CLI expects OpenAI format with choices array")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            print(f"Raw response: {response.text[:500]}...")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_streaming_messages():
    """Test streaming messages endpoint"""
    url = "http://localhost:5000/v1/messages"
    
    payload = {
        "model": "claude-3-sonnet-20240229", 
        "max_tokens": 50,
        "messages": [
            {"role": "user", "content": "Count to 5"}
        ],
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY,
        "anthropic-beta": "prompt-caching-2024-07-31"
    }
    
    print(f"\n🧪 Testing /v1/messages streaming...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
        
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        if "text/event-stream" in response.headers.get("content-type", ""):
            print("\n📡 Streaming response chunks:")
            chunk_count = 0
            for line in response.iter_lines():
                if line and chunk_count < 5:  # Limit output
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str.strip() == '[DONE]':
                            print("✅ Stream completed")
                            break
                        try:
                            chunk_data = json.loads(data_str) 
                            print(f"Chunk {chunk_count}: {json.dumps(chunk_data, indent=2)}")
                            chunk_count += 1
                        except:
                            print(f"Raw chunk: {data_str[:100]}...")
        
    except Exception as e:
        print(f"❌ Streaming test failed: {e}")

if __name__ == "__main__":
    print("🔍 DEBUGGING /v1/messages ENDPOINT STRUCTURE")
    print("="*70)
    test_messages_endpoint()
    test_streaming_messages()