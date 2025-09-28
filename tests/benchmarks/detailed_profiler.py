#!/usr/bin/env python3
"""
Detailed performance profiler to identify specific overhead sources in the proxy.
This will help us understand exactly where the 58% overhead is coming from.
"""

import asyncio
import time
import statistics
import httpx
import json
import os
import cProfile
import pstats
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Optional

# Add project root to path and load environment from project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

# Configuration
PROXY_BASE_URL = "http://localhost:5000"
DIRECT_BASE_URL = os.getenv("UPSTREAM_BASE", "https://api.z.ai/api/anthropic")
API_KEY = os.getenv("SERVER_API_KEY")

class PerformanceProfiler:
    def __init__(self):
        self.timings = {
            "json_serialization": [],
            "http_request": [],
            "response_processing": [],
            "total_proxy": [],
            "total_direct": [],
            "proxy_overhead": []
        }
        
    @asynccontextmanager
    async def time_operation(self, operation_name: str):
        """Context manager to time specific operations"""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            if operation_name not in self.timings:
                self.timings[operation_name] = []
            self.timings[operation_name].append(duration)

    async def profile_proxy_request_detailed(self) -> Dict[str, float]:
        """Profile a proxy request with detailed timing breakdown"""
        timings = {}
        
        # Prepare payload
        payload = {
            "model": "glm-4.5",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Profile test message"}]
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "x-api-key": API_KEY
        }
        
        total_start = time.perf_counter()
        
        # Time JSON serialization
        json_start = time.perf_counter()
        json_payload = json.dumps(payload)
        timings["json_serialization"] = time.perf_counter() - json_start
        
        # Time HTTP request setup and execution
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            http_start = time.perf_counter()
            
            try:
                response = await client.post(
                    f"{PROXY_BASE_URL}/v1/messages",
                    json=payload,
                    headers=headers
                )
                timings["http_request"] = time.perf_counter() - http_start
                
                # Time response processing
                response_start = time.perf_counter()
                if response.status_code == 200:
                    response_data = response.json()
                    timings["response_processing"] = time.perf_counter() - response_start
                    timings["response_size"] = len(response.content)
                else:
                    timings["response_processing"] = time.perf_counter() - response_start
                    timings["error"] = True
                    
            except Exception as e:
                timings["http_request"] = time.perf_counter() - http_start
                timings["error"] = True
                timings["error_message"] = str(e)
        
        timings["total_time"] = time.perf_counter() - total_start
        return timings

    async def profile_direct_request_detailed(self) -> Dict[str, float]:
        """Profile a direct API request with detailed timing breakdown"""
        timings = {}
        
        payload = {
            "model": "glm-4.5",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": "Profile test message"}]
        }
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        total_start = time.perf_counter()
        
        # Time JSON serialization
        json_start = time.perf_counter()
        json_payload = json.dumps(payload)
        timings["json_serialization"] = time.perf_counter() - json_start
        
        # Time HTTP request
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            http_start = time.perf_counter()
            
            try:
                response = await client.post(
                    f"{DIRECT_BASE_URL}/v1/messages",
                    json=payload,
                    headers=headers
                )
                timings["http_request"] = time.perf_counter() - http_start
                
                # Time response processing
                response_start = time.perf_counter()
                if response.status_code == 200:
                    response_data = response.json()
                    timings["response_processing"] = time.perf_counter() - response_start
                    timings["response_size"] = len(response.content)
                else:
                    timings["response_processing"] = time.perf_counter() - response_start
                    timings["error"] = True
                    
            except Exception as e:
                timings["http_request"] = time.perf_counter() - http_start
                timings["error"] = True
                timings["error_message"] = str(e)
        
        timings["total_time"] = time.perf_counter() - total_start
        return timings

    async def run_detailed_comparison(self, iterations: int = 5) -> Dict:
        """Run detailed performance comparison"""
        print("🔍 DETAILED PERFORMANCE PROFILING")
        print("=" * 50)
        
        proxy_results = []
        direct_results = []
        
        print(f"\n📊 Running {iterations} iterations for detailed analysis...")
        
        # Test proxy requests
        print("Profiling proxy requests...")
        for i in range(iterations):
            result = await self.profile_proxy_request_detailed()
            proxy_results.append(result)
            if result.get("error"):
                print(f"  Proxy request {i+1}: ERROR - {result.get('error_message', 'Unknown error')}")
            else:
                print(f"  Proxy request {i+1}: {result['total_time']:.3f}s")
            await asyncio.sleep(0.1)  # Small delay between requests
        
        # Test direct requests  
        print("Profiling direct API requests...")
        for i in range(iterations):
            result = await self.profile_direct_request_detailed()
            direct_results.append(result)
            if result.get("error"):
                print(f"  Direct request {i+1}: ERROR - {result.get('error_message', 'Unknown error')}")
            else:
                print(f"  Direct request {i+1}: {result['total_time']:.3f}s")
            await asyncio.sleep(0.1)
        
        return self.analyze_detailed_results(proxy_results, direct_results)

    def analyze_detailed_results(self, proxy_results: List[Dict], direct_results: List[Dict]) -> Dict:
        """Analyze detailed profiling results"""
        
        # Filter out error results
        proxy_success = [r for r in proxy_results if not r.get("error")]
        direct_success = [r for r in direct_results if not r.get("error")]
        
        if not proxy_success or not direct_success:
            print("❌ Insufficient successful requests for analysis")
            return {}
        
        def calc_stats(results: List[Dict], field: str) -> Dict:
            values = [r[field] for r in results if field in r]
            if not values:
                return {"mean": 0, "min": 0, "max": 0, "std": 0}
            return {
                "mean": statistics.mean(values),
                "min": min(values),
                "max": max(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0
            }
        
        analysis = {
            "proxy": {
                "total_time": calc_stats(proxy_success, "total_time"),
                "json_serialization": calc_stats(proxy_success, "json_serialization"),
                "http_request": calc_stats(proxy_success, "http_request"),
                "response_processing": calc_stats(proxy_success, "response_processing"),
                "successful_requests": len(proxy_success),
                "failed_requests": len(proxy_results) - len(proxy_success)
            },
            "direct": {
                "total_time": calc_stats(direct_success, "total_time"),
                "json_serialization": calc_stats(direct_success, "json_serialization"),
                "http_request": calc_stats(direct_success, "http_request"),
                "response_processing": calc_stats(direct_success, "response_processing"),
                "successful_requests": len(direct_success),
                "failed_requests": len(direct_results) - len(direct_success)
            }
        }
        
        # Calculate overhead breakdown
        proxy_total = analysis["proxy"]["total_time"]["mean"]
        direct_total = analysis["direct"]["total_time"]["mean"]
        
        if proxy_total > 0 and direct_total > 0:
            total_overhead = proxy_total - direct_total
            overhead_percent = (total_overhead / direct_total) * 100
            
            analysis["overhead"] = {
                "total_ms": total_overhead * 1000,
                "percent": overhead_percent,
                "breakdown": {
                    "json_processing_overhead": (analysis["proxy"]["json_serialization"]["mean"] - 
                                               analysis["direct"]["json_serialization"]["mean"]) * 1000,
                    "http_overhead": (analysis["proxy"]["http_request"]["mean"] - 
                                    analysis["direct"]["http_request"]["mean"]) * 1000,
                    "response_processing_overhead": (analysis["proxy"]["response_processing"]["mean"] - 
                                                   analysis["direct"]["response_processing"]["mean"]) * 1000
                }
            }
        
        self.print_detailed_analysis(analysis)
        return analysis
    
    def print_detailed_analysis(self, analysis: Dict):
        """Print detailed analysis results"""
        print(f"\n📈 DETAILED PERFORMANCE BREAKDOWN")
        print("=" * 60)
        
        proxy = analysis["proxy"]
        direct = analysis["direct"]
        
        print(f"\n🔴 PROXY PERFORMANCE:")
        print(f"   Total Time: {proxy['total_time']['mean']:.3f}s ± {proxy['total_time']['std']:.3f}s")
        print(f"   - JSON Serialization: {proxy['json_serialization']['mean']*1000:.1f}ms")
        print(f"   - HTTP Request: {proxy['http_request']['mean']*1000:.1f}ms") 
        print(f"   - Response Processing: {proxy['response_processing']['mean']*1000:.1f}ms")
        print(f"   Success Rate: {proxy['successful_requests']}/{proxy['successful_requests'] + proxy['failed_requests']}")
        
        print(f"\n🔵 DIRECT API PERFORMANCE:")
        print(f"   Total Time: {direct['total_time']['mean']:.3f}s ± {direct['total_time']['std']:.3f}s")
        print(f"   - JSON Serialization: {direct['json_serialization']['mean']*1000:.1f}ms")
        print(f"   - HTTP Request: {direct['http_request']['mean']*1000:.1f}ms")
        print(f"   - Response Processing: {direct['response_processing']['mean']*1000:.1f}ms")
        print(f"   Success Rate: {direct['successful_requests']}/{direct['successful_requests'] + direct['failed_requests']}")
        
        if "overhead" in analysis:
            overhead = analysis["overhead"]
            print(f"\n⚠️  OVERHEAD ANALYSIS:")
            print(f"   Total Overhead: +{overhead['total_ms']:.1f}ms ({overhead['percent']:.1f}%)")
            print(f"   Breakdown:")
            print(f"   - JSON Processing: +{overhead['breakdown']['json_processing_overhead']:.1f}ms")
            print(f"   - HTTP Layer: +{overhead['breakdown']['http_overhead']:.1f}ms")
            print(f"   - Response Processing: +{overhead['breakdown']['response_processing_overhead']:.1f}ms")
            
            # Identify biggest bottleneck
            bottlenecks = overhead['breakdown']
            biggest_bottleneck = max(bottlenecks.items(), key=lambda x: abs(x[1]))
            print(f"\n🎯 BIGGEST BOTTLENECK: {biggest_bottleneck[0]} (+{biggest_bottleneck[1]:.1f}ms)")
            
            # Optimization suggestions
            print(f"\n💡 OPTIMIZATION SUGGESTIONS:")
            if bottlenecks['http_overhead'] > 50:
                print(f"   • HTTP Layer Overhead > 50ms - Check connection pooling effectiveness")
            if bottlenecks['json_processing_overhead'] > 10:
                print(f"   • JSON Processing > 10ms - Consider payload size optimization")
            if bottlenecks['response_processing_overhead'] > 20:
                print(f"   • Response Processing > 20ms - Optimize response transformation")

async def run_profiling():
    """Run the detailed performance profiling"""
    profiler = PerformanceProfiler()
    
    if not API_KEY:
        print("❌ Error: SERVER_API_KEY not found in .env file")
        return
    
    # Run detailed comparison
    results = await profiler.run_detailed_comparison(iterations=5)
    
    if results:
        print(f"\n🔧 NEXT OPTIMIZATION TARGETS:")
        if "overhead" in results:
            overhead = results["overhead"]["breakdown"]
            
            # Prioritize optimizations by impact
            optimizations = []
            if overhead.get("http_overhead", 0) > 50:
                optimizations.append("1. HTTP connection reuse optimization")
            if overhead.get("json_processing_overhead", 0) > 10:
                optimizations.append("2. JSON payload optimization")
            if overhead.get("response_processing_overhead", 0) > 20:
                optimizations.append("3. Response transformation optimization")
            
            for opt in optimizations:
                print(f"   {opt}")
            
            if not optimizations:
                print("   All major bottlenecks appear to be optimized!")
                print("   Remaining overhead may be due to:")
                print("   - Network latency differences")
                print("   - Proxy protocol translation overhead")
                print("   - FastAPI framework overhead")

if __name__ == "__main__":
    asyncio.run(run_profiling())