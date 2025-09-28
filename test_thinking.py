#!/usr/bin/env python3

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('SERVER_API_KEY')
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

def test_thinking_parameter():
    """Test if thinking parameter is being sent to upstream"""
    
    print("🧠 Testing z.ai thinking parameter functionality")
    print("=" * 50)
    
    # Test with glm-4.5-openai (should force OpenAI endpoint)
    print("\n🔍 Testing model: glm-4.5-openai")
    
    payload = {
        'model': 'glm-4.5-openai',
        'messages': [
            {
                'role': 'user', 
                'content': 'Think step by step: What is 2+2? Show your reasoning process.'
            }
        ],
        'max_tokens': 100,
        'temperature': 0.1
    }
    
    try:
        response = requests.post(
            f'{BASE_URL}/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            },
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check response structure
            print(f"✅ Status: {response.status_code}")
            
            if 'usage' in data:
                endpoint_type = data['usage'].get('endpoint_type', 'unknown')
                print(f"📍 Endpoint: {endpoint_type}")
                
                if endpoint_type == 'vision':
                    print("✅ SUCCESS: Request routed to OpenAI endpoint (thinking parameter should be active)")
                else:
                    print("⚠️ WARNING: Request went to text endpoint instead of OpenAI endpoint")
            
            if 'choices' in data and data['choices']:
                content = data['choices'][0].get('message', {}).get('content', '')
                print(f"📝 Response length: {len(content)} chars")
                
                # Look for reasoning indicators
                reasoning_indicators = ['step', 'think', 'reason', 'because', 'first', 'then', 'therefore']
                reasoning_count = sum(1 for indicator in reasoning_indicators if indicator.lower() in content.lower())
                
                print(f"🧠 Reasoning indicators found: {reasoning_count}/7")
                
                if reasoning_count >= 3:
                    print("✅ Response appears to show reasoning process")
                else:
                    print("⚠️ Response may not show detailed reasoning")
                    
                # Show first part of response
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"📖 Response preview:\n{preview}")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

    print("\n" + "=" * 50)
    print("🔍 Check container logs for thinking parameter debug messages:")
    print("docker compose logs --tail=20 | grep -i thinking")

if __name__ == "__main__":
    test_thinking_parameter()