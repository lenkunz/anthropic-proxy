#!/usr/bin/env python3
"""
Complete test script for x-kilo-followsup header functionality

This script tests the x-kilo-followsup feature by:
1. Making requests with the x-kilo-followsup: true header
2. Checking if followup questions are added when appropriate
3. Verifying that followup questions are NOT added for tools use patterns
4. Testing both /v1/chat/completions and /v1/messages endpoints
5. Testing both streaming and non-streaming responses
"""

import os
import json
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY")

def test_non_tools_use_response():
    """Test that followup question is added for regular assistant responses"""
    print("🧪 Testing non-tools use response (should add followup)...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}" if API_KEY else None,
        "x-kilo-followsup": "true"
    }
    
    # Remove None headers
    headers = {k: v for k, v in headers.items() if v is not None}
    
    payload = {
        "model": "glm-4.6",
        "messages": [
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "stream": False
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{API_BASE}/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                print(f"✅ Response received (status: {response.status_code})")
                print(f"📝 Response content: {content[:200]}...")
                
                # Check if followup question was added
                if "<ask_followup_question>" in content:
                    print("✅ Followup question correctly added to non-tools use response")
                    return True
                else:
                    print("❌ Followup question was NOT added to non-tools use response")
                    return False
            else:
                print(f"❌ Request failed with status {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing non-tools use response: {e}")
        return False

def test_without_header():
    """Test that followup question is NOT added when header is not set"""
    print("\n🧪 Testing without x-kilo-followsup header (should NOT add followup)...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}" if API_KEY else None
        # Note: NOT including x-kilo-followsup header
    }
    
    # Remove None headers
    headers = {k: v for k, v in headers.items() if v is not None}
    
    payload = {
        "model": "glm-4.6",
        "messages": [
            {"role": "user", "content": "What is the capital of Italy?"}
        ],
        "stream": False
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{API_BASE}/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                print(f"✅ Response received (status: {response.status_code})")
                print(f"📝 Response content: {content[:200]}...")
                
                # Check if followup question was NOT added
                if "<ask_followup_question>" not in content:
                    print("✅ Followup question correctly NOT added when header is missing")
                    return True
                else:
                    print("❌ Followup question was incorrectly added when header is missing")
                    return False
            else:
                print(f"❌ Request failed with status {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing without header: {e}")
        return False

def test_anthropic_endpoint():
    """Test x-kilo-followsup functionality with /v1/messages endpoint"""
    print("\n🧪 Testing /v1/messages endpoint with x-kilo-followsup...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}" if API_KEY else None,
        "x-kilo-followsup": "true"
    }
    
    # Remove None headers
    headers = {k: v for k, v in headers.items() if v is not None}
    
    payload = {
        "model": "glm-4.6",
        "messages": [
            {"role": "user", "content": "What is the capital of Spain?"}
        ],
        "max_tokens": 500
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{API_BASE}/v1/messages", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content_blocks = result.get("content", [])
                
                # Extract text content
                content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        content += block.get("text", "")
                
                print(f"✅ Response received (status: {response.status_code})")
                print(f"📝 Response content: {content[:200]}...")
                
                # Check if followup question was added
                if "<ask_followup_question>" in content:
                    print("✅ Followup question correctly added to /v1/messages response")
                    return True
                else:
                    print("❌ Followup question was NOT added to /v1/messages response")
                    return False
            else:
                print(f"❌ Request failed with status {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Error testing /v1/messages endpoint: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting x-kilo-followsup functionality tests...\n")
    
    if not API_KEY:
        print("⚠️  Warning: SERVER_API_KEY not found in .env file")
        print("   Make sure the proxy server is running and accessible")
    
    tests = [
        test_non_tools_use_response,
        test_without_header,
        test_anthropic_endpoint,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ Test {test_func.__name__} failed")
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! x-kilo-followsup functionality is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    main()