#!/usr/bin/env python3
"""
Binary search test to find the actual context window size for glm-4.6
by testing directly on the OpenAI endpoint until we hit the context limit.
"""

import json
import os
import time
import httpx
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import tiktoken

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

# Test directly against OpenAI endpoint
OPENAI_BASE_URL = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
MODEL_NAME = "glm-4.6"

print(f"🔍 Binary Search Context Window Test for {MODEL_NAME}")
print(f"📡 Testing endpoint: {OPENAI_BASE_URL}")
print(f"🎯 Starting from: 65,536 tokens")
print("="*60)

def generate_text_content(target_tokens: int) -> str:
    """Generate text content targeting exactly N tokens using tiktoken"""
    # Use tiktoken for accurate token counting
    encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
    
    # Create repetitive but valid text content
    base_text = (
        "This is a comprehensive analysis of machine learning algorithms and their applications "
        "in modern artificial intelligence systems. We explore various methodologies including "
        "supervised learning, unsupervised learning, reinforcement learning, and deep learning. "
        "Each approach has distinct characteristics, advantages, and use cases in different domains. "
    )
    
    # Start with base text and keep adding until we reach target token count
    content = base_text
    while len(encoding.encode(content)) < target_tokens:
        content += base_text
    
    # Trim to exact token count
    tokens = encoding.encode(content)
    if len(tokens) > target_tokens:
        tokens = tokens[:target_tokens]
        content = encoding.decode(tokens)
    
    print(f"📊 Generated content: {len(encoding.encode(content))} tokens (target: {target_tokens})")
    return content

async def test_context_size(token_count: int) -> tuple[bool, Optional[str], Optional[Dict[Any, Any]]]:
    """
    Test if the model can handle the given token count.
    Returns: (success, error_message, response_data)
    """
    print(f"🧪 Testing {token_count:,} tokens...", end=" ", flush=True)
    
    content = generate_text_content(token_count)
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": content + "\n\nPlease provide a brief summary of the above text."
            }
        ],
        "max_tokens": 100,  # Keep response small
        "temperature": 0.1
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS")
                return True, None, data
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {"error": response.text}
                error_msg = str(error_data.get("error", {}).get("message", error_data.get("error", response.text)))
                print(f"❌ FAILED - {error_msg[:100]}...")
                return False, error_msg, error_data
                
    except Exception as e:
        error_msg = str(e)
        print(f"💥 ERROR - {error_msg[:100]}...")
        return False, error_msg, None

async def binary_search_context_window(start_tokens: int = 65536, max_tokens: int = 1000000) -> int:
    """
    Binary search to find the maximum context window size.
    """
    print(f"🚀 Starting binary search between {start_tokens:,} and {max_tokens:,} tokens")
    print("-" * 60)
    
    # First, test if the starting point works
    success, error_msg, _ = await test_context_size(start_tokens)
    if not success:
        print(f"⚠️  Starting point {start_tokens:,} failed: {error_msg}")
        # Find a working starting point by dividing by 2
        while start_tokens > 1000 and not success:
            start_tokens //= 2
            success, error_msg, _ = await test_context_size(start_tokens)
        
        if not success:
            print("❌ Could not find a working starting point!")
            return 0
        
        print(f"✅ Found working starting point: {start_tokens:,} tokens")
    
    # Now binary search for the maximum
    low = start_tokens
    high = max_tokens
    last_successful = start_tokens
    
    iteration = 0
    while low <= high and iteration < 20:  # Max 20 iterations to prevent infinite loops
        iteration += 1
        mid = (low + high) // 2
        
        print(f"\n🔄 Iteration {iteration}: Testing {mid:,} tokens (range: {low:,} - {high:,})")
        
        success, error_msg, response_data = await test_context_size(mid)
        
        if success:
            last_successful = mid
            low = mid + 1
            if response_data and "usage" in response_data:
                usage = response_data["usage"]
                print(f"   💡 Token usage: {usage.get('prompt_tokens', 'N/A')} prompt + {usage.get('completion_tokens', 'N/A')} completion = {usage.get('total_tokens', 'N/A')} total")
        else:
            high = mid - 1
            # Print context limit error details
            if "context" in error_msg.lower() or "token" in error_msg.lower() or "limit" in error_msg.lower():
                print(f"   🎯 Context limit error detected: {error_msg[:200]}")
        
        # Wait a bit between requests to be respectful
        await asyncio.sleep(1)
    
    return last_successful

async def main():
    """Main test execution"""
    try:
        # Test basic connectivity first
        print("🔗 Testing basic connectivity...")
        basic_success, basic_error, _ = await test_context_size(1000)  # Small test
        if not basic_success:
            print(f"❌ Basic connectivity failed: {basic_error}")
            return
        
        print("\n" + "="*60)
        print("🔍 BINARY SEARCH FOR MAXIMUM CONTEXT WINDOW")
        print("="*60)
        
        # Start binary search
        max_context = await binary_search_context_window()
        
        print("\n" + "="*60)
        print("📊 FINAL RESULTS")
        print("="*60)
        print(f"🎯 Model: {MODEL_NAME}")
        print(f"📡 Endpoint: {OPENAI_BASE_URL}")
        print(f"📏 Maximum Context Window: {max_context:,} tokens")
        
        # Test a few values around the maximum for confirmation
        print(f"\n🔬 Confirmation tests around {max_context:,} tokens:")
        for offset in [-1000, -500, 0, +500, +1000]:
            test_size = max_context + offset
            if test_size > 0:
                success, error, _ = await test_context_size(test_size)
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"   {test_size:,} tokens: {status}")
                await asyncio.sleep(0.5)
        
        print(f"\n🎉 Context window discovery complete!")
        print(f"💡 Recommended REAL_TEXT_MODEL_TOKENS setting: {max_context}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())