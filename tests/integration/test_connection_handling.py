#!/usr/bin/env python3
"""
Test script to verify connection handling improvements.
This script tests various connection failure scenarios to ensure
they are properly propagated from server to client.
"""

import asyncio
import aiohttp
import json
import time
import sys
from typing import Dict, Any

# Test configuration
PROXY_BASE_URL = "http://localhost:5000"
TIMEOUT_SECONDS = 5

async def test_invalid_upstream():
    """Test connection to invalid upstream server."""
    print("Testing invalid upstream server connection...")
    
    # This should fail quickly and return an error
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True
        }
        
        try:
            async with session.post(
                f"{PROXY_BASE_URL}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            ) as response:
                print(f"Response status: {response.status}")
                
                if response.content_type == "text/event-stream":
                    print("Received streaming response:")
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str and not line_str.startswith(":"):
                            print(f"  {line_str}")
                            if "connection_error" in line_str:
                                print("✓ Connection error properly detected and propagated")
                                return True
                else:
                    content = await response.text()
                    print(f"Response content: {content}")
                    
        except asyncio.TimeoutError:
            print("✓ Request properly timed out")
            return True
        except Exception as e:
            print(f"Error: {e}")
            
    return False

async def test_streaming_timeout():
    """Test streaming connection timeout."""
    print("\nTesting streaming connection timeout...")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "gpt-4", 
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True
        }
        
        try:
            async with session.post(
                f"{PROXY_BASE_URL}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            ) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 502:
                    content = await response.json()
                    if "connection" in str(content).lower():
                        print("✓ Connection error properly returned as 502")
                        return True
                        
                elif response.content_type == "text/event-stream":
                    print("Received streaming response:")
                    error_found = False
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str and not line_str.startswith(":"):
                            print(f"  {line_str}")
                            if "connection_error" in line_str or "Connection to upstream" in line_str:
                                print("✓ Connection error properly detected in stream")
                                error_found = True
                                break
                    return error_found
                    
        except asyncio.TimeoutError:
            print("✓ Request properly timed out")
            return True
        except Exception as e:
            print(f"Error: {e}")
            
    return False

async def test_anthropic_messages_endpoint():
    """Test the /v1/messages endpoint connection handling."""
    print("\nTesting /v1/messages endpoint connection handling...")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "claude-3-sonnet-20240229",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100
        }
        
        try:
            async with session.post(
                f"{PROXY_BASE_URL}/v1/messages",
                json=payload,
                headers={"Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            ) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 502:
                    content = await response.json()
                    if "connection" in str(content).lower():
                        print("✓ Connection error properly returned as 502")
                        return True
                        
                elif response.content_type == "text/event-stream":
                    print("Received streaming response:")
                    error_found = False
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str and not line_str.startswith(":"):
                            print(f"  {line_str}")
                            if "connection_error" in line_str or "Connection to upstream" in line_str:
                                print("✓ Connection error properly detected in stream")
                                error_found = True
                                break
                    return error_found
                    
        except asyncio.TimeoutError:
            print("✓ Request properly timed out")
            return True  
        except Exception as e:
            print(f"Error: {e}")
            
    return False

async def test_non_streaming_timeout():
    """Test non-streaming connection timeout."""
    print("\nTesting non-streaming connection timeout...")
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False  # Explicitly non-streaming
        }
        
        try:
            async with session.post(
                f"{PROXY_BASE_URL}/v1/chat/completions", 
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
            ) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 502:
                    content = await response.json()
                    print(f"Response content: {content}")
                    if "connection" in str(content).lower():
                        print("✓ Connection error properly returned as 502")
                        return True
                else:
                    content = await response.text()
                    print(f"Response content: {content[:200]}...")
                    
        except asyncio.TimeoutError:
            print("✓ Request properly timed out")
            return True
        except Exception as e:
            print(f"Error: {e}")
            
    return False

async def main():
    """Run all connection handling tests."""
    print("Starting connection handling tests...")
    print("=" * 50)
    
    tests = [
        ("Invalid Upstream", test_invalid_upstream),
        ("Streaming Timeout", test_streaming_timeout), 
        ("Messages Endpoint", test_anthropic_messages_endpoint),
        ("Non-Streaming Timeout", test_non_streaming_timeout)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            time.sleep(1)  # Brief pause between tests
        except Exception as e:
            print(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL" 
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All connection handling tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the proxy configuration and upstream connectivity.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())