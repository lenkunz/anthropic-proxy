#!/usr/bin/env python3
"""
Test upstream endpoints directly to compare token counts
This bypasses the proxy and tests z.ai's Anthropic vs OpenAI endpoints directly
"""

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

# Direct upstream endpoints
ANTHROPIC_UPSTREAM = "https://api.z.ai/api/anthropic"
OPENAI_UPSTREAM = "https://api.z.ai/api/coding/paas"  # Removed /v4

def test_anthropic_endpoint_direct(prompt, max_tokens=100):
    """Test Anthropic endpoint directly"""
    print("📤 Testing Anthropic endpoint directly...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Anthropic format
    payload = {
        "model": "glm-4.5",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        response = requests.post(f"{ANTHROPIC_UPSTREAM}/v1/messages", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Anthropic format might be different - let's see what we get
            print(f"✅ Anthropic direct response received")
            
            # Try to extract usage info
            usage = data.get("usage", {})
            if usage:
                print(f"   • Input tokens: {usage.get('input_tokens', 'N/A')}")
                print(f"   • Output tokens: {usage.get('output_tokens', 'N/A')}")
                
                # Calculate total for comparison
                total = (usage.get('input_tokens', 0) or 0) + (usage.get('output_tokens', 0) or 0)
                print(f"   • Total tokens: {total}")
                
                return {
                    "prompt_tokens": usage.get('input_tokens', 0),
                    "completion_tokens": usage.get('output_tokens', 0),
                    "total_tokens": total,
                    "content": data.get("content", [{}])[0].get("text", "") if data.get("content") else ""
                }
            else:
                print(f"   • Raw response: {json.dumps(data, indent=2)}")
                return None
                
        else:
            print(f"❌ Anthropic direct failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Anthropic direct error: {str(e)}")
        return None

def test_openai_endpoint_direct(prompt, max_tokens=100):
    """Test OpenAI endpoint directly"""
    print("📤 Testing OpenAI endpoint directly...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # OpenAI format
    payload = {
        "model": "glm-4.5v",  # Use vision model for OpenAI endpoint
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        response = requests.post(f"{OPENAI_UPSTREAM}/v1/chat/completions", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            print(f"✅ OpenAI direct response received")
            print(f"   • Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"   • Completion tokens: {usage.get('completion_tokens', 'N/A')}")  
            print(f"   • Total tokens: {usage.get('total_tokens', 'N/A')}")
            
            return {
                "prompt_tokens": usage.get('prompt_tokens', 0),
                "completion_tokens": usage.get('completion_tokens', 0),
                "total_tokens": usage.get('total_tokens', 0),
                "content": content
            }
            
        else:
            print(f"❌ OpenAI direct failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ OpenAI direct error: {str(e)}")
        return None

def compare_endpoints_direct(test_name, prompt, max_tokens=100):
    """Compare both upstream endpoints directly"""
    
    print(f"\n🧪 Test: {test_name}")
    print("=" * 60)
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"Max tokens: {max_tokens}")
    
    # Test both endpoints
    anthropic_result = test_anthropic_endpoint_direct(prompt, max_tokens)
    time.sleep(1)  # Brief pause
    openai_result = test_openai_endpoint_direct(prompt, max_tokens)
    
    # Compare results
    if anthropic_result and openai_result:
        print(f"\n📊 Direct Endpoint Comparison:")
        print(f"{'Metric':<18} | {'Anthropic':<12} | {'OpenAI':<12} | {'Ratio'}")
        print("-" * 65)
        
        metrics = ["prompt_tokens", "completion_tokens", "total_tokens"]
        for metric in metrics:
            anthro_val = anthropic_result.get(metric, 0)
            openai_val = openai_result.get(metric, 0)
            
            if openai_val > 0:
                ratio = anthro_val / openai_val
                ratio_str = f"{ratio:.3f}"
            else:
                ratio_str = "N/A"
            
            print(f"{metric:<18} | {anthro_val:<12} | {openai_val:<12} | {ratio_str}")
        
        # Content comparison
        anthro_content = anthropic_result.get("content", "")
        openai_content = openai_result.get("content", "")
        
        print(f"\n📝 Response Content Comparison:")
        print(f"   Anthropic: {anthro_content[:100]}...")
        print(f"   OpenAI:    {openai_content[:100]}...")
        
        content_similar = anthro_content.strip()[:50] == openai_content.strip()[:50]
        print(f"   Similar content: {'✅ Yes' if content_similar else '❌ No'}")
        
        return {
            "anthropic": anthropic_result,
            "openai": openai_result
        }
    
    return None

def main():
    print("🧪 Direct Upstream Endpoint Comparison")
    print("Testing z.ai's Anthropic vs OpenAI endpoints directly (bypassing proxy)")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "Simple Question",
            "prompt": "What is the capital of France?",
            "max_tokens": 50
        },
        {
            "name": "Technical Question",
            "prompt": "Explain the difference between REST and GraphQL APIs.",
            "max_tokens": 200
        },
        {
            "name": "Longer Context",
            "prompt": "Write a comprehensive analysis of the benefits and challenges of microservices architecture compared to monolithic architecture. Include specific examples.",
            "max_tokens": 400
        }
    ]
    
    all_results = {}
    
    for test_case in test_cases:
        result = compare_endpoints_direct(
            test_case["name"],
            test_case["prompt"],
            test_case["max_tokens"]
        )
        
        if result:
            all_results[test_case["name"]] = result
        
        time.sleep(2)  # Longer pause between test cases
    
    # Overall analysis
    print(f"\n📋 OVERALL ANALYSIS")
    print("=" * 80)
    
    if all_results:
        print("🔍 Key Findings:")
        
        # Calculate average ratios
        total_token_ratios = []
        prompt_token_ratios = []
        
        for test_name, result in all_results.items():
            anthro = result["anthropic"]
            openai = result["openai"]
            
            if anthro["total_tokens"] > 0 and openai["total_tokens"] > 0:
                total_ratio = anthro["total_tokens"] / openai["total_tokens"]
                total_token_ratios.append(total_ratio)
            
            if anthro["prompt_tokens"] > 0 and openai["prompt_tokens"] > 0:
                prompt_ratio = anthro["prompt_tokens"] / openai["prompt_tokens"]
                prompt_token_ratios.append(prompt_ratio)
        
        if total_token_ratios:
            avg_total_ratio = sum(total_token_ratios) / len(total_token_ratios)
            print(f"   • Average total token ratio (Anthropic/OpenAI): {avg_total_ratio:.3f}")
        
        if prompt_token_ratios:
            avg_prompt_ratio = sum(prompt_token_ratios) / len(prompt_token_ratios)
            print(f"   • Average prompt token ratio (Anthropic/OpenAI): {avg_prompt_ratio:.3f}")
        
        print(f"\n💡 Implications:")
        print(f"   • If ratios ≈ 1.0: Endpoints count tokens similarly")
        print(f"   • If ratios ≠ 1.0: Endpoints use different tokenization/counting")
        print(f"   • Prompt token differences indicate input processing differences")
        print(f"   • Total token differences indicate response generation differences")
        
        # Expected scaling insights
        print(f"\n🔧 Scaling Insights:")
        print(f"   • Your proxy applies scaling to normalize token counts")
        print(f"   • Anthropic context: 200k tokens (expected)")
        print(f"   • OpenAI context: 131k tokens (expected)")
        print(f"   • Scaling factor: {128000/200000:.3f} (OpenAI/Anthropic)")
        
        if total_token_ratios:
            expected_inverse_scaling = 200000 / 128000  # ~1.5625
            actual_avg = avg_total_ratio
            print(f"   • Expected ratio without scaling: {expected_inverse_scaling:.3f}")
            print(f"   • Actual measured ratio: {actual_avg:.3f}")
    
    else:
        print("❌ No successful tests completed")

if __name__ == "__main__":
    main()