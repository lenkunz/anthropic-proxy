#!/usr/bin/env python3
"""
Compare thinking block formats between glm-4.6 and glm-4.5v models
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
OPENAI_UPSTREAM = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")

def test_model_thinking(model_name):
    """Test thinking blocks for a specific model"""
    print(f"\n=== Testing {model_name} ===")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Solve step by step: What is 12 * 15 + 8 * 3?"}
        ],
        "temperature": 0,
        "thinking": {
            "type": "enabled"
        }
    }
    
    try:
        response = requests.post(f"{OPENAI_UPSTREAM}/chat/completions", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {model_name} API call successful")
            
            if 'choices' in data and data['choices']:
                choice = data['choices'][0]
                if 'message' in choice:
                    message = choice['message']
                    
                    # Check for reasoning_content
                    if 'reasoning_content' in message:
                        reasoning = message['reasoning_content']
                        print(f"✅ Found reasoning_content field ({len(reasoning)} chars)")
                        print(f"Reasoning preview: {reasoning[:150]}...")
                    else:
                        print("❌ No reasoning_content field found")
                    
                    # Check for traditional thinking tags in content
                    content = message.get('content', '')
                    if '<thinking>' in content:
                        print("✅ Found <thinking> tags in content")
                        start = content.find('<thinking>')
                        end = content.find('</thinking>')
                        if start != -1 and end != -1:
                            thinking_content = content[start:end + 10]
                            print(f"Thinking tags content: {thinking_content[:150]}...")
                    else:
                        print("❌ No <thinking> tags found in content")
                    
                    # Check for other possible thinking formats
                    if 'thinking' in message and isinstance(message['thinking'], str):
                        print(f"✅ Found thinking field: {message['thinking'][:100]}...")
                    else:
                        print("❌ No separate thinking field found")
                    
                    # Show full message structure
                    print(f"Message keys: {list(message.keys())}")
                    print(f"Content length: {len(content)} chars")
                    
            return data
        else:
            print(f"❌ {model_name} API call failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ {model_name} API call error: {e}")
        return None

def compare_responses(response1, response2, model1, model2):
    """Compare responses from two models"""
    print(f"\n=== Comparing {model1} vs {model2} ===")
    
    if not response1 or not response2:
        print("❌ Cannot compare - one or both responses failed")
        return
    
    # Compare structure
    msg1 = response1['choices'][0]['message']
    msg2 = response2['choices'][0]['message']
    
    print(f"{model1} message keys: {list(msg1.keys())}")
    print(f"{model2} message keys: {list(msg2.keys())}")
    
    # Compare reasoning content
    rc1 = msg1.get('reasoning_content', '')
    rc2 = msg2.get('reasoning_content', '')
    
    print(f"\n{model1} reasoning_content length: {len(rc1)} chars")
    print(f"{model2} reasoning_content length: {len(rc2)} chars")
    
    # Compare content
    c1 = msg1.get('content', '')
    c2 = msg2.get('content', '')
    
    print(f"{model1} content length: {len(c1)} chars")
    print(f"{model2} content length: {len(c2)} chars")
    
    # Check for any differences in format
    differences = []
    
    if ('reasoning_content' in msg1) != ('reasoning_content' in msg2):
        differences.append("reasoning_content field presence differs")
    
    if ('thinking' in msg1) != ('thinking' in msg2):
        differences.append("thinking field presence differs")
    
    if ('<thinking>' in c1) != ('<thinking>' in c2):
        differences.append("<thinking> tags in content differ")
    
    if differences:
        print(f"\n🔍 Differences found: {differences}")
    else:
        print(f"\n✅ No structural differences found")

def main():
    """Run comparison tests"""
    print("🔍 Comparing thinking block formats between models...")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return
    
    # Test both models
    response_46 = test_model_thinking("glm-4.6")
    response_45v = test_model_thinking("glm-4.5v")
    
    # Compare responses
    compare_responses(response_46, response_45v, "glm-4.6", "glm-4.5v")
    
    print("\n🏁 Comparison complete!")

if __name__ == "__main__":
    main()