#!/usr/bin/env python3
"""Test error logging without API keys by triggering validation errors"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test_error_logging():
    """Test that causes validation errors to trigger enhanced logging"""
    print("🧪 Testing Enhanced Error Logging (No API Key Required)")
    print("=" * 60)
    
    # Test 1: Missing API key
    print("\n=== Test 1: Missing API Key ===")
    payload = {
        "model": "glm-4.5",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 100
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                                json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Invalid JSON
    print("\n=== Test 2: Invalid JSON ===")
    invalid_json = '{"model": "glm-4.5", "messages": [{"role": "user",}'  # Broken JSON
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                                data=invalid_json, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Missing required fields
    print("\n=== Test 3: Missing Required Fields ===")
    payload = {
        "model": "glm-4.5",
        # Missing messages field
        "max_tokens": 100
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                                json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"\n⏳ Waiting 2 seconds for logs to be written...")
    time.sleep(2)
    
    return True

def check_recent_logs():
    """Check for recent log entries"""
    print("\n=== Checking Recent Logs ===")
    
    import os
    logs_dir = "/home/souta/IKP/cs-refactor/cashout/anthropic-proxy/logs"
    
    try:
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.json')]
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
        
        # Check most recent files
        for log_file in log_files[:3]:
            log_path = os.path.join(logs_dir, log_file)
            print(f"\n📄 Recent entries in {log_file}:")
            
            try:
                # Read the last few lines
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-3:]:  # Last 3 lines
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                print(f"  ⏰ {entry.get('timestamp', 'no timestamp')}")
                                print(f"  🔍 Type: {entry.get('type', 'unknown')}")
                                if 'where' in entry:
                                    print(f"  📍 Where: {entry['where']}")
                                if 'exc' in entry:
                                    print(f"  ⚠️  Exception: {entry['exc'].get('type', 'unknown')}")
                                if 'status_code' in entry:
                                    print(f"  📊 Status: {entry['status_code']}")
                                print("  " + "-"*40)
                            except json.JSONDecodeError:
                                print(f"  📝 Raw log: {line[:100]}...")
            except Exception as e:
                print(f"  ❌ Error reading {log_file}: {e}")
                
    except Exception as e:
        print(f"❌ Could not access logs: {e}")

def main():
    """Run the error logging test"""
    test_error_logging()
    check_recent_logs()
    
    print(f"\n📊 Test completed! Check logs for enhanced error context.")

if __name__ == "__main__":
    main()