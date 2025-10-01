#!/usr/bin/env python3
"""
Performance test for GLM-4.6 on the direct OpenAI endpoint.
Tests various context sizes, concurrent requests, and measures response times.
"""

import asyncio
import json
import os
import time
import statistics
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple
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

OPENAI_BASE_URL = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
MODEL_NAME = "glm-4.6"

class PerformanceTest:
    def __init__(self):
        self.results = []
        self.total_requests = 0
        self.total_errors = 0
    def generate_content(self, token_count: int) -> str:
        """Generate content targeting exactly N tokens using tiktoken"""
        # Use tiktoken for accurate token counting
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        
        base_text = (
            "In the realm of artificial intelligence and machine learning, we encounter "
            "various algorithms and methodologies that shape our understanding of computational "
            "intelligence. Neural networks, with their interconnected layers and weighted "
            "connections, form the backbone of deep learning systems. These systems excel "
            "at pattern recognition, natural language processing, and complex decision making. "
            "The training process involves forward propagation, backpropagation, and gradient "
            "descent optimization techniques that iteratively improve model performance. "
        )
        
        
        # Start with base text and keep adding until we reach target token count
        content = base_text
        while len(encoding.encode(content)) < token_count:
            content += base_text
        
        # Trim to exact token count
        tokens = encoding.encode(content)
        if len(tokens) > token_count:
            tokens = tokens[:token_count]
            content = encoding.decode(tokens)
        
        print(f"📊 Generated content: {len(encoding.encode(content))} tokens (target: {token_count})")
        return content
    
    def make_request(self, content: str, test_name: str) -> Dict[str, Any]:
        """Make a single request and measure performance"""
        start_time = time.time()
        
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": content + "\n\nPlease provide a brief summary (1-2 sentences)."
                }
            ],
            "max_tokens": 50,
            "temperature": 0.1,
            "thinking": {"type": "enabled"}
        }
        
        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{OPENAI_BASE_URL}/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "glm46-performance-test"
                }
            )
            
            with urllib.request.urlopen(req, timeout=120) as response:
                response_time = time.time() - start_time
                
                if response.getcode() == 200:
                    response_data = json.loads(response.read().decode('utf-8'))
                    usage = response_data.get("usage", {})
                    
                    return {
                        "success": True,
                        "test_name": test_name,
                        "response_time": response_time,
                        "status_code": response.getcode(),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                        "content_length": len(content),
                        "error": None
                    }
                else:
                    return {
                        "success": False,
                        "test_name": test_name,
                        "response_time": response_time,
                        "status_code": response.getcode(),
                        "error": f"HTTP {response.getcode()}"
                    }
                    
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "test_name": test_name,
                "response_time": response_time,
                "error": str(e)[:200]
            }
    
    def test_context_sizes(self) -> None:
        """Test various context sizes"""
        print("🔍 CONTEXT SIZE PERFORMANCE TEST")
        print("="*70)
        
        # Test different context sizes
        test_sizes = [1000, 5000, 10000, 20000, 50000, 100000, 150000, 200000]
        
        for size in test_sizes:
            print(f"\n📏 Testing {size:,} token context...")
            content = self.generate_content(size)
            
            # Run 3 requests for each size to get average
            times = []
            tokens = []
            
            for i in range(3):
                print(f"   Request {i+1}/3...", end=" ", flush=True)
                result = self.make_request(content, f"context_{size}")
                self.results.append(result)
                self.total_requests += 1
                
                if result["success"]:
                    times.append(result["response_time"])
                    tokens.append(result["prompt_tokens"])
                    print(f"✅ {result['response_time']:.2f}s ({result['prompt_tokens']} tokens)")
                else:
                    self.total_errors += 1
                    print(f"❌ {result['error']}")
                
                time.sleep(1)  # Rate limiting
            
            # Calculate statistics
            if times:
                avg_time = statistics.mean(times)
                avg_tokens = statistics.mean(tokens)
                tokens_per_second = avg_tokens / avg_time if avg_time > 0 else 0
                
                print(f"   📊 Average: {avg_time:.2f}s, {avg_tokens:.0f} tokens, {tokens_per_second:.0f} tokens/sec")
            else:
                print("   ⚠️  All requests failed")
    
    def test_concurrent_requests(self) -> None:
        """Test concurrent request handling"""
        print("\n\n🚀 CONCURRENT REQUEST PERFORMANCE TEST")
        print("="*70)
        
        content = self.generate_content(10000)  # 10k token content
        
        # Test different concurrency levels
        for concurrency in [1, 2, 4, 8]:
            print(f"\n⚡ Testing {concurrency} concurrent requests...")
            
            start_time = time.time()
            
            # Use ThreadPoolExecutor for concurrent requests
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = []
                for i in range(concurrency):
                    future = executor.submit(
                        self.make_request, 
                        content, 
                        f"concurrent_{concurrency}_{i}"
                    )
                    futures.append(future)
                
                # Collect results
                concurrent_results = []
                for future in futures:
                    result = future.result()
                    concurrent_results.append(result)
                    self.results.append(result)
                    self.total_requests += 1
                    
                    if not result["success"]:
                        self.total_errors += 1
            
            total_time = time.time() - start_time
            
            # Calculate statistics
            successful_results = [r for r in concurrent_results if r["success"]]
            if successful_results:
                response_times = [r["response_time"] for r in successful_results]
                avg_response_time = statistics.mean(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                
                requests_per_second = len(successful_results) / total_time
                
                print(f"   📈 Success: {len(successful_results)}/{concurrency}")
                print(f"   📊 Avg response time: {avg_response_time:.2f}s")
                print(f"   ⚡ Min/Max: {min_time:.2f}s / {max_time:.2f}s")
                print(f"   🎯 Requests/sec: {requests_per_second:.2f}")
                print(f"   ⏱️  Total time: {total_time:.2f}s")
            else:
                print("   ❌ All requests failed")
    
    def test_throughput(self) -> None:
        """Test sustained throughput"""
        print("\n\n📈 THROUGHPUT TEST (30 seconds)")
        print("="*70)
        
        content = self.generate_content(5000)  # 5k token content
        test_duration = 30  # seconds
        start_time = time.time()
        throughput_results = []
        
        request_count = 0
        while time.time() - start_time < test_duration:
            request_count += 1
            print(f"📡 Request {request_count}...", end=" ", flush=True)
            
            result = self.make_request(content, f"throughput_{request_count}")
            throughput_results.append(result)
            self.results.append(result)
            self.total_requests += 1
            
            if result["success"]:
                print(f"✅ {result['response_time']:.2f}s")
            else:
                self.total_errors += 1
                print(f"❌ {result['error']}")
            
            # Small delay to avoid overwhelming
            time.sleep(0.5)
        
        actual_duration = time.time() - start_time
        successful_requests = [r for r in throughput_results if r["success"]]
        
        if successful_requests:
            avg_response_time = statistics.mean([r["response_time"] for r in successful_requests])
            total_requests = len(throughput_results)
            success_rate = len(successful_requests) / total_requests * 100
            requests_per_second = total_requests / actual_duration
            
            print(f"\n📊 THROUGHPUT RESULTS:")
            print(f"   🎯 Total requests: {total_requests}")
            print(f"   ✅ Successful: {len(successful_requests)} ({success_rate:.1f}%)")
            print(f"   📈 Requests/sec: {requests_per_second:.2f}")
            print(f"   ⏱️  Avg response time: {avg_response_time:.2f}s")
            print(f"   🕐 Test duration: {actual_duration:.1f}s")
    
    def generate_report(self) -> None:
        """Generate comprehensive performance report"""
        print("\n\n📋 COMPREHENSIVE PERFORMANCE REPORT")
        print("="*70)
        
        successful_results = [r for r in self.results if r["success"]]
        
        if not successful_results:
            print("❌ No successful requests to analyze")
            return
        
        # Overall statistics
        response_times = [r["response_time"] for r in successful_results]
        prompt_tokens = [r["prompt_tokens"] for r in successful_results if "prompt_tokens" in r]
        
        print(f"🎯 Overall Results:")
        print(f"   Total Requests: {self.total_requests}")
        print(f"   Successful: {len(successful_results)} ({len(successful_results)/self.total_requests*100:.1f}%)")
        print(f"   Failed: {self.total_errors}")
        
        print(f"\n⏱️  Response Time Statistics:")
        print(f"   Average: {statistics.mean(response_times):.2f}s")
        print(f"   Median: {statistics.median(response_times):.2f}s")
        print(f"   Min: {min(response_times):.2f}s")
        print(f"   Max: {max(response_times):.2f}s")
        print(f"   Std Dev: {statistics.stdev(response_times):.2f}s")
        
        if prompt_tokens:
            print(f"\n📊 Token Processing:")
            print(f"   Avg Prompt Tokens: {statistics.mean(prompt_tokens):.0f}")
            print(f"   Max Prompt Tokens: {max(prompt_tokens)}")
            print(f"   Tokens/Second: {statistics.mean(prompt_tokens) / statistics.mean(response_times):.0f}")
        
        # Performance by context size
        context_results = {}
        for result in successful_results:
            test_name = result["test_name"]
            if "context_" in test_name:
                size = test_name.split("_")[1]
                if size not in context_results:
                    context_results[size] = []
                context_results[size].append(result["response_time"])
        
        if context_results:
            print(f"\n📏 Performance by Context Size:")
            for size in sorted(context_results.keys(), key=int):
                times = context_results[size]
                avg_time = statistics.mean(times)
                print(f"   {size:>8} tokens: {avg_time:.2f}s avg")
        
        print(f"\n🎉 Performance test completed!")
        print(f"📡 Endpoint: {OPENAI_BASE_URL}")
        print(f"🤖 Model: {MODEL_NAME}")

def main():
    """Main test execution"""
    print("🚀 GLM-4.6 PERFORMANCE TEST SUITE")
    print(f"📡 Endpoint: {OPENAI_BASE_URL}")
    print(f"🤖 Model: {MODEL_NAME}")
    print("="*70)
    
    # Test basic connectivity first
    test = PerformanceTest()
    print("🔗 Testing basic connectivity...")
    basic_result = test.make_request("Hello, please respond briefly.", "basic_connectivity")
    
    if not basic_result["success"]:
        print(f"❌ Basic connectivity failed: {basic_result['error']}")
        return
    
    print(f"✅ Connectivity confirmed ({basic_result['response_time']:.2f}s)")
    
    # Run performance tests
    try:
        test.test_context_sizes()
        test.test_concurrent_requests()
        test.test_throughput()
        test.generate_report()
        
    except KeyboardInterrupt:
        print("\n⏹️  Performance test interrupted by user")
        if test.results:
            test.generate_report()
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        if test.results:
            test.generate_report()

if __name__ == "__main__":
    main()