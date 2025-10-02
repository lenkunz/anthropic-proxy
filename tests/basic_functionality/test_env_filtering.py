#!/usr/bin/env python3
"""
Test environment details filtering functionality
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
PROXY_BASE_URL = "http://localhost:5000"

def test_env_filtering():
    """Test environment details filtering with multiple messages containing env details"""
    print("🔍 Testing Environment Details Filtering...")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create test messages with multiple environment details blocks
    messages = [
        {
            "role": "user", 
            "content": "Help me understand this code"
        },
        {
            "role": "assistant",
            "content": "I'll help you understand the code. First, let me check the current environment.\n\n<n\nNow let's analyze the code structure..."
        },
        {
            "role": "user",
            "content": "Can you explain the main function?"
        },
        {
            "role": "assistant", 
            "content": "Let me examine the main function in the context.\n\n```environment\nCurrent directory: /home/user/project\nFiles: main.py, utils.py, config.json\nGit status: clean\nPython version: 3.9\nWorking directory: /home/user/project\n```\n\nThe main function is the entry point of the application..."
        },
        {
            "role": "user",
            "content": "What about the utils module?"
        },
        {
            "role": "assistant",
            "content": "Looking at the utils module:\n\nEnvironment: /home/user/project\nFiles: main.py, utils.py, config.json\nStatus: clean\nPython: 3.9\n\nThe utils module contains helper functions..."
        }
    ]
    
    payload = {
        "model": "glm-4.6-openai",
        "messages": messages,
        "max_tokens": 500
    }
    
    try:
        print(f"Making request with {len(messages)} messages containing environment details...")
        response = requests.post(f"{PROXY_BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Request successful")
            
            # Check if environment details were filtered
            if 'choices' in data and data['choices']:
                choice = data['choices'][0]
                if 'message' in choice:
                    content = choice['message'].get('content', '')
                    
                    # Count environment details occurrences
                    env_details_count = content.count('<, "```environment\nCurrent dir: /test\n```", "Environment: /test directory", "Context: Working in /test", "Workspace: /test/project"
    ]
    
    for i, env_format in enumerate(formats):
        print(f"\nTesting format {i+1}: {env_format[:30]}...")
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "user", "content": f"Test message {env_format}"},
            {"role": "assistant", "content": f"Response with {env_format} Analysis..."}
        ]
        
        payload = {
            "model": "glm-4.6-openai",
            "messages": messages,
            "max_tokens": 100
        }
        
        try:
            response = requests.post(f"{PROXY_BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and data['choices']:
                    content = data['choices'][0]['message'].get('content', '')
                    if env_format not in content:
                        print(f"  ✅ Format {i+1} filtered out")
                    else:
                        print(f"  ⚠️  Format {i+1} still present")
            else:
                print(f"  ❌ Format {i+1} test failed: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Format {i+1} test error: {e}")

def check_deduplication_stats():
    """Check deduplication statistics if available"""
    print("\n🔍 Checking Deduplication Statistics...")
    
    try:
        # Try to access stats endpoint if it exists
        response = requests.get(f"{PROXY_BASE_URL}/stats", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            if 'environment_deduplication' in stats:
                env_stats = stats['environment_deduplication']
                print("✅ Environment deduplication statistics found:")
                for key, value in env_stats.items():
                    print(f"  {key}: {value}")
            else:
                print("❌ No environment deduplication statistics found")
        else:
            print("⚠️  Stats endpoint not available")
            
    except Exception as e:
        print(f"⚠️  Could not check stats: {e}")

def main():
    """Run all environment filtering tests"""
    print("🚀 Starting Environment Details Filtering Tests...")
    
    # Test main filtering functionality
    filtering_works = test_env_filtering()
    
    # Test different formats
    test_different_env_formats()
    
    # Check statistics
    check_deduplication_stats()
    
    print(f"\n🏁 Environment Filtering Test Results:")
    if filtering_works:
        print("✅ Environment details filtering appears to be working")
    else:
        print("❌ Environment details filtering may have issues")
    
    print("\n💡 If filtering is not working, check:")
    print("1. ENABLE_ENV_DEDUPLICATION=true in .env")
    print("2. ENV_DEDUPLICATION_LOGGING=true for debug info")
    print("3. Proxy server logs for deduplication activity")

if __name__ == "__main__":
    main()