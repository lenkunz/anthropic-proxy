#!/usr/bin/env python3
"""
Test high-token scenarios to verify scaling behavior with ~100k tokens
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

def generate_large_content(target_tokens_approx=100000):
    """Generate content that should result in approximately 100k tokens"""
    # Rough estimate: 1 token ≈ 4 characters for English text
    # So ~100k tokens ≈ 400k characters
    
    # Create varied, realistic content to avoid compression/deduplication
    content_blocks = [
        "In the rapidly evolving landscape of artificial intelligence, researchers are continuously pushing the boundaries of what's possible with machine learning algorithms and neural network architectures. ",
        "The intersection of quantum computing and artificial intelligence represents one of the most promising frontiers in computational science, with potential applications spanning from cryptography to drug discovery. ",
        "Large language models have demonstrated remarkable capabilities in natural language understanding and generation, transforming how we interact with technology and process information. ",
        "The ethical implications of AI development require careful consideration of bias, fairness, transparency, and accountability in algorithmic decision-making systems. ",
        "Distributed computing paradigms enable the training of increasingly complex models across vast datasets, leveraging cloud infrastructure and specialized hardware accelerators. "
    ]
    
    # Repeat and combine blocks to reach target size
    target_chars = target_tokens_approx * 4  # Rough estimate
    result = ""
    block_index = 0
    
    while len(result) < target_chars:
        result += f"[Section {len(result)//1000}] " + content_blocks[block_index % len(content_blocks)]
        result += f"This section contains detailed analysis of topic #{block_index}, including comprehensive examples, case studies, and technical specifications that demonstrate the complexity and depth of modern computational systems. "
        block_index += 1
    
    return result

def test_model_with_large_content(model_name, content):
    """Test a specific model with large content"""
    print(f"\n📤 Testing {model_name} with large content...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user", 
                "content": content + "\n\nPlease provide a comprehensive summary of the key themes and concepts discussed in the above text."
            }
        ],
        "max_tokens": 500,  # Limit response to focus on prompt tokens
        "temperature": 0.1
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/v1/chat/completions", headers=headers, json=payload)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            
            print(f"✅ {model_name} response received ({end_time - start_time:.2f}s)")
            print(f"   • Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
            print(f"   • Completion tokens: {usage.get('completion_tokens', 'N/A')}")
            print(f"   • Total tokens: {usage.get('total_tokens', 'N/A')}")
            
            return usage
        else:
            print(f"❌ {model_name} failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ {model_name} error: {str(e)}")
        return None

def main():
    print("🧪 High Token Scaling Test")
    print("=" * 60)
    
    # Generate large content
    print("📝 Generating large content (~100k tokens)...")
    large_content = generate_large_content(100000)
    content_chars = len(large_content)
    estimated_tokens = content_chars // 4
    
    print(f"   • Content length: {content_chars:,} characters")
    print(f"   • Estimated tokens: ~{estimated_tokens:,}")
    
    # Test all model variants
    models_to_test = [
        "glm-4.5",           # Auto-routing
        "glm-4.5-anthropic", # Force Anthropic
        "glm-4.5-openai"     # Force OpenAI
    ]
    
    results = {}
    
    for model in models_to_test:
        usage = test_model_with_large_content(model, large_content)
        if usage:
            results[model] = usage
        time.sleep(1)  # Brief pause between requests
    
    # Analysis
    print("\n📊 HIGH TOKEN SCALING ANALYSIS")
    print("=" * 60)
    
    if len(results) >= 2:
        for model, usage in results.items():
            total = usage.get('total_tokens', 0)
            print(f"{model:<20} | {total:>8,} tokens")
        
        # Compare anthropic vs openai if both available
        if "glm-4.5-anthropic" in results and "glm-4.5-openai" in results:
            anthropic_tokens = results["glm-4.5-anthropic"].get("total_tokens", 0)
            openai_tokens = results["glm-4.5-openai"].get("total_tokens", 0)
            
            print(f"\n🔍 Endpoint Comparison:")
            print(f"   Anthropic endpoint: {anthropic_tokens:,} tokens")
            print(f"   OpenAI endpoint:    {openai_tokens:,} tokens")
            
            if anthropic_tokens > 0 and openai_tokens > 0:
                ratio = anthropic_tokens / openai_tokens
                print(f"   Ratio (A/O):        {ratio:.3f}")
                
                # Expected scaling factor
                expected_factor = 200000 / 128000  # ~1.5625 for Anthropic to show higher
                print(f"   Expected ratio:     {expected_factor:.3f}")
                
                if abs(ratio - expected_factor) < 0.1:
                    print("   ✅ Ratio matches expected scaling!")
                else:
                    print("   ❓ Ratio differs from expected scaling")
        
        # Check if scaling is being applied for anthropic
        if "glm-4.5-anthropic" in results:
            anthropic_total = results["glm-4.5-anthropic"].get("total_tokens", 0)
            # If scaling were NOT applied, we'd expect much higher numbers
            # If scaling IS applied, we'd expect reasonable numbers
            
            print(f"\n🧮 Scaling Analysis for glm-4.5-anthropic:")
            print(f"   Reported tokens: {anthropic_total:,}")
            print(f"   If no scaling:   Would show raw Anthropic counts")
            print(f"   If scaling:      Shows scaled-down counts")
            
            # Very rough heuristic - if we're seeing reasonable numbers relative to content,
            # scaling is probably working
            if anthropic_total < estimated_tokens * 2:
                print("   ✅ Token count seems reasonable - scaling likely working")
            else:
                print("   ❓ Token count seems high - scaling might not be working")
    
    print("\n" + "=" * 60)
    print("🎯 High token test completed")

if __name__ == "__main__":
    main()