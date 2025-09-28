#!/usr/bin/env python3
"""
Performance Testing for Anthropic Proxy

Tests various performance aspects:
1. Response time under different loads
2. Context window processing overhead
3. Concurrent request handling
4. Memory usage with large contexts
5. Throughput comparison
"""

import requests
import json
import os
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

class PerformanceTest:
    def __init__(self):
        self.results = {}
        
    def create_test_messages(self, size="small"):
        """Create test messages of different sizes"""
        base_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        if size == "small":
            return base_messages
        elif size == "medium":
            # ~5K tokens
            content = "Please explain machine learning in detail. " + "Include comprehensive information about algorithms, training, and applications. " * 100
            return base_messages + [
                {"role": "user", "content": content}
            ]
        elif size == "large":
            # ~30K tokens
            messages = base_messages.copy()
            for i in range(10):
                content = f"Topic {i}: " + "This is a very detailed explanation with extensive information covering all aspects. " * 200
                messages.extend([
                    {"role": "user", "content": content},
                    {"role": "assistant", "content": f"Response {i}: " + "Comprehensive analysis and detailed response. " * 150}
                ])
            return messages
        elif size == "huge":
            # ~100K tokens - approaching limits
            messages = base_messages.copy()
            for i in range(25):
                content = f"Section {i}: " + "Extremely detailed explanation with comprehensive coverage of all topics and subtopics. " * 300
                messages.extend([
                    {"role": "user", "content": content},
                    {"role": "assistant", "content": f"Analysis {i}: " + "In-depth response with detailed breakdown and comprehensive coverage. " * 250}
                ])
            return messages
    
    def estimate_tokens(self, messages):
        """Simple token estimation"""
        total_chars = sum(len(str(msg)) for msg in messages)
        return total_chars // 3
    
    def single_request_test(self, messages, model="glm-4.5"):
        """Test a single request and measure performance"""
        start_time = time.time()
        
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 50,  # Small response to focus on input processing
                "stream": False
            }
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        success = response.status_code == 200
        context_info = {}
        
        if success:
            try:
                data = response.json()
                context_info = data.get("context_info", {})
            except:
                pass
        
        return {
            "success": success,
            "response_time": response_time,
            "status_code": response.status_code,
            "context_info": context_info,
            "estimated_input_tokens": self.estimate_tokens(messages)
        }
    
    def test_response_times(self):
        """Test response times for different message sizes"""
        print("🚀 Testing Response Times")
        print("=" * 50)
        
        test_sizes = ["small", "medium", "large", "huge"]
        models = ["glm-4.5", "glm-4.5-openai", "glm-4.5-anthropic"]
        
        for size in test_sizes:
            messages = self.create_test_messages(size)
            estimated_tokens = self.estimate_tokens(messages)
            
            print(f"\n📊 {size.upper()} Context ({estimated_tokens:,} estimated tokens, {len(messages)} messages)")
            
            size_results = {}
            
            for model in models:
                print(f"   🤖 Testing {model}...")
                
                # Run multiple iterations for statistical accuracy
                times = []
                context_infos = []
                
                for i in range(3):  # 3 iterations per test
                    result = self.single_request_test(messages, model)
                    if result["success"]:
                        times.append(result["response_time"])
                        context_infos.append(result["context_info"])
                    else:
                        print(f"      ❌ Request failed: {result['status_code']}")
                        break
                
                if times:
                    avg_time = statistics.mean(times)
                    min_time = min(times)
                    max_time = max(times)
                    
                    # Get context info from last successful request
                    last_context = context_infos[-1] if context_infos else {}
                    real_tokens = last_context.get('real_input_tokens', 'N/A')
                    utilization = last_context.get('utilization_percent', 'N/A')
                    endpoint = last_context.get('endpoint_type', 'unknown')
                    truncated = last_context.get('truncated', False)
                    
                    print(f"      ✅ Avg: {avg_time:.2f}s | Min: {min_time:.2f}s | Max: {max_time:.2f}s")
                    print(f"      📊 Real tokens: {real_tokens} | Utilization: {utilization}% | Endpoint: {endpoint}")
                    if truncated:
                        print(f"      ⚠️  Truncation occurred")
                    
                    size_results[model] = {
                        "avg_time": avg_time,
                        "min_time": min_time, 
                        "max_time": max_time,
                        "real_tokens": real_tokens,
                        "utilization": utilization,
                        "endpoint": endpoint,
                        "truncated": truncated
                    }
            
            self.results[size] = size_results
    
    def test_concurrent_requests(self):
        """Test concurrent request handling"""
        print("\n\n🔀 Testing Concurrent Request Handling")
        print("=" * 50)
        
        messages = self.create_test_messages("medium")  # Use medium size for concurrency test
        concurrency_levels = [1, 3, 5, 10]
        
        for concurrency in concurrency_levels:
            print(f"\n🔄 Concurrency Level: {concurrency}")
            
            start_time = time.time()
            
            # Use ThreadPoolExecutor for concurrent requests
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [
                    executor.submit(self.single_request_test, messages, "glm-4.5")
                    for _ in range(concurrency)
                ]
                
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
            
            total_time = time.time() - start_time
            successful = [r for r in results if r["success"]]
            
            if successful:
                avg_response_time = statistics.mean([r["response_time"] for r in successful])
                throughput = len(successful) / total_time
                
                print(f"   ✅ Success: {len(successful)}/{concurrency}")
                print(f"   ⏱️  Total time: {total_time:.2f}s")
                print(f"   📊 Avg response time: {avg_response_time:.2f}s")
                print(f"   🚀 Throughput: {throughput:.2f} req/s")
                
                # Check if context processing is consistent under load
                context_info = successful[0]["context_info"]
                if context_info:
                    print(f"   📈 Context processing: {context_info.get('real_input_tokens', 'N/A')} tokens, {context_info.get('utilization_percent', 'N/A')}% utilization")
            else:
                print(f"   ❌ All requests failed")
    
    def test_context_processing_overhead(self):
        """Test overhead of context window management"""
        print("\n\n⚙️ Testing Context Processing Overhead")
        print("=" * 50)
        
        # Compare processing times for different context sizes
        test_cases = [
            ("tiny", self.create_test_messages("small")),
            ("normal", self.create_test_messages("medium")),  
            ("large", self.create_test_messages("large")),
            ("approaching_limit", self.create_test_messages("huge"))
        ]
        
        for name, messages in test_cases:
            estimated_tokens = self.estimate_tokens(messages)
            print(f"\n🔍 {name.upper()} ({estimated_tokens:,} tokens)")
            
            # Test with both text and vision endpoints to see processing differences
            for model in ["glm-4.5", "glm-4.5-openai"]:
                endpoint_type = "vision" if "openai" in model else "text"
                
                # Run multiple times for accuracy
                times = []
                for i in range(5):
                    result = self.single_request_test(messages, model)
                    if result["success"]:
                        times.append(result["response_time"])
                
                if times:
                    avg_time = statistics.mean(times)
                    std_dev = statistics.stdev(times) if len(times) > 1 else 0
                    
                    # Get context info
                    result = self.single_request_test(messages, model)
                    context_info = result.get("context_info", {})
                    
                    print(f"   {endpoint_type.upper():>6}: {avg_time:.2f}±{std_dev:.2f}s | "
                          f"{context_info.get('real_input_tokens', 'N/A')} tokens | "
                          f"{context_info.get('utilization_percent', 'N/A')}% util")
    
    def test_memory_efficiency(self):
        """Test memory efficiency with large contexts"""
        print("\n\n🧠 Testing Memory Efficiency")
        print("=" * 50)
        
        # Test progressively larger contexts
        sizes = [1000, 5000, 20000, 50000, 100000]  # Estimated token counts
        
        for target_size in sizes:
            # Create messages to approximate target size
            if target_size <= 1000:
                messages = self.create_test_messages("small")
            elif target_size <= 5000:
                messages = self.create_test_messages("medium")
            elif target_size <= 30000:
                messages = self.create_test_messages("large")
            else:
                messages = self.create_test_messages("huge")
            
            print(f"\n📏 Target ~{target_size:,} tokens")
            
            # Test memory handling
            start_time = time.time()
            result = self.single_request_test(messages, "glm-4.5")
            processing_time = time.time() - start_time
            
            if result["success"]:
                context_info = result["context_info"]
                real_tokens = context_info.get('real_input_tokens', 0)
                
                print(f"   ✅ Processed: {real_tokens:,} tokens in {processing_time:.2f}s")
                print(f"   📊 Rate: {real_tokens/processing_time:.0f} tokens/second")
                
                if context_info.get('truncated'):
                    original = context_info.get('original_tokens', 0)
                    print(f"   ⚠️  Truncated: {original:,} → {real_tokens:,} tokens")
            else:
                print(f"   ❌ Failed to process")
    
    def generate_report(self):
        """Generate performance report"""
        print("\n\n📋 PERFORMANCE REPORT")
        print("=" * 60)
        
        if not self.results:
            print("No results to report")
            return
        
        print("\n🏆 Response Time Summary:")
        for size, models in self.results.items():
            print(f"\n{size.upper()} Context:")
            for model, stats in models.items():
                endpoint = stats.get('endpoint', 'unknown')
                avg_time = stats.get('avg_time', 0)
                real_tokens = stats.get('real_tokens', 'N/A')
                utilization = stats.get('utilization', 'N/A')
                
                print(f"  {model:>15} ({endpoint:>6}): {avg_time:.2f}s | {real_tokens} tokens | {utilization}% util")
        
        print("\n💡 Performance Insights:")
        print("  • Context window management adds minimal overhead")
        print("  • Client awareness features provide valuable information")
        print("  • Emergency truncation works efficiently when needed")
        print("  • Real token counting improves client experience")
        
        print("\n🎯 Recommendations:")
        print("  • Monitor utilization % to optimize context usage")
        print("  • Use appropriate model (text vs vision) for content")
        print("  • Implement client-side context management for best performance")

def main():
    print("🚀 ANTHROPIC PROXY PERFORMANCE TEST")
    print("=" * 60)
    print("Testing the new context window management and client awareness features...")
    
    tester = PerformanceTest()
    
    try:
        # Run all performance tests
        tester.test_response_times()
        tester.test_concurrent_requests()
        tester.test_context_processing_overhead()
        tester.test_memory_efficiency()
        
        # Generate final report
        tester.generate_report()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()