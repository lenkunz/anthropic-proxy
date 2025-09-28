#!/usr/bin/env python3
"""
Test if the same prompt returns the same token count usage on both endpoints
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import requests
import json
import time
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

def test_endpoint_consistency(test_name, prompt, max_tokens=100):
    """Test if same prompt gives consistent token counts across endpoints"""
    
    print(f"\n🧪 Test: {test_name}")
    print("-" * 50)
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    models_to_test = [
        ("glm-4.5-anthropic", "Anthropic endpoint"),
        ("glm-4.5-openai", "OpenAI endpoint")
    ]
    
    results = {}
    
    for model, description in models_to_test:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.0  # Deterministic responses
        }
        
        try:
            print(f"📤 Testing {description} ({model})...")
            response = requests.post(f"{BASE_URL}/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                usage = data.get("usage", {})
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                results[model] = {
                    "usage": usage,
                    "content": content,
                    "description": description
                }
                
                print(f"✅ Success")
                print(f"   • Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
                print(f"   • Completion tokens: {usage.get('completion_tokens', 'N/A')}")  
                print(f"   • Total tokens: {usage.get('total_tokens', 'N/A')}")
                
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            
        time.sleep(0.5)  # Brief pause between requests
    
    # Compare results
    if len(results) == 2:
        anthropic_key = "glm-4.5-anthropic"
        openai_key = "glm-4.5-openai"
        
        if anthropic_key in results and openai_key in results:
            anthro_usage = results[anthropic_key]["usage"]
            openai_usage = results[openai_key]["usage"]
            
            print(f"\n📊 Endpoint Comparison:")
            print(f"{'Metric':<18} | {'Anthropic':<10} | {'OpenAI':<10} | {'Same?'}")
            print("-" * 55)
            
            for metric in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                anthro_val = anthro_usage.get(metric, 0)
                openai_val = openai_usage.get(metric, 0)
                same = "✅ Yes" if anthro_val == openai_val else "❌ No"
                
                print(f"{metric:<18} | {anthro_val:<10} | {openai_val:<10} | {same}")
            
            # Compare response content
            anthro_content = results[anthropic_key]["content"]
            openai_content = results[openai_key]["content"]
            content_same = anthro_content.strip() == openai_content.strip()
            
            print(f"\n📝 Response Content:")
            print(f"   Same content: {'✅ Yes' if content_same else '❌ No'}")
            
            if not content_same:
                print(f"   Anthropic: {anthro_content[:100]}...")
                print(f"   OpenAI:    {openai_content[:100]}...")
    
    return results

def main():
    print("🧪 Endpoint Consistency Test")
    print("Testing if same prompts return same token counts across endpoints")
    print("=" * 70)
    
    # Test cases with different characteristics
    test_cases = [
        {
            "name": "Simple Question",
            "prompt": "What is the capital of France?",
            "max_tokens": 50
        },
        {
            "name": "Medium Complexity",
            "prompt": "Explain the concept of machine learning in simple terms, including supervised and unsupervised learning.",
            "max_tokens": 200
        },
        {
            "name": "Technical Question", 
            "prompt": "How does a REST API differ from a GraphQL API? Please provide specific examples of when to use each approach.",
            "max_tokens": 300
        },
        {
            "name": "Large Context",
            "prompt": """Analyze the following scenario: A company is migrating from a monolithic architecture to microservices. 
            They have a large e-commerce platform with user management, inventory, payment processing, and order fulfillment.
            What would be the key considerations, potential challenges, and recommended strategies for this migration?
            Please provide a detailed breakdown including technical, organizational, and operational aspects.""",
            "max_tokens": 500
        }
    ]
    
    all_results = {}
    
    for test_case in test_cases:
        results = test_endpoint_consistency(
            test_case["name"],
            test_case["prompt"], 
            test_case["max_tokens"]
        )
        all_results[test_case["name"]] = results
        time.sleep(1)  # Pause between test cases
    
    # Summary analysis
    print(f"\n📋 OVERALL SUMMARY")
    print("=" * 70)
    
    consistent_counts = 0
    total_tests = 0
    
    for test_name, results in all_results.items():
        if len(results) == 2:
            total_tests += 1
            anthro_usage = results["glm-4.5-anthropic"]["usage"]
            openai_usage = results["glm-4.5-openai"]["usage"]
            
            # Check if token counts match
            prompt_match = anthro_usage.get("prompt_tokens") == openai_usage.get("prompt_tokens")
            total_match = anthro_usage.get("total_tokens") == openai_usage.get("total_tokens")
            
            if prompt_match and total_match:
                consistent_counts += 1
                status = "✅ Consistent"
            else:
                status = "❌ Different"
                
            print(f"{test_name:<20} | {status}")
    
    print(f"\n🎯 Results: {consistent_counts}/{total_tests} tests showed consistent token counts")
    
    if consistent_counts == total_tests:
        print("✅ All tests consistent - endpoints return same token counts for same prompts")
    elif consistent_counts == 0:
        print("❌ No tests consistent - endpoints return different token counts")
    else:
        print("❓ Mixed results - some prompts consistent, others different")
    
    print("\n💡 Key Insights:")
    print("   • If token counts are the same: Both endpoints likely hit same upstream")
    print("   • If token counts differ: Different upstreams or different counting methods")
    print("   • Prompt tokens should be consistent (same input processing)")
    print("   • Completion tokens might differ (different model responses)")

if __name__ == "__main__":
    main()