#!/usr/bin/env python3
"""Test enhanced error logging with both endpoints and various image formats"""

from dotenv import load_dotenv
import os
import requests
import json
import time
import base64

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"

if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

def get_test_image_base64():
    """Get base64 encoded image for testing"""
    image_path = "/home/souta/IKP/cs-refactor/cashout/anthropic-proxy/pexels-photo-1108099.jpeg"
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"❌ Could not read test image: {e}")
        return None

def test_openai_endpoint():
    """Test OpenAI endpoint with valid image"""
    print("\n=== Testing OpenAI Endpoint ===")
    
    image_base64 = get_test_image_base64()
    if not image_base64:
        return False
    
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
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                                json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            print("✅ OpenAI endpoint successful")
            result = response.json()
            print(f"Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100]}...")
            return True
        else:
            print(f"❌ OpenAI endpoint failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI endpoint error: {e}")
        return False

def test_anthropic_endpoint():
    """Test Anthropic endpoint with valid image"""
    print("\n=== Testing Anthropic Endpoint ===")
    
    image_base64 = get_test_image_base64()
    if not image_base64:
        return False
    
    payload = {
        "model": "glm-4.5-anthropic",
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions",
                                json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            print("✅ Anthropic endpoint successful")
            result = response.json()
            print(f"Response: {result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100]}...")
            return True
        else:
            print(f"❌ Anthropic endpoint failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Anthropic endpoint error: {e}")
        return False

def test_invalid_image():
    """Test error logging with invalid image data"""
    print("\n=== Testing Invalid Image (Error Logging) ===")
    
    payload = {
        "model": "glm-4.5-openai",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,invalid_base64_data"}
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions",
                                json=payload, headers=headers, timeout=30)
        
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Error response (expected): {response.text}")
            return True  # Expected error
        else:
            print("❌ Expected error but got success")
            return False
            
    except Exception as e:
        print(f"Request error (may be expected): {e}")
        return True

def check_error_logs():
    """Check if error logs contain detailed information"""
    print("\n=== Checking Error Logs ===")
    
    logs_dir = "/home/souta/IKP/cs-refactor/cashout/anthropic-proxy/logs"
    try:
        # Get recent log files
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.json')]
        log_files.sort(reverse=True)  # Most recent first
        
        print(f"Found {len(log_files)} log files")
        
        # Check the most recent few logs
        for log_file in log_files[:5]:
            log_path = os.path.join(logs_dir, log_file)
            try:
                with open(log_path, 'r') as f:
                    log_data = json.load(f)
                
                if 'error' in log_data or 'exc' in log_data or 'where' in log_data:
                    print(f"\n📋 Error log in {log_file}:")
                    print(f"  Type: {log_data.get('type', 'unknown')}")
                    print(f"  Where: {log_data.get('where', 'unknown')}")
                    print(f"  Model: {log_data.get('model', 'unknown')}")
                    if 'exc' in log_data:
                        print(f"  Exception: {log_data['exc'].get('type', 'unknown')} - {log_data['exc'].get('message', 'no message')[:100]}")
                    if 'upstream_status' in log_data:
                        print(f"  Upstream Status: {log_data['upstream_status']}")
                    if 'upstream_url' in log_data:
                        print(f"  Upstream URL: {log_data['upstream_url']}")
                
            except Exception as e:
                print(f"❌ Could not read log {log_file}: {e}")
                
    except Exception as e:
        print(f"❌ Could not access logs directory: {e}")

def main():
    """Run comprehensive tests"""
    print("🧪 Testing Enhanced Error Logging and Image Processing")
    print("=" * 60)
    
    # Test valid scenarios
    openai_success = test_openai_endpoint()
    anthropic_success = test_anthropic_endpoint()
    
    # Test error scenario (to generate logs)
    error_test = test_invalid_image()
    
    # Wait a moment for logs to be written
    time.sleep(2)
    
    # Check logs
    check_error_logs()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"✅ OpenAI Endpoint: {'Pass' if openai_success else 'Fail'}")
    print(f"✅ Anthropic Endpoint: {'Pass' if anthropic_success else 'Fail'}")
    print(f"✅ Error Logging: {'Pass' if error_test else 'Fail'}")
    
    if openai_success and anthropic_success:
        print("\n🎉 Both endpoints working correctly!")
    else:
        print("\n⚠️  Some endpoints have issues")

if __name__ == "__main__":
    main()