#!/usr/bin/env python3
"""
Debug token scaling with forced high token counts
"""

import requests
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"

def test_with_long_content():
    """Test with very long content to trigger higher token counts"""
    print("🧪 Testing Token Scaling with Long Content")
    print("=" * 60)
    
    # Create a very long message to get higher token counts
    long_message = """
    Please write a comprehensive analysis of artificial intelligence, machine learning, and deep learning technologies. 
    Include discussions of neural networks, natural language processing, computer vision, reinforcement learning, 
    transformer architectures, attention mechanisms, convolutional neural networks, recurrent neural networks,
    generative adversarial networks, variational autoencoders, and their applications in various domains such as
    healthcare, finance, autonomous vehicles, robotics, and scientific research. Also discuss the ethical implications,
    bias concerns, fairness, transparency, explainability, and the future of AI development including AGI considerations.
    """ * 50  # Repeat to get a very long message
    
    print(f"📏 Message length: {len(long_message)} characters")
    
    # Test each model variant
    models = ["glm-4.5", "glm-4.5-anthropic", "glm-4.5-openai"]
    results = {}
    
    for model in models:
        print(f"\n📤 Testing {model}...")
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": long_message}],
                "max_tokens": 100,  # Keep completion short
                "stream": False
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            
            results[model] = {
                "prompt_tokens": usage.get('prompt_tokens'),
                "completion_tokens": usage.get('completion_tokens'),
                "total_tokens": usage.get('total_tokens')
            }
            
            print(f"✅ {model}: {usage.get('total_tokens')} total tokens")
        else:
            print(f"❌ {model} failed: {response.status_code}")
            results[model] = {"error": response.text}
    
    # Analyze results
    print(f"\n📊 TOKEN SCALING ANALYSIS")
    print("=" * 60)
    
    for model, result in results.items():
        if "error" not in result:
            total = result["total_tokens"]
            print(f"{model:<20} | {total:>8} tokens")
            
            if model == "glm-4.5-anthropic":
                print(f"{'':20} | Expected: ~{total*0.656:.0f} if scaling from 200k→131k")
                if total > 100000:  # High enough to see scaling effects
                    if total > 180000:
                        print(f"{'':20} | 🔴 BUG: No scaling applied (showing ~200k values)")
                    elif total < 140000:
                        print(f"{'':20} | 🟢 OK: Scaling applied correctly")
    
    return results

def main():
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print(f"❌ Proxy not responding")
            return
    except Exception as e:
        print(f"❌ Cannot connect to proxy: {e}")
        return
    
    test_with_long_content()

if __name__ == "__main__":
    main()