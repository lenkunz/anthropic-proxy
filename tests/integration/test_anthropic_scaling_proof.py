#!/usr/bin/env python3
"""
Test to prove Anthropic endpoint token scaling behavior
This test will show:
1. What raw token counts the Anthropic endpoint returns
2. How your proxy scales those tokens
3. The scaling factor applied
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"  # Your proxy
ANTHROPIC_DIRECT = "https://api.z.ai/api/anthropic"  # Direct upstream

def test_anthropic_direct(prompt, description):
    """Test Anthropic endpoint directly to get raw token counts"""
    print(f"\n🔍 Direct Anthropic Test: {description}")
    print("-" * 50)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.5",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(f"{ANTHROPIC_DIRECT}/v1/messages", headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            total_tokens = input_tokens + output_tokens
            
            print(f"✅ RAW Anthropic tokens:")
            print(f"   • Input tokens:  {input_tokens}")
            print(f"   • Output tokens: {output_tokens}")
            print(f"   • Total tokens:  {total_tokens}")
            
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens, 
                "total_tokens": total_tokens,
                "raw_usage": usage
            }
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_proxy_anthropic(prompt, description, model="glm-4.5-anthropic"):
    """Test your proxy with glm-4.5-anthropic to see scaled tokens"""
    print(f"\n🔍 Proxy {model} Test: {description}")
    print("-" * 50)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "max_tokens": 100,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)
            
            print(f"✅ SCALED proxy tokens:")
            print(f"   • Prompt tokens:     {prompt_tokens}")
            print(f"   • Completion tokens: {completion_tokens}")
            print(f"   • Total tokens:      {total_tokens}")
            
            return {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "raw_usage": usage
            }
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def analyze_scaling(direct_result, proxy_result, test_name):
    """Analyze the scaling between direct and proxy results"""
    
    if not direct_result or not proxy_result:
        print(f"❌ Cannot analyze {test_name} - missing data")
        return
    
    print(f"\n📊 SCALING ANALYSIS: {test_name}")
    print("=" * 60)
    
    # Compare input/prompt tokens
    direct_input = direct_result['input_tokens']
    proxy_prompt = proxy_result['prompt_tokens']
    
    print(f"📥 INPUT/PROMPT TOKENS:")
    print(f"   Direct Anthropic:  {direct_input}")
    print(f"   Proxy (scaled):    {proxy_prompt}")
    
    if direct_input > 0:
        input_scaling_factor = proxy_prompt / direct_input
        print(f"   Scaling factor:    {input_scaling_factor:.6f}")
        print(f"   Percentage:        {input_scaling_factor * 100:.2f}%")
    else:
        print(f"   Scaling factor:    N/A (zero input)")
    
    # Compare output/completion tokens  
    direct_output = direct_result['output_tokens']
    proxy_completion = proxy_result['completion_tokens']
    
    print(f"\n📤 OUTPUT/COMPLETION TOKENS:")
    print(f"   Direct Anthropic:  {direct_output}")
    print(f"   Proxy (scaled):    {proxy_completion}")
    
    if direct_output > 0:
        output_scaling_factor = proxy_completion / direct_output
        print(f"   Scaling factor:    {output_scaling_factor:.6f}")
        print(f"   Percentage:        {output_scaling_factor * 100:.2f}%")
    else:
        print(f"   Scaling factor:    N/A (zero output)")
    
    # Compare total tokens
    direct_total = direct_result['total_tokens']
    proxy_total = proxy_result['total_tokens']
    
    print(f"\n🔢 TOTAL TOKENS:")
    print(f"   Direct Anthropic:  {direct_total}")
    print(f"   Proxy (scaled):    {proxy_total}")
    
    if direct_total > 0:
        total_scaling_factor = proxy_total / direct_total
        print(f"   Scaling factor:    {total_scaling_factor:.6f}")
        print(f"   Percentage:        {total_scaling_factor * 100:.2f}%")
        
        # Calculate theoretical scaling
        theoretical_factor = 128000 / 200000  # OpenAI 128k / Anthropic 200k
        print(f"\n🧮 THEORETICAL SCALING:")
        print(f"   Expected factor:   {theoretical_factor:.6f} (131k/200k)")
        print(f"   Expected %:        {theoretical_factor * 100:.2f}%")
        print(f"   Actual factor:     {total_scaling_factor:.6f}")
        print(f"   Difference:        {abs(total_scaling_factor - theoretical_factor):.6f}")
        
        if abs(total_scaling_factor - theoretical_factor) < 0.01:
            print(f"   ✅ MATCHES expected scaling!")
        else:
            print(f"   ❓ DIFFERS from expected scaling")
    else:
        print(f"   Scaling factor:    N/A (zero total)")

def main():
    print("🧪 Anthropic Token Scaling Proof Test")
    print("=" * 70)
    print("This test will show:")
    print("1. Raw token counts from Anthropic endpoint")
    print("2. Scaled token counts from your proxy")  
    print("3. The exact scaling factor applied")
    print("4. Whether it matches the expected 131k/200k ratio")
    
    test_cases = [
        {
            "prompt": "What is 2+2?",
            "description": "Simple Math Question"
        },
        {
            "prompt": "Explain quantum computing in one paragraph.",
            "description": "Medium Complexity"
        },
        {
            "prompt": "Write a detailed analysis of the pros and cons of microservices architecture versus monolithic architecture, including specific examples of when to use each approach, common pitfalls to avoid, and best practices for implementation.",
            "description": "Complex Request"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"🧪 TEST {i}/3: {test_case['description']}")
        print(f"{'='*70}")
        print(f"Prompt: {test_case['prompt'][:100]}{'...' if len(test_case['prompt']) > 100 else ''}")
        
        # Test direct Anthropic
        direct_result = test_anthropic_direct(test_case['prompt'], test_case['description'])
        
        # Test proxy with glm-4.5-anthropic
        proxy_result = test_proxy_anthropic(test_case['prompt'], test_case['description'], "glm-4.5-anthropic")
        
        # Analyze scaling
        analyze_scaling(direct_result, proxy_result, test_case['description'])
        
        print(f"\n{'='*70}")
    
    print(f"\n🎯 FINAL CONCLUSIONS:")
    print("If scaling is working correctly, you should see:")
    print("• Proxy tokens are ~65.54% of direct Anthropic tokens")
    print("• Scaling factor around 0.65536 (131072/200000)")
    print("• This proves Anthropic scales from ~200k context to ~131k context")

if __name__ == "__main__":
    main()