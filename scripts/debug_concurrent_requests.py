#!/usr/bin/env python3
"""
Concurrent Request Handling Diagnostic Script for Anthropic Proxy

This script helps identify potential bottlenecks and blocking operations
that could cause requests to get stuck in a concurrent environment.

Usage:
    python debug_concurrent_requests.py

The script will:
1. Test concurrent request handling
2. Measure response times under load
3. Identify blocking operations
4. Check for resource contention
5. Validate timeout configurations
"""

import asyncio
import time
import json
import threading
import concurrent.futures
from typing import List, Dict, Any
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ConcurrentRequestDiagnostics:
    """Diagnostic tools for concurrent request handling"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_key = os.getenv("SERVER_API_KEY")
        if not self.api_key:
            print("❌ SERVER_API_KEY not found in .env file")
            exit(1)
        
        self.results = []
        
    async def test_concurrent_requests(self, num_requests: int = 10, delay_between: float = 0.1):
        """Test concurrent requests to identify blocking operations"""
        print(f"\n🔄 Testing {num_requests} concurrent requests...")
        
        async def make_request(request_id: int):
            start_time = time.time()
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "glm-4.6",
                            "messages": [
                                {"role": "user", "content": f"Test request {request_id}: What is 2+2?"}
                            ],
                            "max_tokens": 50,
                            "stream": False
                        }
                    )
                    
                    end_time = time.time()
                    duration = end_time - start_time
                    
                    result = {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "duration": duration,
                        "success": response.status_code == 200,
                        "thread_id": threading.current_thread().ident,
                        "start_time": start_time,
                        "end_time": end_time
                    }
                    
                    if response.status_code != 200:
                        result["error"] = response.text
                    
                    return result
                    
            except Exception as e:
                end_time = time.time()
                return {
                    "request_id": request_id,
                    "status_code": 0,
                    "duration": end_time - start_time,
                    "success": False,
                    "error": str(e),
                    "thread_id": threading.current_thread().ident,
                    "start_time": start_time,
                    "end_time": end_time
                }
        
        # Create tasks with staggered starts
        tasks = []
        for i in range(num_requests):
            task = asyncio.create_task(make_request(i))
            tasks.append(task)
            if delay_between > 0:
                await asyncio.sleep(delay_between)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful = [r for r in results if isinstance(r, dict) and r.get("success", False)]
        failed = [r for r in results if isinstance(r, dict) and not r.get("success", False)]
        exceptions = [r for r in results if not isinstance(r, dict)]
        
        print(f"\n📊 Results Summary:")
        print(f"  Total requests: {num_requests}")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Exceptions: {len(exceptions)}")
        
        if successful:
            durations = [r["duration"] for r in successful]
            print(f"  Average duration: {sum(durations)/len(durations):.2f}s")
            print(f"  Min duration: {min(durations):.2f}s")
            print(f"  Max duration: {max(durations):.2f}s")
            
            # Check for requests that took unusually long
            avg_duration = sum(durations) / len(durations)
            slow_requests = [r for r in successful if r["duration"] > avg_duration * 2]
            if slow_requests:
                print(f"  ⚠️  {len(slow_requests)} requests were unusually slow (>2x average):")
                for r in slow_requests:
                    print(f"    Request {r['request_id']}: {r['duration']:.2f}s")
        
        if failed:
            print(f"\n❌ Failed requests:")
            for r in failed:
                print(f"  Request {r['request_id']}: {r.get('error', 'Unknown error')}")
        
        if exceptions:
            print(f"\n💥 Exceptions:")
            for i, exc in enumerate(exceptions):
                print(f"  Request {i}: {exc}")
        
        self.results.extend(successful + failed)
        return successful, failed, exceptions
    
    def analyze_threading_patterns(self):
        """Analyze threading patterns to identify potential contention"""
        print(f"\n🧵 Threading Analysis:")
        
        if not self.results:
            print("  No results to analyze")
            return
        
        # Group by thread ID
        thread_groups = {}
        for result in self.results:
            thread_id = result.get("thread_id")
            if thread_id not in thread_groups:
                thread_groups[thread_id] = []
            thread_groups[thread_id].append(result)
        
        print(f"  Total threads used: {len(thread_groups)}")
        
        for thread_id, requests in thread_groups.items():
            durations = [r["duration"] for r in requests if r.get("success", False)]
            if durations:
                print(f"  Thread {thread_id}: {len(requests)} requests, avg duration: {sum(durations)/len(durations):.2f}s")
        
        # Check if all requests ran on the same thread (potential blocking issue)
        if len(thread_groups) == 1:
            print(f"  ⚠️  All requests ran on the same thread - potential blocking issue!")
    
    async def test_timeout_configurations(self):
        """Test various timeout configurations"""
        print(f"\n⏱️  Testing timeout configurations...")
        
        timeout_tests = [
            {"timeout": 5.0, "description": "5 second timeout"},
            {"timeout": 10.0, "description": "10 second timeout"},
            {"timeout": 30.0, "description": "30 second timeout"},
        ]
        
        for test in timeout_tests:
            print(f"  Testing {test['description']}...")
            start_time = time.time()
            
            try:
                async with httpx.AsyncClient(timeout=test["timeout"]) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "glm-4.6",
                            "messages": [
                                {"role": "user", "content": "Quick test: What is 1+1?"}
                            ],
                            "max_tokens": 10,
                            "stream": False
                        }
                    )
                    
                    duration = time.time() - start_time
                    print(f"    ✅ Completed in {duration:.2f}s (status: {response.status_code})")
                    
            except httpx.TimeoutException:
                duration = time.time() - start_time
                print(f"    ⏰ Timed out after {duration:.2f}s")
            except Exception as e:
                duration = time.time() - start_time
                print(f"    ❌ Failed after {duration:.2f}s: {e}")
    
    async def test_streaming_vs_non_streaming(self):
        """Compare streaming vs non-streaming performance"""
        print(f"\n🌊 Testing streaming vs non-streaming...")
        
        # Test non-streaming
        print("  Testing non-streaming request...")
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "glm-4.6",
                        "messages": [
                            {"role": "user", "content": "Write a short poem about coding."}
                        ],
                        "max_tokens": 100,
                        "stream": False
                    }
                )
                non_streaming_duration = time.time() - start_time
                print(f"    ✅ Non-streaming completed in {non_streaming_duration:.2f}s")
        except Exception as e:
            non_streaming_duration = time.time() - start_time
            print(f"    ❌ Non-streaming failed after {non_streaming_duration:.2f}s: {e}")
        
        # Test streaming
        print("  Testing streaming request...")
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "glm-4.6",
                        "messages": [
                            {"role": "user", "content": "Write a short poem about coding."}
                        ],
                        "max_tokens": 100,
                        "stream": True
                    }
                ) as response:
                    # Read the stream
                    async for chunk in response.aiter_text():
                        pass
                    
                    streaming_duration = time.time() - start_time
                    print(f"    ✅ Streaming completed in {streaming_duration:.2f}s")
                    
        except Exception as e:
            streaming_duration = time.time() - start_time
            print(f"    ❌ Streaming failed after {streaming_duration:.2f}s: {e}")
    
    async def test_image_processing_impact(self):
        """Test the impact of image processing on concurrent requests"""
        print(f"\n🖼️  Testing image processing impact...")
        
        # Test with image (if vision model is available)
        print("  Testing request with image...")
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "glm-4.6",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Describe this image briefly."},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": "https://picsum.photos/100/100"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 50,
                        "stream": False
                    }
                )
                
                image_duration = time.time() - start_time
                print(f"    ✅ Image request completed in {image_duration:.2f}s (status: {response.status_code})")
                
        except Exception as e:
            image_duration = time.time() - start_time
            print(f"    ❌ Image request failed after {image_duration:.2f}s: {e}")
    
    def check_server_health(self):
        """Check server health and configuration"""
        print(f"\n🏥 Checking server health...")
        
        try:
            response = httpx.get(f"{self.base_url}/v1/models", timeout=10.0)
            if response.status_code == 200:
                models = response.json()
                print(f"  ✅ Server is healthy")
                print(f"  Available models: {len(models.get('data', []))}")
            else:
                print(f"  ⚠️  Server returned status {response.status_code}")
        except Exception as e:
            print(f"  ❌ Server health check failed: {e}")
    
    async def run_full_diagnostic(self):
        """Run the complete diagnostic suite"""
        print("🚀 Starting Concurrent Request Handling Diagnostics")
        print("=" * 60)
        
        # Check server health first
        self.check_server_health()
        
        # Test concurrent requests with different loads
        await self.test_concurrent_requests(num_requests=5, delay_between=0.5)
        await self.test_concurrent_requests(num_requests=10, delay_between=0.1)
        await self.test_concurrent_requests(num_requests=20, delay_between=0.05)
        
        # Analyze results
        self.analyze_threading_patterns()
        
        # Test timeout configurations
        await self.test_timeout_configurations()
        
        # Test streaming vs non-streaming
        await self.test_streaming_vs_non_streaming()
        
        # Test image processing impact
        await self.test_image_processing_impact()
        
        print(f"\n📋 Diagnostic Summary:")
        print(f"  Total requests tested: {len(self.results)}")
        successful = [r for r in self.results if r.get("success", False)]
        print(f"  Successful requests: {len(successful)}")
        print(f"  Success rate: {len(successful)/len(self.results)*100:.1f}%" if self.results else "N/A")
        
        if successful:
            avg_duration = sum(r["duration"] for r in successful) / len(successful)
            print(f"  Average response time: {avg_duration:.2f}s")
            
            # Flag potential issues
            if avg_duration > 10.0:
                print(f"  ⚠️  High average response time detected")
            
            if len(successful) < len(self.results) * 0.8:
                print(f"  ⚠️  Low success rate detected")
        
        print(f"\n🔍 Recommendations:")
        print(f"  1. Monitor the logs for any error patterns during concurrent requests")
        print(f"  2. Check for blocking operations in the request processing pipeline")
        print(f"  3. Verify that HTTP client connection pooling is working correctly")
        print(f"  4. Ensure async/await is used consistently throughout the codebase")
        print(f"  5. Consider adding more detailed logging for request tracking")

async def main():
    """Main diagnostic function"""
    diagnostics = ConcurrentRequestDiagnostics()
    await diagnostics.run_full_diagnostic()

if __name__ == "__main__":
    asyncio.run(main())