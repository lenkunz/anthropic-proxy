#!/usr/bin/env python3
"""
Test script for complex message conversion fix.
Tests the /v1/messages endpoint with complex Anthropic message structures
to verify they can be properly routed to the OpenAI endpoint.
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

def test_complex_message_conversion():
    """Test complex message structure that was failing in the user's log"""
    print("🧪 Testing complex message conversion (system + tool calls + multipart content)...")
    
    # Simulate a complex message structure similar to what was in the user's log
    complex_payload = {
        "model": "glm-4.5-openai",  # Force OpenAI routing to test conversion
        "max_tokens": 2000,
        "temperature": 0.7,
        "stream": False,
        "system": [
            {
                "type": "text", 
                "text": "You are Claude Code, an AI assistant integrated with your development environment. You can help with code understanding, development tasks, and project management within VS Code workspaces."
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "I want to be able to send that message to openai endpoint but it seems broken. Here's the upstream request log showing the complex structure with tool calls and system reminders."
                    }
                ]
            },
            {
                "role": "assistant", 
                "content": [
                    {
                        "type": "text",
                        "text": "I can help you debug the message conversion issue. Let me analyze the problem with routing complex messages to the OpenAI endpoint."
                    },
                    {
                        "type": "tool_use",
                        "id": "call_analyze_logs", 
                        "name": "analyze_proxy_logs",
                        "input": {
                            "log_type": "upstream_request",
                            "focus": "message_conversion"
                        }
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_analyze_logs",
                        "content": "Found conversion issue: Anthropic messages with tool calls and system content are not properly converted to OpenAI format when routing to OpenAI endpoint."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Can you help fix this conversion issue?"
                    }
                ]
            }
        ]
    }
    
    try:
        start_time = time.time()
        
        print(f"📤 Sending complex message to /v1/messages endpoint...")
        print(f"   Model: {complex_payload['model']}")
        print(f"   System blocks: {len(complex_payload.get('system', []))}")
        print(f"   Messages: {len(complex_payload['messages'])}")
        print(f"   Has tool calls: {any('tool_use' in str(msg) for msg in complex_payload['messages'])}")
        
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=complex_payload,
            timeout=30
        )
        
        duration = time.time() - start_time
        
        print(f"📥 Response received in {duration:.2f}s")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ Success! Message conversion working properly")
                print(f"   Response ID: {result.get('id', 'unknown')}")
                print(f"   Model: {result.get('model', 'unknown')}")
                print(f"   Content length: {len(result.get('content', []))}")
                print(f"   Usage: {result.get('usage', {})}")
                
                # Check if response has expected Anthropic format structure
                if "content" in result and isinstance(result["content"], list):
                    print(f"   ✓ Proper Anthropic response format maintained")
                else:
                    print(f"   ⚠️  Response format may be unexpected")
                    
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ Response is not valid JSON: {e}")
                print(f"Raw response: {response.text[:500]}...")
                return False
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_simple_message():
    """Test that simple messages still work after the conversion changes"""
    print("\n🧪 Testing simple message (baseline)...")
    
    simple_payload = {
        "model": "glm-4.5-openai",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Hello, this is a simple test message. Please respond briefly."
            }
        ]
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=simple_payload,
            timeout=15
        )
        
        duration = time.time() - start_time
        print(f"📥 Response received in {duration:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Simple message test passed")
            print(f"   Content preview: {str(result.get('content', []))[:100]}...")
            return True
        else:
            print(f"❌ Simple message test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Simple message test error: {e}")
        return False

def test_health_check():
    """Ensure the service is running"""
    print("🏥 Checking service health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service is healthy")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def main():
    print("🔧 Testing Complex Message Conversion Fix")
    print("=" * 50)
    
    # Check if service is running
    if not test_health_check():
        print("\n❌ Service not available. Make sure the proxy is running.")
        return False
    
    # Test simple message first
    simple_ok = test_simple_message()
    
    # Test complex message conversion
    complex_ok = test_complex_message_conversion()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Simple message: {'✅ PASS' if simple_ok else '❌ FAIL'}")
    print(f"   Complex message: {'✅ PASS' if complex_ok else '❌ FAIL'}")
    
    if simple_ok and complex_ok:
        print(f"\n🎉 All tests passed! The message conversion fix is working.")
        return True
    else:
        print(f"\n❌ Some tests failed. Check the logs for details.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)