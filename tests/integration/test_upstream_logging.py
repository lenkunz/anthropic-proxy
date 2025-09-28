#!/usr/bin/env python3
"""Test upstream response logging by making various requests"""

import requests
import json
import time
import os
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY", "test-key")

def test_upstream_logging():
    """Test various requests to trigger upstream response logging"""
    print("🧪 Testing Upstream Response Logging")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Simple text request to OpenAI endpoint
    print("\n=== Test 1: OpenAI Endpoint - Text Request ===")
    payload = {
        "model": "glm-4.5-openai",
        "messages": [{"role": "user", "content": "Hello, how are you?"}],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                                json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Simple text request to Anthropic endpoint
    print("\n=== Test 2: Anthropic Endpoint - Text Request ===")
    payload = {
        "model": "glm-4.5-anthropic", 
        "messages": [{"role": "user", "content": "What's the weather like?"}],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions",
                                json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Anthropic /v1/messages endpoint
    print("\n=== Test 3: Anthropic /v1/messages Endpoint ===")
    payload = {
        "model": "glm-4.5",
        "messages": [{"role": "user", "content": "Tell me a joke"}],
        "max_tokens": 100
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/messages",
                                json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 4: Request with image (if available)
    print("\n=== Test 4: OpenAI Endpoint - Image Request ===")
    image_path = "/home/souta/IKP/cs-refactor/cashout/anthropic-proxy/pexels-photo-1108099.jpeg"
    
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            payload = {
                "model": "glm-4.5-openai",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What's in this image?"},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 100
            }
            
            response = requests.post(f"{BASE_URL}/v1/chat/completions",
                                    json=payload, headers=headers, timeout=60)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Test image not found, skipping image test")
    
    # Test 5: Invalid request to trigger error logging
    print("\n=== Test 5: Invalid Request - Error Logging ===")
    payload = {
        "model": "nonexistent-model",
        "messages": [{"role": "user", "content": "This should fail"}],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions",
                                json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    print(f"\n⏳ Waiting 3 seconds for logs to be written...")
    time.sleep(3)

def check_upstream_response_logs():
    """Check if upstream response logs were created"""
    print("\n=== Checking Upstream Response Logs ===")
    
    logs_dir = "/home/souta/IKP/cs-refactor/cashout/anthropic-proxy/logs"
    
    try:
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.json')]
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
        
        upstream_logs_found = 0
        
        # Check most recent files for upstream response logs
        for log_file in log_files[:5]:
            log_path = os.path.join(logs_dir, log_file)
            print(f"\n📄 Checking {log_file}...")
            
            try:
                # Read the last few lines
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-10:]:  # Last 10 lines
                        line = line.strip()
                        if line:
                            try:
                                entry = json.loads(line)
                                # Check if this is an upstream response log entry
                                if (entry.get('message', '').startswith('upstream_response') or 
                                    (entry.get('data', {}).get('endpoint_type') in ['openai', 'anthropic'])):
                                    upstream_logs_found += 1
                                    data = entry.get('data', {})
                                    print(f"  🎯 Found upstream response log:")
                                    print(f"     ⏰ {entry.get('timestamp', 'no timestamp')}")
                                    print(f"     🌐 Endpoint: {data.get('endpoint_type', 'unknown')}")
                                    print(f"     🤖 Model: {data.get('model', 'unknown')}")
                                    print(f"     📊 Status: {data.get('status_code', 'unknown')}")
                                    print(f"     ⏱️  Response Time: {data.get('response_time_ms', 'unknown')}ms")
                                    print(f"     📏 Content Length: {data.get('content_length', 'unknown')} bytes")
                                    if data.get('usage_info'):
                                        print(f"     🔢 Usage: {data['usage_info']}")
                                    print(f"     🔗 URL: {data.get('url', 'unknown')}")
                                    print("     " + "-"*50)
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                print(f"  ❌ Error reading {log_file}: {e}")
                
        print(f"\n📈 Summary: Found {upstream_logs_found} upstream response log entries")
        
        if upstream_logs_found > 0:
            print("✅ Upstream response logging is working!")
        else:
            print("⚠️  No upstream response logs found - check if requests reached upstream")
                
    except Exception as e:
        print(f"❌ Could not access logs: {e}")

def main():
    """Run upstream response logging tests"""
    test_upstream_logging()
    check_upstream_response_logs()
    
    print(f"\n🎉 Upstream response logging test completed!")

if __name__ == "__main__":
    main()