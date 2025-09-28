#!/usr/bin/env python3
"""
Test to trigger a streaming error by temporarily changing the upstream URL
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")

def test_anthropic_messages_endpoint():
    """Test the Anthropic /v1/messages endpoint directly to trigger streaming errors"""
    url = "http://localhost:5000/v1/messages"
    
    # Request that should work but might have streaming errors
    payload = {
        "model": "glm-4.5",
        "messages": [{"role": "user", "content": "Tell me a very long story about adventure"}],
        "max_tokens": 1000,
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    print("🧪 Testing /v1/messages endpoint streaming...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=5)  # Short timeout to trigger error
        print(f"Status: {response.status_code}")
        
        if "text/event-stream" in response.headers.get("content-type", ""):
            print("📡 Processing stream...")
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        if data_str.strip() == '[DONE]':
                            break
                            
                        try:
                            chunk_data = json.loads(data_str)
                            print(f"Chunk: {json.dumps(chunk_data, indent=2)}")
                            
                            # Check for error structure
                            if 'error' in chunk_data:
                                if 'choices' in chunk_data:
                                    print("✅ Error chunk has 'choices' - no map() error!")
                                else:
                                    print("❌ Error chunk missing 'choices' - would cause map() error!")
                                    
                        except json.JSONDecodeError:
                            print(f"Invalid JSON: {data_str[:100]}...")
                            
    except Exception as e:
        print(f"Error: {e}")

def test_force_streaming_timeout():
    """Test with very short timeout to force a streaming error"""
    url = "http://localhost:5000/v1/chat/completions"
    
    payload = {
        "model": "glm-4.5-anthropic",
        "messages": [{"role": "user", "content": "Write a very long story"}],
        "max_tokens": 1000,
        "stream": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    print("\n🧪 Testing with very short timeout to force error...")
    
    try:
        # Very short timeout to trigger connection error during streaming
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=0.1)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                print(f"Line: {line_str}")
                
    except Exception as e:
        print(f"Expected timeout error: {e}")

if __name__ == "__main__":
    print("🔧 TESTING STREAMING ERROR CONDITIONS")
    print("="*60)
    test_anthropic_messages_endpoint()
    test_force_streaming_timeout()