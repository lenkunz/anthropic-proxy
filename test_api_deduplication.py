#!/usr/bin/env python3
"""
Test script to verify environment details deduplication in API calls
"""

import sys
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"

def test_deduplication_in_api():
    """Test environment details deduplication through actual API calls"""
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    # Test message with multiple environment details
    test_messages = [
        {
            "role": "user",
            "content": """First message with environment:
<environment_details>
Workspace: /test/project
Files: main.py, utils.py
Directory: /test/project
</environment_details>

Hello, can you help me?"""
        },
        {
            "role": "assistant", 
            "content": "I can help you with your project."
        },
        {
            "role": "user",
            "content": """Second message with updated environment:
<environment_details>
Workspace: /test/project
Files: main.py, utils.py, new.py
Directory: /test/project
Current directory: /test/project
</environment_details>

What do you think about the new file?"""
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Test both endpoints
    endpoints = [
        "/v1/chat/completions",
        "/v1/messages"
    ]
    
    for endpoint in endpoints:
        print(f"\n=== Testing {endpoint} ===")
        
        if endpoint == "/v1/chat/completions":
            payload = {
                "model": "glm-4.6-anthropic",
                "messages": test_messages,
                "max_tokens": 100
            }
        else:  # /v1/messages
            payload = {
                "model": "glm-4.6-anthropic",
                "messages": test_messages,
                "max_tokens": 100
            }
        
        try:
            response = requests.post(f"{BASE_URL}{endpoint}", 
                                   headers=headers, 
                                   json=payload,
                                   timeout=30)
            
            if response.status_code == 200:
                print(f"✅ {endpoint} request successful")
                
                # Check if response indicates deduplication happened
                response_data = response.json()
                if "usage" in response_data:
                    print(f"   Input tokens: {response_data['usage'].get('input_tokens', 'N/A')}")
                    print(f"   Output tokens: {response_data['usage'].get('output_tokens', 'N/A')}")
                
            else:
                print(f"❌ {endpoint} request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ {endpoint} request timed out")
        except requests.exceptions.ConnectionError:
            print(f"❌ Could not connect to server at {BASE_URL}")
            print("   Make sure the server is running with: docker compose up -d")
        except Exception as e:
            print(f"❌ {endpoint} request error: {e}")
    
    return True

def check_server_health():
    """Check if the server is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except:
        print("❌ Server is not running or not accessible")
        print("   Start the server with: docker compose up -d")
        return False

if __name__ == "__main__":
    print("=== Environment Details Deduplication API Test ===")
    
    if check_server_health():
        test_deduplication_in_api()
    else:
        print("\n💡 To test deduplication:")
        print("1. Start the server: docker compose up -d")
        print("2. Run this script again")
        print("3. Check the logs to see deduplication in action:")
        print("   docker compose logs -f | grep -i dedup")