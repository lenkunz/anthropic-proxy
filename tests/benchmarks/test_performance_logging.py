#!/usr/bin/env python3
"""Test performance improvements for async logging system"""

import asyncio
import time
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY", "test-key")

async def test_logging_performance():
    """Test the performance of the new async logging system"""
    print("🚀 Testing Async Logging Performance")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Test with different performance levels
    performance_levels = [
        ("minimal", "Maximum performance, minimal logging"),
        ("performance", "High performance, essential logging"),
        ("balanced", "Balanced performance and detail"),
        ("max_detail", "Maximum detail, lower performance")
    ]
    
    for level, description in performance_levels:
        print(f"\n=== Testing Performance Level: {level} ===")
        print(f"Description: {description}")
        
        # Set environment variable for this test
        os.environ["LOGGING_PERFORMANCE_LEVEL"] = level
        
        # Make multiple rapid requests to test performance
        start_time = time.time()
        request_count = 10
        
        for i in range(request_count):
            payload = {
                "model": "glm-4.5-openai",
                "messages": [{"role": "user", "content": f"Test message {i+1}"}],
                "max_tokens": 20
            }
            
            try:
                response = requests.post(f"{BASE_URL}/v1/chat/completions",
                                       json=payload, headers=headers, timeout=30)
                if i == 0:  # Show first response
                    print(f"  First response status: {response.status_code}")
            except Exception as e:
                print(f"  Request {i+1} failed: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / request_count
        
        print(f"  📊 Results for {request_count} requests:")
        print(f"     Total time: {total_time:.2f}s")
        print(f"     Average time per request: {avg_time:.3f}s")
        print(f"     Requests per second: {request_count/total_time:.2f}")
        
        # Small delay between tests
        await asyncio.sleep(2)

def test_different_log_scenarios():
    """Test different logging scenarios to see performance impact"""
    print("\n🔄 Testing Different Logging Scenarios")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    scenarios = [
        {
            "name": "Fast Text Request",
            "payload": {
                "model": "glm-4.5-openai",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            "expected_log_level": "DEBUG (minimal logging)"
        },
        {
            "name": "Slow Text Request",
            "payload": {
                "model": "glm-4.5-anthropic",
                "messages": [{"role": "user", "content": "Write a long story about a dragon"}],
                "max_tokens": 200
            },
            "expected_log_level": "IMPORTANT (detailed logging)"
        },
        {
            "name": "Invalid Model (Error)",
            "payload": {
                "model": "nonexistent-model",
                "messages": [{"role": "user", "content": "This will fail"}],
                "max_tokens": 20
            },
            "expected_log_level": "CRITICAL (full error logging)"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n=== {scenario['name']} ===")
        print(f"Expected logging level: {scenario['expected_log_level']}")
        
        start_time = time.time()
        try:
            response = requests.post(f"{BASE_URL}/v1/chat/completions",
                                   json=scenario['payload'], headers=headers, timeout=60)
            end_time = time.time()
            
            print(f"Status: {response.status_code}")
            print(f"Response time: {(end_time - start_time)*1000:.1f}ms")
            
        except Exception as e:
            end_time = time.time()
            print(f"Error: {e}")
            print(f"Response time: {(end_time - start_time)*1000:.1f}ms")

def check_new_log_files():
    """Check if the new async log files were created"""
    print("\n📄 Checking New Log Files")
    print("=" * 60)
    
    log_files = [
        "logs/upstream_responses.json",
        "logs/performance_metrics.json",
        "logs/error_logs.json"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"✅ {log_file}: {size} bytes")
            
            # Show sample entries
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()[-3:]  # Last 3 lines
                    for line in lines:
                        if line.strip():
                            entry = json.loads(line.strip())
                            print(f"   📝 {entry.get('type', 'unknown')}: {entry.get('timestamp', 'no timestamp')}")
            except Exception as e:
                print(f"   ⚠️  Could not read entries: {e}")
        else:
            print(f"❌ {log_file}: Not found")

async def main():
    """Run all performance tests"""
    print("🎯 Async Logging Performance Test Suite")
    print("=" * 80)
    
    # Test performance with different levels
    await test_logging_performance()
    
    # Test different scenarios
    test_different_log_scenarios()
    
    # Check log files
    await asyncio.sleep(3)  # Wait for async logs to be written
    check_new_log_files()
    
    print("\n🎉 Performance testing completed!")
    print("\n💡 Tips for production:")
    print("   - Use LOGGING_PERFORMANCE_LEVEL=performance for high-load production")  
    print("   - Use LOGGING_PERFORMANCE_LEVEL=balanced for normal production")
    print("   - Use LOGGING_PERFORMANCE_LEVEL=max_detail only for debugging")

if __name__ == "__main__":
    asyncio.run(main())