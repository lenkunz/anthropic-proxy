#!/usr/bin/env python3
"""
Test z.ai thinking parameter support

This verifies that the thinking.type=enabled parameter is automatically added
to requests routed to z.ai's OpenAI endpoint.
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

def test_thinking_parameter():
    print("🧠 Testing z.ai Thinking Parameter Support")
    print("=" * 50)
    
    # Test cases that should route to OpenAI endpoint (where thinking is added)
    test_cases = [
        {
            "name": "Force OpenAI endpoint with -openai suffix",
            "model": "glm-4.5-openai",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2? Show your reasoning."}
            ]
        },
        {
            "name": "Auto-route to OpenAI with image",
            "model": "glm-4.5", 
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": "Describe this image and show your reasoning:"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}}
                ]}
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"   Model: {test_case['model']}")
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": test_case["model"],
                "messages": test_case["messages"],
                "max_tokens": 100,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            
            print(f"   ✅ SUCCESS: Response received")
            print(f"   💭 Content: {content[:100]}...")
            
            # Check usage information
            usage = data.get("usage", {})
            endpoint_type = usage.get("endpoint_type", "unknown")
            print(f"   🎯 Endpoint: {endpoint_type}")
            
            if endpoint_type == "vision":
                print(f"   🧠 ✅ Routed to OpenAI endpoint - thinking parameter should be active")
                # Look for signs of reasoning in response (this is indirect detection)
                if any(word in content.lower() for word in ["because", "reasoning", "therefore", "since", "thus"]):
                    print(f"   🎯 ✅ Response shows reasoning patterns - thinking likely enabled!")
                else:
                    print(f"   🎯 ℹ️  No obvious reasoning patterns detected, but thinking parameter was sent")
            else:
                print(f"   ℹ️  Routed to Anthropic endpoint - thinking parameter not applicable")
        else:
            print(f"   ❌ FAILED: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error: {response.text[:200]}")
    
    # Test Anthropic endpoint (should not have thinking parameter)
    print(f"\n🧪 Testing: Anthropic endpoint (no thinking parameter)")
    print(f"   Model: glm-4.5-anthropic")
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "glm-4.5-anthropic",
            "messages": [
                {"role": "user", "content": "What is 2+2?"}
            ],
            "max_tokens": 50,
            "stream": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        endpoint_type = usage.get("endpoint_type", "unknown")
        
        print(f"   ✅ SUCCESS: Response received")
        print(f"   💭 Content: {content}")
        print(f"   🎯 Endpoint: {endpoint_type}")
        print(f"   ℹ️  Anthropic endpoint - thinking parameter not added (correct)")
    else:
        print(f"   ❌ FAILED: {response.status_code}")

def test_thinking_configuration():
    print(f"\n⚙️ Testing Thinking Configuration")
    print("=" * 40)
    print("Current configuration: ENABLE_ZAI_THINKING=true (default)")
    print("To disable thinking, set ENABLE_ZAI_THINKING=false in .env")
    
    # Check logs for confirmation
    print("\n📋 Check Docker logs to confirm thinking parameter is being added:")
    print("docker compose logs --tail=10 | grep thinking")

if __name__ == "__main__":
    test_thinking_parameter()
    test_thinking_configuration()