#!/usr/bin/env python3
"""
Simple test suite for x-kilo-followsup header functionality

Tests the x-kilo-followsup feature by validating:
1. Header detection and processing
2. Followup question injection for both endpoints
3. Proper behavior when header is missing
"""

import os
import sys
import json
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY")

def test_x_kilo_followup_feature():
    """Test x-kilo-followsup functionality"""
    print("🧪 Testing x-kilo-followsup functionality...")
    
    if not API_KEY:
        print("⚠️  Warning: SERVER_API_KEY not found in .env file")
        print("   Make sure the proxy server is running and accessible")
        return False
    
    passed = 0
    total = 3
    
    # Test 1: Chat completions with followup header
    print("\n1. Testing /v1/chat/completions with x-kilo-followsup: true")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "x-kilo-followsup": "true"
        }
        
        payload = {
            "model": "glm-4.6",
            "messages": [
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "stream": False
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{API_BASE}/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                if "<ask_followup_question>" in content:
                    print("✅ Followup question correctly added to chat completions")
                    passed += 1
                else:
                    print("❌ Followup question was NOT added to chat completions")
                    print(f"   Response content: {content[:200]}...")
            else:
                print(f"❌ Request failed with status {response.status_code}: {response.text}")
                
    except Exception as e:
        print(f"❌ Error testing chat completions: {e}")
    
    # Test 2: Messages endpoint with followup header
    print("\n2. Testing /v1/messages with x-kilo-followsup: true")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "x-kilo-followsup": "true"
        }
        
        payload = {
            "model": "glm-4.6",
            "messages": [
                {"role": "user", "content": "What is the capital of Spain?"}
            ],
            "max_tokens": 500
        }
        
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
                
                if "<ask_followup_question>" in content:
                    print("✅ Followup question correctly added to messages endpoint")
                    passed += 1
                else:
                    print("❌ Followup question was NOT added to messages endpoint")
                    print(f"   Response content: {content[:200]}...")
            else:
                print(f"❌ Request failed with status {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error testing messages endpoint: {e}")
    
    # Test 3: Chat completions WITHOUT followup header
    print("\n3. Testing /v1/chat/completions WITHOUT x-kilo-followsup header")
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
            # Note: NOT including x-kilo-followsup header
        }
        
        payload = {
            "model": "glm-4.6",
            "messages": [
                {"role": "user", "content": "What is the capital of Italy?"}
            ],
            "stream": False
        }
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{API_BASE}/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                if "<ask_followup_question>" not in content:
                    print("✅ Followup question correctly NOT added when header is missing")
                    passed += 1
                else:
                    print("❌ Followup question was incorrectly added when header is missing")
            else:
                print(f"❌ Request failed with status {response.status_code}")
                
    except Exception as e:
        print(f"❌ Error testing without header: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! x-kilo-followsup functionality is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = test_x_kilo_followup_feature()
    sys.exit(0 if success else 1)