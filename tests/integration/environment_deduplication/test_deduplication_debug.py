#!/usr/bin/env python3
"""
Debug script to test environment details deduplication with logging
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

def test_with_large_context():
    """Test with many environment details to trigger deduplication"""
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    # Create a conversation with many environment details to trigger deduplication
    messages = []
    
    # Add many messages with environment details to fill up context
    for i in range(10):
        messages.append({
            "role": "user",
            "content": f"""Message {i+1} with environment details:


Please help me with task {i+1}."""
        })
        
        messages.append({
            "role": "assistant",
            "content": f"I'll help you with task {i+1}. Here's what you need to do..."
        })
    
    # Add final message with more environment details
    messages.append({
        "role": "user",
        "content": """Final message with latest environment:


Now let's work on the final task."""
    })
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.6-anthropic",
        "messages": messages,
        "max_tokens": 50
    }
    
    print(f"Sending request with {len(messages)} messages...")
    print("This should trigger environment details deduplication due to multiple environment blocks.")
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                               headers=headers, 
                               json=payload,
                               timeout=60)
        
        if response.status_code == 200:
            print("✅ Request successful")
            response_data = response.json()
            if "usage" in response_data:
                print(f"   Input tokens: {response_data['usage'].get('input_tokens', 'N/A')}")
                print(f"   Output tokens: {response_data['usage'].get('output_tokens', 'N/A')}")
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False

def check_deduplication_logs():
    """Check recent logs for deduplication activity"""
    print("\n=== Checking for deduplication logs ===")
    try:
        result = os.popen("docker compose logs --tail=50 | grep -i dedup").read()
        if result.strip():
            print("Found deduplication logs:")
            print(result)
        else:
            print("No deduplication logs found in recent output")
            print("This could mean:")
            print("1. No environment details were detected")
            print("2. Deduplication wasn't triggered")
            print("3. Logging is not working properly")
    except Exception as e:
        print(f"Error checking logs: {e}")

if __name__ == "__main__":
    print("=== Environment Details Deduplication Debug Test ===")
    
    # Check server health first
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not healthy")
            exit(1)
    except:
        print("❌ Server is not running")
        print("Start with: docker compose up -d")
        exit(1)
    
    print("✅ Server is running")
    
    # Run test with large context
    if test_with_large_context():
        print("\n✅ Test completed successfully")
        
        # Check logs
        check_deduplication_logs()
        
        print("\n💡 Next steps:")
        print("1. Check the logs above for deduplication activity")
        print("2. If no deduplication logs appear, the system may not be detecting environment details")
        print("3. Check upstream logs to see what's actually being sent to the API")
        
    else:
        print("❌ Test failed")