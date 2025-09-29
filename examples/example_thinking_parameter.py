#!/usr/bin/env python3
"""
Example: z.ai Thinking Parameter Usage
Demonstrates how the ENABLE_ZAI_THINKING parameter works with different model variants.

This example shows:
1. How thinking parameter is automatically added to OpenAI endpoint requests
2. Comparison between different model variants
3. How to control thinking parameter behavior
4. Request logging verification
"""

import os
import json
import time
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    print("Please create a .env file from .env.example and set your API key")
    exit(1)

BASE_URL = "http://localhost:5000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "x-api-key": API_KEY
}

def make_request(model, message="Explain quantum computing in simple terms.", use_thinking=None):
    """Make a chat completion request with optional thinking parameter override."""
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": message}
        ],
        "max_tokens": 150
    }
    
    # Override thinking parameter if specified (for testing purposes)
    if use_thinking is not None:
        payload["thinking"] = {"type": "enabled" if use_thinking else "disabled"}
    
    print(f"\n🔄 Making request with model: {model}")
    print(f"   Message: {message[:50]}...")
    
    response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                           json=payload, 
                           headers=HEADERS)
    
    if response.status_code == 200:
        result = response.json()
        usage = result.get("usage", {})
        endpoint_type = usage.get("endpoint_type", "unknown")
        
        print(f"✅ Success! Response from {endpoint_type} endpoint")
        print(f"   Tokens used: {usage.get('total_tokens', 'unknown')}")
        print(f"   Response preview: {result['choices'][0]['message']['content'][:100]}...")
        
        # Check if we can find evidence of thinking parameter in logs
        return {
            "success": True,
            "endpoint_type": endpoint_type,
            "usage": usage,
            "response_length": len(result['choices'][0]['message']['content'])
        }
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   Response: {response.text}")
        return {"success": False, "error": response.text}

def check_upstream_logs():
    """Check upstream request logs for thinking parameter evidence."""
    log_files = [
        "logs/upstream_requests.json"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n📋 Checking {log_file} for thinking parameter evidence...")
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-5:]  # Check last 5 log entries
                    
                for line in recent_lines:
                    try:
                        log_entry = json.loads(line.strip())
                        if "thinking" in str(log_entry):
                            print(f"✅ Found thinking parameter in logs:")
                            print(f"   Endpoint: {log_entry.get('endpoint_type', 'unknown')}")
                            print(f"   Timestamp: {log_entry.get('timestamp', 'unknown')}")
                            return True
                    except json.JSONDecodeError:
                        continue
                        
                print(f"ℹ️  No thinking parameter found in recent {log_file} entries")
            except Exception as e:
                print(f"⚠️  Could not read {log_file}: {e}")
        else:
            print(f"ℹ️  Log file {log_file} does not exist")
    
    return False

def main():
    """Run comprehensive thinking parameter demonstration."""
    print("🧠 z.ai Thinking Parameter Usage Example")
    print("=" * 50)
    
    # Check proxy health first
    try:
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code != 200:
            print("❌ Proxy server is not healthy")
            return
        print("✅ Proxy server is healthy")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to proxy server. Is it running on http://localhost:5000?")
        return
    
    print("\n1. Testing Model Variants (Thinking Parameter Behavior)")
    print("-" * 55)
    
    test_cases = [
        {
            "model": "glm-4.5",
            "description": "Auto-routing model (text → Anthropic, should NOT get thinking parameter)",
            "expected_endpoint": "anthropic"
        },
        {
            "model": "glm-4.5-openai",
            "description": "Force OpenAI model (should get thinking parameter)",
            "expected_endpoint": "openai"
        },
        {
            "model": "glm-4.5-anthropic",
            "description": "Force Anthropic model (should NOT get thinking parameter)",
            "expected_endpoint": "anthropic"
        }
    ]
    
    results = []
    for test_case in test_cases:
        print(f"\n📝 Test: {test_case['description']}")
        result = make_request(test_case["model"])
        result["expected_endpoint"] = test_case["expected_endpoint"]
        result["model"] = test_case["model"]
        results.append(result)
        
        # Small delay to ensure log ordering
        time.sleep(1)
    
    print("\n2. Testing Image Request (Should Route to OpenAI with Thinking)")
    print("-" * 60)
    
    image_request_message = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "What do you see in this image?"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAAAD/2wBDAAEBAQEBAQ=="  # Minimal base64 image
                }
            }
        ]
    }]
    
    image_payload = {
        "model": "glm-4.5",  # Auto-routing should go to OpenAI for images
        "messages": image_request_message,
        "max_tokens": 150
    }
    
    print("\n🖼️ Making image request (should route to OpenAI with thinking parameter)")
    image_response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                                 json=image_payload, 
                                 headers=HEADERS)
    
    if image_response.status_code == 200:
        image_result = image_response.json()
        image_usage = image_result.get("usage", {})
        print(f"✅ Image request routed to: {image_usage.get('endpoint_type', 'unknown')}")
    else:
        print(f"❌ Image request failed: {image_response.status_code}")
    
    time.sleep(2)  # Wait for logs to be written
    
    print("\n3. Checking Upstream Request Logs")
    print("-" * 40)
    found_thinking = check_upstream_logs()
    
    print("\n4. Summary")
    print("-" * 15)
    
    openai_requests = [r for r in results if r.get("success") and r.get("endpoint_type") == "openai"]
    anthropic_requests = [r for r in results if r.get("success") and r.get("endpoint_type") == "anthropic"]
    
    print(f"✅ Successful requests: {len([r for r in results if r.get('success')])}")
    print(f"📊 OpenAI endpoints (should have thinking): {len(openai_requests)}")
    print(f"📊 Anthropic endpoints (no thinking): {len(anthropic_requests)}")
    
    if found_thinking:
        print(f"🧠 Thinking parameter evidence found in logs")
    else:
        print(f"ℹ️  No thinking parameter evidence found in logs (check logs/upstream_requests.json)")
    
    print("\n5. Configuration Notes")
    print("-" * 25)
    print("• ENABLE_ZAI_THINKING=true (default) adds thinking parameter to OpenAI requests")
    print("• Thinking parameter: {\"type\": \"enabled\"}")
    print("• Only applied to OpenAI endpoint requests (glm-4.5-openai, image requests)")
    print("• Anthropic endpoint requests do NOT get thinking parameter")
    print("• Check logs/upstream_requests.json for full request payloads")
    
    print(f"\n🎉 Thinking parameter demonstration complete!")

if __name__ == "__main__":
    main()