#!/usr/bin/env python3
"""
Debug script to check if environment details are actually being removed from upstream requests.
This will make a real request and check what's being sent upstream.
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
PROXY_BASE_URL = "http://localhost:5000"

def test_upstream_deduplication():
    """Test if environment details are actually removed from upstream requests"""
    print("🔍 Testing Upstream Environment Details Deduplication...")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create test messages with CLEAR environment details that should be removed
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "First message"
                },
                {
                    "type": "text",
                    "text": "<environment_details>\n# VSCode Visible Files\ntest.py, utils.py\n\n# Current Time\nCurrent time in ISO 8601 UTC format: 2025-10-01T17:40:00.000Z\nUser time zone: Asia/Bangkok, UTC+7\n\n# Current Cost\n$0.00\n\n# Current Mode\n<slug>code</slug>\n<name>Code</name>\n<model>glm-4.6-openai</model>\n====\n\nREMINDERS\n\n| # | Content | Status |\n|---|---------|--------|\n| 1 | Test task | Completed |\n\n</environment_details>"
                }
            ]
        },
        {
            "role": "assistant",
            "content": "I understand you have a test task."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Second message"
                },
                {
                    "type": "text",
                    "text": "<environment_details>\n# VSCode Visible Files\ntest.py, utils.py, config.json\n\n# Current Time\nCurrent time in ISO 8601 UTC format: 2025-10-01T17:41:00.000Z\nUser time zone: Asia/Bangkok, UTC+7\n\n# Current Cost\n$0.00\n\n# Current Mode\n<slug>code</slug>\n<name>Code</name>\n<model>glm-4.6-openai</model>\n====\n\nREMINDERS\n\n| # | Content | Status |\n|---|---------|--------|\n| 1 | Second task | In Progress |\n\n</environment_details>"
                }
            ]
        }
    ]
    
    payload = {
        "model": "glm-4.6-openai",
        "messages": messages,
        "max_tokens": 100,
        "temperature": 0
    }
    
    # Count environment details in original request
    original_env_count = 0
    for msg in messages:
        if msg['role'] == 'user' and isinstance(msg['content'], list):
            for part in msg['content']:
                if isinstance(part, dict) and part.get('type') == 'text':
                    if '<environment_details>' in part.get('text', ''):
                        original_env_count += 1
    
    print(f"Original environment details count: {original_env_count}")
    
    try:
        print("Making request to check upstream deduplication...")
        
        # Make the request
        response = requests.post(f"{PROXY_BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            print("✅ Request successful")
            
            # Check the most recent upstream request log
            try:
                # Read the upstream request log
                log_file = "logs/upstream_requests.json"
                if os.path.exists(log_file):
                    print(f"Checking log file: {log_file}")
                    
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                    
                    # Parse the last log entry
                    log_lines = log_content.strip().split('\n')
                    if log_lines:
                        last_log = json.loads(log_lines[-1])
                        
                        # Check the upstream payload
                        upstream_payload = last_log.get('payload', {})
                        upstream_messages = upstream_payload.get('messages', [])
                        
                        print(f"Upstream messages count: {len(upstream_messages)}")
                        
                        # Count environment details in upstream request
                        upstream_env_count = 0
                        for msg in upstream_messages:
                            if msg.get('role') == 'user':
                                content = msg.get('content', [])
                                if isinstance(content, list):
                                    for part in content:
                                        if isinstance(part, dict) and part.get('type') == 'text':
                                            text = part.get('text', '')
                                            if '<environment_details>' in text:
                                                upstream_env_count += 1
                                                print(f"Found environment_details in upstream message: {text[:100]}...")
                                elif isinstance(content, str):
                                    if '<environment_details>' in content:
                                        upstream_env_count += 1
                                        print(f"Found environment_details in upstream string content: {content[:100]}...")
                        
                        print(f"Environment details in original request: {original_env_count}")
                        print(f"Environment details in upstream request: {upstream_env_count}")
                        
                        if upstream_env_count == 0:
                            print("✅ SUCCESS: Environment details were removed from upstream request!")
                            return True
                        elif upstream_env_count < original_env_count:
                            print(f"⚠️  PARTIAL SUCCESS: {original_env_count - upstream_env_count} environment details removed")
                            return True
                        else:
                            print("❌ FAILURE: Environment details were NOT removed from upstream request")
                            print("This confirms the deduplication is not working properly")
                            return False
                    else:
                        print("❌ No log entries found")
                        return False
                else:
                    print("❌ No upstream request log files found")
                    return False
                    
            except Exception as e:
                print(f"❌ Error checking upstream logs: {e}")
                return False
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False

def check_deduplication_config():
    """Check if deduplication is properly configured"""
    print("\n🔍 Checking Deduplication Configuration...")
    
    # Check environment variables
    enable_env_deduplication = os.getenv("ENABLE_ENV_DEDUPLICATION", "true").lower() in ("true", "1", "yes")
    env_deduplication_strategy = os.getenv("ENV_DEDUPLICATION_STRATEGY", "keep_latest")
    env_deduplication_logging = os.getenv("ENV_DEDUPLICATION_LOGGING", "false").lower() in ("true", "1", "yes")
    
    print(f"ENABLE_ENV_DEDUPLICATION: {enable_env_deduplication}")
    print(f"ENV_DEDUPLICATION_STRATEGY: {env_deduplication_strategy}")
    print(f"ENV_DEDUCTION_AVAILABLE: {enable_env_deduplication}")  # This should match the import check
    
    if not enable_env_deduplication:
        print("❌ DEDUPLICATION IS DISABLED! This explains why nothing is being removed.")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Upstream Deduplication Debug...")
    
    # Check configuration first
    config_ok = check_deduplication_config()
    
    if config_ok:
        # Test actual upstream deduplication
        dedup_works = test_upstream_deduplication()
        
        print(f"\n🏁 Results:")
        if dedup_works:
            print("✅ Environment details deduplication is working correctly")
        else:
            print("❌ Environment details deduplication is NOT working")
            print("💡 Possible causes:")
            print("   - Deduplication disabled in configuration")
            print("   - Environment details patterns not matching")
            print("   - Deduplication logic not being called")
            print("   - Integration issue in main.py")
    else:
        print("❌ Configuration issues prevent deduplication from working")