#!/usr/bin/env python3
"""
Test Context Window Management for Anthropic Proxy

This test validates the context window overflow handling when switching
between endpoints with different context limits.

Scenarios:
1. Large text conversation → add image (should truncate)
2. Vision request that exceeds vision context limit
3. Normal requests that fit within limits
"""

import requests
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY", "test-key")

def create_long_conversation(message_count: int = 20, words_per_message: int = 500) -> list:
    """Create a long conversation to test context limits"""
    messages = [
        {"role": "system", "content": "You are a helpful assistant that provides detailed explanations."}
    ]
    
    base_content = " ".join(["word"] * words_per_message)  # Roughly words_per_message tokens
    
    for i in range(message_count):
        messages.append({
            "role": "user", 
            "content": f"Question {i+1}: Please explain this topic in detail. {base_content}"
        })
        messages.append({
            "role": "assistant",
            "content": f"Answer {i+1}: Here is a detailed explanation. {base_content} This covers all aspects thoroughly."
        })
    
    return messages

def test_context_overflow_text_to_vision():
    """Test context overflow when switching from text to vision model"""
    print("🧪 Testing: Text → Vision Context Overflow")
    print("=" * 60)
    
    # Create a large conversation that fits in text model (200k) but not vision (65k)
    long_messages = create_long_conversation(message_count=15, words_per_message=800)
    
    print(f"Created conversation with {len(long_messages)} messages")
    
    # Add an image to trigger vision model routing
    long_messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": "What do you see in this image?"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                }
            }
        ]
    })
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5",  # Text model, but image will trigger vision routing
        "messages": long_messages,
        "max_tokens": 100,
        "stream": False
    }
    
    print(f"Sending request with {len(long_messages)} messages...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        print(f"Response received in {elapsed:.2f}s")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Request successful!")
            print(f"Response: {data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')[:100]}...")
            
            # Check for truncation headers or indicators
            if 'X-Context-Truncated' in response.headers:
                print(f"🔄 Context was truncated: {response.headers['X-Context-Truncated']}")
            
            usage = data.get('usage', {})
            print(f"Usage: {usage}")
            
        else:
            print(f"❌ Request failed: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except Exception as e:
        print(f"💥 Error: {e}")
    
    print()

def test_vision_context_overflow():
    """Test context overflow in pure vision request"""
    print("🧪 Testing: Vision Model Context Overflow")
    print("=" * 60)
    
    # Create a very long text with an image
    long_text = " ".join(["word"] * 10000)  # ~10k tokens of text
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Analyze this image in detail. Context: {long_text}"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                    }
                }
            ]
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5v",  # Vision model
        "messages": messages,
        "max_tokens": 100,
        "stream": False
    }
    
    print(f"Sending vision request with large context...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        print(f"Response received in {elapsed:.2f}s")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Request successful!")
            print(f"Response: {data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')[:100]}...")
            
            usage = data.get('usage', {})
            print(f"Usage: {usage}")
            
        else:
            print(f"❌ Request failed: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except Exception as e:
        print(f"💥 Error: {e}")
    
    print()

def test_normal_requests():
    """Test normal requests that should fit within limits"""
    print("🧪 Testing: Normal Requests (Within Limits)")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "Short text request",
            "payload": {
                "model": "glm-4.5",
                "messages": [{"role": "user", "content": "Hello, how are you?"}],
                "max_tokens": 50
            }
        },
        {
            "name": "Short vision request", 
            "payload": {
                "model": "glm-4.5v",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What's in this image?"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 50
            }
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    for case in test_cases:
        print(f"Testing: {case['name']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                headers=headers,
                json=case['payload'],
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Success: {data.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')[:50]}...")
            else:
                print(f"  ❌ Failed: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"  💥 Error: {e}")
        
        time.sleep(0.5)  # Brief pause between requests
    
    print()

def main():
    """Run all context window management tests"""
    print("🚀 Context Window Management Test Suite")
    print("=" * 80)
    
    # Test 1: Text to Vision overflow
    test_context_overflow_text_to_vision()
    
    # Test 2: Vision model overflow
    test_vision_context_overflow()
    
    # Test 3: Normal requests
    test_normal_requests()
    
    print("🎯 Context Window Management Tests Complete")
    print("=" * 80)
    print("Check the proxy logs for context truncation messages and warnings.")

if __name__ == "__main__":
    main()