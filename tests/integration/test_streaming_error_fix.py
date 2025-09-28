#!/usr/bin/env python3
"""
Test script to trigger streaming errors and verify the fix
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")

def test_streaming_error_with_bad_request():
    """Test streaming with a request that should cause an error"""
    url = "http://localhost:5000/v1/chat/completions"
    
    # This should cause an error - empty messages
    payload = {
        "model": "glm-4.5-anthropic",
        "messages": [],  # Empty messages should trigger error
        "max_tokens": 50,
        "stream": True  # Test streaming error handling
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    print("🧪 Testing streaming error handling...")
    print("This should trigger an error but with proper OpenAI structure")
    
    try:
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        if "text/event-stream" in response.headers.get("content-type", ""):
            print("📡 Receiving streamed response...")
            error_found = False
            choices_found = False
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    print(f"Raw line: {line_str}")
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        if data_str.strip() == '[DONE]':
                            print("✅ Stream completed")
                            break
                        
                        try:
                            chunk_data = json.loads(data_str)
                            print(f"Parsed chunk: {json.dumps(chunk_data, indent=2)}")
                            
                            # Check if it has the proper structure
                            if 'choices' in chunk_data:
                                choices_found = True
                                print("✅ Chunk has 'choices' field")
                                
                                choices = chunk_data['choices']
                                if isinstance(choices, list):
                                    print("✅ 'choices' is a list")
                                else:
                                    print(f"❌ 'choices' is not a list: {type(choices)}")
                            else:
                                print("❌ Chunk missing 'choices' field - this would cause map() error!")
                                
                            if 'error' in chunk_data:
                                error_found = True
                                print("🚨 Error chunk detected")
                                
                        except json.JSONDecodeError as e:
                            print(f"❌ Invalid JSON in chunk: {data_str}")
                            
            if error_found and choices_found:
                print("✅ SUCCESS: Error response has proper 'choices' structure")
            elif error_found and not choices_found:
                print("❌ FAILED: Error response missing 'choices' - would cause map() error")
            else:
                print("ℹ️  No error occurred during streaming")
                
        else:
            # Non-streaming response
            try:
                response_data = response.json()
                print(f"Non-streaming response: {json.dumps(response_data, indent=2)}")
                
                if 'choices' in response_data:
                    print("✅ Non-streaming response has 'choices'")
                else:
                    print("❌ Non-streaming response missing 'choices'")
                    
            except:
                print(f"Raw response: {response.text}")
                
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    print("🔧 TESTING STREAMING ERROR FIX")
    print("="*60)
    test_streaming_error_with_bad_request()