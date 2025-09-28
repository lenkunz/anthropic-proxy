#!/usr/bin/env python3
"""
Performance benchmark comparing proxy vs direct API calls.
Measures the actual overhead introduced by the proxy service.
"""

import asyncio
import time
import statistics
import httpx
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional

# Add project root to path and load environment from project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")
import time
import statistics
import httpx
import json
import os
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

# Configuration
PROXY_BASE_URL = "http://localhost:5000"
DIRECT_BASE_URL = os.getenv("UPSTREAM_BASE", "https://api.z.ai/api/anthropic")
API_KEY = os.getenv("SERVER_API_KEY")

class PerformanceBenchmark:
    def __init__(self):
        self.results = {
            "proxy": {"times": [], "errors": 0, "total_requests": 0},
            "direct": {"times": [], "errors": 0, "total_requests": 0}
        }
    
    async def benchmark_proxy_endpoint(self, iterations: int = 5) -> List[float]:
        """Benchmark proxy /v1/messages endpoint"""
        times = []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "x-api-key": API_KEY
        }
        
        payload = {
            "model": "glm-4.5",
            "max_tokens": 50,
            "messages": [
                {"role": "user", "content": "Hello, this is a performance test message."}
            ]
        }
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            for i in range(iterations):
                start_time = time.perf_counter()
                try:
                    response = await client.post(
                        f"{PROXY_BASE_URL}/v1/messages",
                        json=payload,
                        headers=headers
                    )
                    end_time = time.perf_counter()
                    
                    if response.status_code == 200:
                        times.append(end_time - start_time)
                        self.results["proxy"]["total_requests"] += 1
                    else:
                        print(f"Proxy error {i+1}: {response.status_code} - {response.text[:100]}")
                        self.results["proxy"]["errors"] += 1
                        
                except Exception as e:
                    print(f"Proxy request {i+1} failed: {e}")
                    self.results["proxy"]["errors"] += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)
        
        self.results["proxy"]["times"] = times
        return times
    
    async def benchmark_direct_endpoint(self, iterations: int = 5) -> List[float]:
        """Benchmark direct API endpoint"""
        times = []
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": "glm-4.5",
            "max_tokens": 50,
            "messages": [
                {"role": "user", "content": "Hello, this is a performance test message."}
            ]
        }
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            for i in range(iterations):
                start_time = time.perf_counter()
                try:
                    response = await client.post(
                        f"{DIRECT_BASE_URL}/v1/messages",
                        json=payload,
                        headers=headers
                    )
                    end_time = time.perf_counter()
                    
                    if response.status_code == 200:
                        times.append(end_time - start_time)
                        self.results["direct"]["total_requests"] += 1
                    else:
                        print(f"Direct error {i+1}: {response.status_code} - {response.text[:100]}")
                        self.results["direct"]["errors"] += 1
                        
                except Exception as e:
                    print(f"Direct request {i+1} failed: {e}")
                    self.results["direct"]["errors"] += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)
        
        self.results["direct"]["times"] = times
        return times
    
    def calculate_statistics(self, times: List[float]) -> Dict[str, float]:
        """Calculate performance statistics"""
        if not times:
            return {"min": 0, "max": 0, "mean": 0, "median": 0, "std": 0}
        
        return {
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "std": statistics.stdev(times) if len(times) > 1 else 0
        }
    
    def print_results(self):
        """Print comprehensive performance comparison"""
        print("\n" + "="*80)
        print("PERFORMANCE BENCHMARK: PROXY vs DIRECT API")
        print("="*80)
        
        proxy_stats = self.calculate_statistics(self.results["proxy"]["times"])
        direct_stats = self.calculate_statistics(self.results["direct"]["times"])
        
        print(f"\n📊 PROXY PERFORMANCE:")
        print(f"   Requests: {self.results['proxy']['total_requests']} successful, {self.results['proxy']['errors']} errors")
        if proxy_stats["mean"] > 0:
            print(f"   Response Time: {proxy_stats['mean']:.3f}s avg, {proxy_stats['median']:.3f}s median")
            print(f"   Range: {proxy_stats['min']:.3f}s - {proxy_stats['max']:.3f}s")
            print(f"   Std Dev: ±{proxy_stats['std']:.3f}s")
        
        print(f"\n📊 DIRECT API PERFORMANCE:")
        print(f"   Requests: {self.results['direct']['total_requests']} successful, {self.results['direct']['errors']} errors")
        if direct_stats["mean"] > 0:
            print(f"   Response Time: {direct_stats['mean']:.3f}s avg, {direct_stats['median']:.3f}s median")
            print(f"   Range: {direct_stats['min']:.3f}s - {direct_stats['max']:.3f}s")
            print(f"   Std Dev: ±{direct_stats['std']:.3f}s")
        
        # Calculate overhead
        if proxy_stats["mean"] > 0 and direct_stats["mean"] > 0:
            overhead_ms = (proxy_stats["mean"] - direct_stats["mean"]) * 1000
            overhead_percent = ((proxy_stats["mean"] / direct_stats["mean"]) - 1) * 100
            
            print(f"\n🔍 PROXY OVERHEAD ANALYSIS:")
            print(f"   Absolute Overhead: +{overhead_ms:.1f}ms per request")
            print(f"   Relative Overhead: +{overhead_percent:.1f}%")
            
            if overhead_ms < 50:
                print(f"   ✅ LOW OVERHEAD: Proxy adds minimal latency")
            elif overhead_ms < 100:
                print(f"   ⚠️  MODERATE OVERHEAD: Acceptable for most use cases")
            else:
                print(f"   ❌ HIGH OVERHEAD: Consider optimization")
        
        # Performance breakdown estimate
        if proxy_stats["mean"] > 0:
            print(f"\n🔧 ESTIMATED OVERHEAD BREAKDOWN:")
            print(f"   • JSON Processing: ~5-15ms")
            print(f"   • HTTP Proxy Layer: ~10-30ms")
            print(f"   • Connection Setup: ~50-200ms (without pooling)")
            print(f"   • Logging/Debugging: ~5-20ms")
            print(f"   • Token Processing: ~10-50ms")

async def run_concurrent_benchmark(iterations: int = 3, concurrency: int = 2):
    """Run concurrent requests to test under load"""
    print(f"\n🚀 CONCURRENT LOAD TEST ({concurrency} concurrent requests)")
    
    benchmark = PerformanceBenchmark()
    
    # Create concurrent tasks
    proxy_tasks = []
    direct_tasks = []
    
    for _ in range(concurrency):
        proxy_tasks.append(benchmark.benchmark_proxy_endpoint(iterations))
        direct_tasks.append(benchmark.benchmark_direct_endpoint(iterations))
    
    # Run proxy tests
    print("Testing proxy under concurrent load...")
    proxy_results = await asyncio.gather(*proxy_tasks, return_exceptions=True)
    
    # Run direct tests
    print("Testing direct API under concurrent load...")  
    direct_results = await asyncio.gather(*direct_tasks, return_exceptions=True)
    
    # Flatten results
    all_proxy_times = []
    all_direct_times = []
    
    for result in proxy_results:
        if isinstance(result, list):
            all_proxy_times.extend(result)
    
    for result in direct_results:
        if isinstance(result, list):
            all_direct_times.extend(result)
    
    # Calculate concurrent performance
    if all_proxy_times and all_direct_times:
        proxy_avg = statistics.mean(all_proxy_times)
        direct_avg = statistics.mean(all_direct_times)
        overhead_ms = (proxy_avg - direct_avg) * 1000
        
        print(f"\n📈 CONCURRENT PERFORMANCE RESULTS:")
        print(f"   Proxy Average: {proxy_avg:.3f}s")
        print(f"   Direct Average: {direct_avg:.3f}s") 
        print(f"   Overhead under load: +{overhead_ms:.1f}ms")

async def main():
    """Main benchmark execution"""
    print("🔍 ANTHROPIC PROXY PERFORMANCE ANALYSIS")
    print("=" * 50)
    
    if not API_KEY:
        print("❌ Error: SERVER_API_KEY not found in .env file")
        return
    
    benchmark = PerformanceBenchmark()
    
    print("\n⏱️  Running sequential performance tests...")
    
    # Sequential tests
    print("Testing proxy performance...")
    await benchmark.benchmark_proxy_endpoint(5)
    
    print("Testing direct API performance...")
    await benchmark.benchmark_direct_endpoint(5)
    
    # Print results
    benchmark.print_results()
    
    # Concurrent load test
    await run_concurrent_benchmark(3, 2)
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   1. Implement HTTP connection pooling to reduce connection overhead")
    print(f"   2. Add response caching for frequently requested operations")
    print(f"   3. Optimize logging in production (conditional debug logging)")
    print(f"   4. Consider request batching for high-throughput scenarios")

if __name__ == "__main__":
    asyncio.run(main())