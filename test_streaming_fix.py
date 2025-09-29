#!/usr/bin/env python3
"""
Test script to verify streaming requests work after the headers fix.
Tests both Anthropic and OpenAI endpoint routing with streaming enabled.
"""

import json
import time
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def test_streaming_openai_endpoint():
    """Test streaming with OpenAI endpoint routing"""
    print("🧪 Testing streaming with OpenAI endpoint routing...")
    
    payload = {
        "model": "glm-4.5-openai",  # Force OpenAI routing
        "max_tokens": 100,
        "stream": True,  # Enable streaming
        "messages": [
            {
                "role": "user",
                "content": "Count from 1 to 5, one number per sentence."
            }
        ]
    }
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=payload,
            stream=True,  # Important for streaming
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            chunks_received = 0
            total_content = ""
            
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        if data.strip() and data.strip() != '[DONE]':
                            try:
                                chunk = json.loads(data)
                                chunks_received += 1
                                # Extract content from chunk if present
                                if 'content' in chunk:
                                    content = chunk['content']
                                    if isinstance(content, list) and content:
                                        text = content[0].get('text', '') if content[0].get('type') == 'text' else ''
                                        total_content += text
                            except json.JSONDecodeError:
                                pass  # Skip invalid JSON chunks
            
            duration = time.time() - start_time
            print(f"✅ OpenAI streaming test passed!")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Chunks received: {chunks_received}")
            print(f"   Content preview: {total_content[:100]}...")
            return True
        else:
            print(f"❌ OpenAI streaming test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI streaming test error: {e}")
        return False

def test_streaming_anthropic_endpoint():
    """Test streaming with Anthropic endpoint routing"""
    print("\n🧪 Testing streaming with Anthropic endpoint routing...")
    
    payload = {
        "model": "glm-4.5",  # Auto-routing (should go to Anthropic for text)
        "max_tokens": 100,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": "Say hello and tell me your name."
            }
        ]
    }
    
    try:
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=payload,
            stream=True,
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            chunks_received = 0
            
            for line in response.iter_lines():
                if line:
                    chunks_received += 1
                    if chunks_received > 5:  # Just check first few chunks
                        break
            
            duration = time.time() - start_time
            print(f"✅ Anthropic streaming test passed!")
            print(f"   Duration: {duration:.2f}s")
            print(f"   Chunks received: {chunks_received}")
            return True
        else:
            print(f"❌ Anthropic streaming test failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Anthropic streaming test error: {e}")
        return False

def test_non_streaming_baseline():
    """Test non-streaming requests as baseline"""
    print("\n🧪 Testing non-streaming baseline...")
    
    payload = {
        "model": "glm-4.5",
        "max_tokens": 50,
        "stream": False,
        "messages": [
            {
                "role": "user", 
                "content": "Hello!"
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            print("✅ Non-streaming baseline passed")
            return True
        else:
            print(f"❌ Non-streaming baseline failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Non-streaming baseline error: {e}")
        return False

def main():
    print("🔧 Testing Streaming Headers Fix")
    print("=" * 40)
    
    # Test baseline first
    baseline_ok = test_non_streaming_baseline()
    
    # Test streaming endpoints
    openai_streaming_ok = test_streaming_openai_endpoint()
    anthropic_streaming_ok = test_streaming_anthropic_endpoint()
    
    print("\n" + "=" * 40)
    print("📊 Test Results:")
    print(f"   Non-streaming baseline: {'✅ PASS' if baseline_ok else '❌ FAIL'}")
    print(f"   OpenAI streaming: {'✅ PASS' if openai_streaming_ok else '❌ FAIL'}")
    print(f"   Anthropic streaming: {'✅ PASS' if anthropic_streaming_ok else '❌ FAIL'}")
    
    if all([baseline_ok, openai_streaming_ok, anthropic_streaming_ok]):
        print(f"\n🎉 All streaming tests passed! The headers fix resolved the issue.")
        return True
    else:
        print(f"\n❌ Some tests failed. The 'stream has been closed' error may persist.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)