#!/usr/bin/env python3
"""
Test script for simplified glm-4.5 model functionality
Tests that single model routes correctly based on content with proper token scaling
"""

import json
import requests
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_API_KEY = os.getenv("SERVER_API_KEY", "test-key-12345")

def test_single_model_availability():
    """Test that only glm-4.5 model is available"""
    print("🔍 Testing single model availability...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/v1/models",
            headers={"Authorization": f"Bearer {TEST_API_KEY}"}
        )
        
        if response.status_code == 200:
            models_data = response.json()
            model_ids = [model["id"] for model in models_data.get("data", [])]
            
            if model_ids == ["glm-4.5"]:
                print("✅ Only glm-4.5 model is available (simplified approach)")
                return True
            elif "glm-4.5" in model_ids and len(model_ids) == 1:
                print("✅ Single glm-4.5 model available")
                return True
            else:
                print(f"❌ Expected only glm-4.5 model. Found: {model_ids}")
                return False
        else:
            print(f"❌ Failed to get models list: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to proxy server. Make sure it's running on localhost:5000")
        return False
    except Exception as e:
        print(f"❌ Error testing model availability: {e}")
        return False

def test_text_request_routing():
    """Test that text requests route correctly"""
    print("🔍 Testing text request routing...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {TEST_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "glm-4.5",
                "messages": [{"role": "user", "content": "Say 'Hello from text model'"}],
                "max_tokens": 50
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Text request successful (should route to Anthropic endpoint)")
            
            # Check usage info if available
            if "usage" in data:
                usage = data["usage"]
                print(f"   Usage: prompt_tokens={usage.get('prompt_tokens')}, "
                     f"completion_tokens={usage.get('completion_tokens')}, "
                     f"total_tokens={usage.get('total_tokens')}")
            
            return True
        else:
            print(f"❌ Text request failed: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                error_data = response.json()
                print(f"   Error: {error_data}")
            else:
                print(f"   Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing text request: {e}")
        return False

def test_token_counting():
    """Test token counting with simplified model"""
    print("🔍 Testing token counting...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/messages/count_tokens",
            headers={
                "Authorization": f"Bearer {TEST_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "glm-4.5",
                "messages": [{"role": "user", "content": "Count tokens for simplified model"}]
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Token counting successful")
            
            if "input_tokens" in data:
                print(f"   Token count: {data['input_tokens']}")
            
            return True
        else:
            print(f"❌ Token counting failed: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                error_data = response.json()
                print(f"   Error: {error_data}")
            else:
                print(f"   Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing token counting: {e}")
        return False

def test_health_endpoint():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") is True:
                print("✅ Health endpoint healthy")
                return True
            else:
                print(f"❌ Health endpoint returned: {data}")
                return False
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
        return False

def main():
    """Run all simplified model tests"""
    print("🚀 Starting simplified glm-4.5 model tests...")
    print("=" * 60)
    
    tests = [
        test_health_endpoint,
        test_single_model_availability,
        test_text_request_routing,
        test_token_counting,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 40)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All simplified model tests passed!")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())