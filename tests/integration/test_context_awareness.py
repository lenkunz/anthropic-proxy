#!/usr/bin/env python3
"""
Test real token count reporting to clients

This demonstrates the new feature where clients receive accurate token information
so they can manage context without triggering API errors.
"""

import requests
import json
import os
from dotenv import load_dotenv
import tiktoken

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

def test_context_awareness():
    print("🧪 Testing Client Context Awareness")
    print("=" * 50)
    
    # Test different conversation sizes to see token reporting
    test_cases = [
        {
            "name": "Small conversation", 
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2?"}
            ]
        },
        {
            "name": "Medium conversation",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Explain machine learning in detail." + " Please provide comprehensive information." * 50},
                {"role": "assistant", "content": "Machine learning is a subset of artificial intelligence." + " It involves training algorithms on data." * 100},
                {"role": "user", "content": "Now explain neural networks with examples and mathematical formulations." + " Be very detailed." * 30}
            ]
        },
        {
            "name": "Large conversation (approaching limits)",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant specialized in detailed explanations."},
            ] + [
                {"role": "user" if i % 2 == 0 else "assistant", 
                 "content": f"Message {i}: " + "This is a detailed explanation with lots of information. " * 200}
                for i in range(20)
            ] + [
                {"role": "user", "content": "Please summarize everything we discussed."}
            ]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 {test_case['name']}")
        
        # Estimate size
        # Use tiktoken for accurate token counting
        try:
            encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
            total_tokens = 0
            for msg in test_case['messages']:
                content = msg.get('content', '')
                if isinstance(content, str):
                    total_tokens += len(encoding.encode(content))
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            total_tokens += len(encoding.encode(item.get('text', '')))
            
            total_chars = sum(len(str(msg)) for msg in test_case['messages'])
            print(f"   📊 Messages: {len(test_case['messages'])}")
            print(f"   📊 Exact tokens: {total_tokens:,}")
        except Exception as e:
            # Fallback to rough estimation
            total_chars = sum(len(str(msg)) for msg in test_case['messages'])
            estimated_tokens = total_chars // 3
            print(f"   📊 Messages: {len(test_case['messages'])}")
            print(f"   📊 Estimated tokens: ~{estimated_tokens:,}")
        
        # Test with different models to see different limits
        for model in ["glm-4.5", "glm-4.5-openai"]:
            print(f"\n   🤖 Testing with model: {model}")
            
            response = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": model,
                    "messages": test_case['messages'],
                    "max_tokens": 100,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for context information
                context_info = data.get("context_info", {})
                usage = data.get("usage", {})
                
                print(f"   ✅ Response received")
                print(f"   📈 Usage tokens: {usage.get('prompt_tokens', 'N/A')} input, {usage.get('completion_tokens', 'N/A')} output")
                
                if context_info:
                    print(f"   🎯 REAL input tokens: {context_info.get('real_input_tokens', 'N/A')}")
                    print(f"   🎯 Context limit: {context_info.get('context_hard_limit', 'N/A')} ({context_info.get('endpoint_type', 'unknown')})")
                    print(f"   🎯 Utilization: {context_info.get('utilization_percent', 'N/A')}%")
                    print(f"   🎯 Available: {context_info.get('available_tokens', 'N/A')} tokens")
                    
                    if context_info.get('truncated', False):
                        print(f"   ⚠️  TRUNCATED: {context_info.get('original_tokens', 'N/A')} → {context_info.get('real_input_tokens', 'N/A')} tokens")
                        print(f"   ⚠️  Reason: {context_info.get('truncation_reason', 'Unknown')}")
                        print(f"   💡 Note: {context_info.get('note', 'Client should manage context')}")
                    else:
                        print(f"   ✨ No truncation - client controlled successfully!")
                else:
                    print(f"   ⚠️  No context_info found in response (feature may not be active)")
                
                # Check real token counts in usage
                real_input = usage.get('real_input_tokens')
                if real_input:
                    print(f"   📊 Real input tokens in usage: {real_input}")
                    print(f"   📊 Context limit in usage: {usage.get('context_limit', 'N/A')}")
                    print(f"   📊 Context utilization: {usage.get('context_utilization', 'N/A')}")
                
            else:
                print(f"   ❌ FAILED: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Error: {response.text[:200]}")

if __name__ == "__main__":
    test_context_awareness()