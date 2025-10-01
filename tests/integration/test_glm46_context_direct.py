#!/usr/bin/env python3
"""
Direct OpenAI endpoint test for glm-4.6 context window discovery.
Uses binary search starting from 65,536 tokens to find the actual limit.
"""

import json
import os
import time
import urllib.request
import urllib.parse
from dotenv import load_dotenv
import tiktoken

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

# Direct OpenAI endpoint (bypassing proxy)
OPENAI_BASE_URL = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
MODEL_NAME = "glm-4.6"

def create_large_content(target_tokens: int) -> str:
    """Create content targeting exactly N tokens using tiktoken"""
    # Use tiktoken for accurate token counting
    encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
    
    # Create structured, meaningful content
    sections = [
        "# Machine Learning Fundamentals",
        "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
        
        "## Supervised Learning",
        "Supervised learning algorithms learn from labeled training data to make predictions or decisions. Common examples include classification and regression tasks.",
        
        "## Unsupervised Learning",
        "Unsupervised learning finds hidden patterns in data without labeled examples. Clustering and dimensionality reduction are key applications.",
        
        "## Deep Learning",
        "Deep learning uses neural networks with multiple layers to model complex patterns. It has revolutionized computer vision, natural language processing, and many other fields.",
        
        "## Applications",
        "Modern machine learning applications span healthcare, finance, autonomous vehicles, recommendation systems, and scientific research.",
    ]
    
    base_content = "\n\n".join(sections)
    
    # Start with base content and keep adding until we reach target token count
    content = base_content
    while len(encoding.encode(content)) < target_tokens:
        content += "\n\n" + base_content
    
    # Trim to exact token count
    tokens = encoding.encode(content)
    if len(tokens) > target_tokens:
        tokens = tokens[:target_tokens]
        content = encoding.decode(tokens)
    
    print(f"📊 Generated content: {len(encoding.encode(content))} tokens (target: {target_tokens})")
    return content

def test_token_count(token_target: int) -> tuple[bool, str, dict]:
    """
    Test the model with exactly N tokens of input.
    Returns: (success, error_message, response_data)
    """
    print(f"🧪 Testing {token_target:,} tokens... ", end="", flush=True)
    
    content = create_large_content(token_target)
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful assistant that provides concise summaries."
            },
            {
                "role": "user",
                "content": content + "\n\nPlease provide a brief 2-sentence summary of the key points above."
            }
        ],
        "max_tokens": 20,  # Keep response very minimal to avoid timeout
        "temperature": 0.1,
        "thinking": {"type": "enabled"}  # Enable z.ai thinking mode
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"{OPENAI_BASE_URL}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "anthropic-proxy-context-test"
            }
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            if response.getcode() == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                print("✅ SUCCESS")
                
                # Print token usage if available
                if "usage" in response_data:
                    usage = response_data["usage"]
                    prompt_tokens = usage.get("prompt_tokens", "?")
                    total_tokens = usage.get("total_tokens", "?")
                    print(json.dumps(response_data, indent=2))
                    print(f"   📊 Actual usage: {prompt_tokens} prompt tokens, {total_tokens} total")
                
                return True, "", response_data
            else:
                print(f"❌ HTTP {response.getcode()}")
                return False, f"HTTP {response.getcode()}", {}
                
    except urllib.error.HTTPError as e:
        error_data = {}
        try:
            error_response = json.loads(e.read().decode('utf-8'))
            error_message = error_response.get("error", {}).get("message", str(e))
            error_data = error_response
        except:
            error_message = str(e)
        
        print(f"❌ {e.code} - {error_message[:100]}...")
        return False, error_message, error_data
        
    except Exception as e:
        error_message = str(e)
        print(f"💥 {error_message[:100]}...")
        return False, error_message, {}

def binary_search_max_tokens(start: int = 65536, max_limit: int = 500000) -> int:
    """Binary search to find maximum token capacity"""
    
    print(f"🚀 Binary search starting from {start:,} tokens (max search: {max_limit:,})")
    print("="*70)
    
    # Verify starting point works
    success, error, _ = test_token_count(start)
    if not success:
        print(f"⚠️  Starting point {start:,} failed: {error}")
        # Try smaller starting points
        for test_start in [32768, 16384, 8192, 4096]:
            success, error, _ = test_token_count(test_start)
            if success:
                start = test_start
                print(f"✅ Found working start: {start:,} tokens")
                break
        else:
            print("❌ No working starting point found!")
            return 0
    
    # Binary search
    low = start
    high = max_limit
    max_successful = start
    iteration = 0
    
    print(f"\n🔍 Binary search range: {low:,} to {high:,} tokens")
    print("-" * 70)
    
    while low <= high and iteration < 25:  # Max 25 iterations
        iteration += 1
        mid = (low + high) // 2
        
        print(f"\n[{iteration:2d}] Range: {low:,} ≤ {mid:,} ≤ {high:,}")
        
        success, error_msg, response_data = test_token_count(mid)
        
        if success:
            max_successful = mid
            low = mid + 1
            print(f"     ✅ SUCCESS at {mid:,} tokens")
        else:
            high = mid - 1
            print(f"     ❌ FAILED at {mid:,} tokens")
            
            # Check if it's a context limit error
            if any(keyword in error_msg.lower() for keyword in ['context', 'token', 'limit', 'length', 'exceed']):
                print(f"     🎯 Context limit error: {error_msg[:150]}")
        
        # Rate limiting delay - increased to avoid overwhelming the server
        time.sleep(3.0)
    
    return max_successful

def main():
    """Main execution"""
    print("🔬 GLM-4.6 Context Window Discovery Tool")
    print(f"📡 Direct endpoint: {OPENAI_BASE_URL}")
    print(f"🤖 Model: {MODEL_NAME}")
    print("="*70)
    
    # Basic connectivity test
    print("🔗 Testing basic connectivity...")
    success, error, _ = test_token_count(1000)
    if not success:
        print(f"❌ Basic connectivity failed: {error}")
        return
    
    print("\n✅ Connectivity confirmed, starting context window discovery...")
    
    # Find maximum context window
    max_tokens = binary_search_max_tokens()
    
    print("\n" + "="*70)
    print("📊 RESULTS SUMMARY")
    print("="*70)
    print(f"🎯 Model: {MODEL_NAME}")
    print(f"📡 Endpoint: {OPENAI_BASE_URL}")
    print(f"📏 Maximum Context: {max_tokens:,} tokens")
    print(f"🔧 Current REAL_TEXT_MODEL_TOKENS: {os.getenv('REAL_TEXT_MODEL_TOKENS', 'Not set')}")
    
    if max_tokens > 0:
        print(f"\n💡 Recommended .env update:")
        print(f"    REAL_TEXT_MODEL_TOKENS={max_tokens}")
        print(f"    AUTOTEXT_MODEL=glm-4.6")
        
        # Final verification tests
        print(f"\n🔬 Verification tests around {max_tokens:,} tokens:")
        for delta in [-2000, -1000, 0, +1000, +2000]:
            test_val = max_tokens + delta
            if test_val > 0:
                success, _, _ = test_token_count(test_val)
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"   {test_val:,} tokens: {status}")
                time.sleep(1)
    
    print(f"\n🎉 Context window discovery complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        raise