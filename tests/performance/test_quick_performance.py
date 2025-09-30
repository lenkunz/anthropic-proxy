#!/usr/bin/env python3
"""
Quick performance test for GLM-4.6 - focuses on response times and throughput
"""

import json
import os
import time
import urllib.request
from dotenv import load_dotenv
import tiktoken

load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
MODEL_NAME = "glm-4.6"

def quick_test(token_target: int, description: str):
    """Quick performance test for a specific token size using tiktoken"""
    # Use tiktoken for accurate token counting
    encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
    
    base_sentence = "AI and machine learning continue to evolve rapidly. "
    content = base_sentence
    while len(encoding.encode(content)) < token_target:
        content += base_sentence
    
    # Trim to exact token count
    tokens = encoding.encode(content)
    if len(tokens) > token_target:
        tokens = tokens[:token_target]
        content = encoding.decode(tokens)
    
    print(f"📊 Generated content: {len(encoding.encode(content))} tokens (target: {token_target})")
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": content + "\n\nBrief summary please."}],
        "max_tokens": 30,
        "temperature": 0.1
    }
    
    start_time = time.time()
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{OPENAI_BASE_URL}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            response_time = time.time() - start_time
            
            if response.getcode() == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                usage = response_data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                
                print(f"✅ {description}: {response_time:.2f}s ({prompt_tokens:,} tokens)")
                return response_time, prompt_tokens, True
            else:
                print(f"❌ {description}: HTTP {response.getcode()}")
                return response_time, 0, False
                
    except Exception as e:
        response_time = time.time() - start_time
        print(f"💥 {description}: {str(e)[:50]}... ({response_time:.2f}s)")
        return response_time, 0, False

def main():
    print("⚡ QUICK GLM-4.6 PERFORMANCE TEST")
    print(f"📡 {OPENAI_BASE_URL}")
    print("="*50)
    
    # Test different sizes
    test_cases = [
        (1000, "Small (1K tokens)"),
        (10000, "Medium (10K tokens)"),
        (50000, "Large (50K tokens)"),
        (100000, "Very Large (100K tokens)"),
        (200000, "Maximum (200K tokens)")
    ]
    
    results = []
    for token_size, description in test_cases:
        print(f"\n🧪 {description}...")
        response_time, prompt_tokens, success = quick_test(token_size, description)
        results.append((description, response_time, prompt_tokens, success))
        time.sleep(2)  # Rate limiting
    
    print(f"\n📊 PERFORMANCE SUMMARY:")
    print("="*50)
    for desc, time_taken, tokens, success in results:
        if success:
            tokens_per_sec = tokens / time_taken if time_taken > 0 else 0
            print(f"{desc:20} | {time_taken:6.2f}s | {tokens:7,} tokens | {tokens_per_sec:6.0f} tok/s")
        else:
            print(f"{desc:20} | {time_taken:6.2f}s | FAILED")

if __name__ == "__main__":
    main()