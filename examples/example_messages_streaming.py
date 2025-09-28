#!/usr/bin/env python3
"""
Example script demonstrating the /v1/messages endpoint with both streaming and non-streaming modes.

This script shows how to use the fixed /v1/messages endpoint that now properly handles:
- Non-streaming requests (stream=false or omitted) → Returns JSON response
- Streaming requests (stream=true) → Returns Server-Sent Events (SSE)

This fix resolves the "Cannot read properties of undefined (reading 'map')" error
that occurred when Claude CLI and other clients tried to parse streaming responses
as JSON.
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path and load environment from project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")
import os
import sys
from dotenv import load_dotenv
from typing import Dict, Any, Optional

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
API_KEY = os.getenv("SERVER_API_KEY")

if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    print("Please ensure you have a .env file with SERVER_API_KEY=your_api_key_here")
    sys.exit(1)

def print_separator(title: str):
    """Print a formatted separator"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_non_streaming_request():
    """Test non-streaming /v1/messages request (default behavior)"""
    print_separator("NON-STREAMING /v1/messages REQUEST")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello! Please tell me a short joke."}
        ]
        # Note: stream=false is the default, so we don't need to specify it
    }
    
    print(f"🔗 URL: {BASE_URL}/v1/messages")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print(f"📋 Expected: JSON response with Content-Type: application/json")
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/v1/messages", json=payload, headers=headers)
        elapsed_time = time.time() - start_time
        
        print(f"\n📥 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Time: {elapsed_time:.2f}s")
        print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
        print(f"   Content-Length: {response.headers.get('content-length', 'Not specified')}")
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                print(f"\n✅ SUCCESS: Received valid JSON response")
                print(f"📋 Response JSON:")
                print(json.dumps(response_json, indent=2))
                
                # Check if it's proper Anthropic format
                if "content" in response_json and "role" in response_json:
                    print(f"✅ Proper Anthropic format detected")
                    if response_json.get("content") and len(response_json["content"]) > 0:
                        content_text = response_json["content"][0].get("text", "")
                        print(f"💬 Assistant response: {content_text}")
                else:
                    print(f"⚠️  Unexpected response format")
                    
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ ERROR: Response is not valid JSON - {e}")
                print(f"Raw response: {response.text[:500]}...")
                return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False

def test_explicit_non_streaming_request():
    """Test non-streaming /v1/messages request with explicit stream=false"""
    print_separator("EXPLICIT NON-STREAMING REQUEST (stream=false)")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "What's the capital of France?"}
        ],
        "stream": False  # Explicitly set to false
    }
    
    print(f"🔗 URL: {BASE_URL}/v1/messages")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print(f"📋 Expected: JSON response with Content-Type: application/json")
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/v1/messages", json=payload, headers=headers)
        elapsed_time = time.time() - start_time
        
        print(f"\n📥 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Time: {elapsed_time:.2f}s")
        print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                print(f"✅ SUCCESS: Received JSON response as expected")
                try:
                    response_json = response.json()
                    print(f"📋 Response JSON:")
                    print(json.dumps(response_json, indent=2))
                    return True
                except json.JSONDecodeError as e:
                    print(f"❌ ERROR: JSON decode failed - {e}")
                    return False
            else:
                print(f"❌ ERROR: Expected JSON but got {content_type}")
                print(f"Response: {response.text[:300]}...")
                return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False

def test_streaming_request():
    """Test streaming /v1/messages request"""
    print_separator("STREAMING /v1/messages REQUEST (stream=true)")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 150,
        "messages": [
            {"role": "user", "content": "Please count from 1 to 5 and explain each number."}
        ],
        "stream": True  # Enable streaming
    }
    
    print(f"🔗 URL: {BASE_URL}/v1/messages")
    print(f"📦 Payload: {json.dumps(payload, indent=2)}")
    print(f"📋 Expected: SSE stream with Content-Type: text/event-stream")
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/v1/messages", json=payload, headers=headers, stream=True)
        
        print(f"\n📥 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'text/event-stream' in content_type:
                print(f"✅ SUCCESS: Received streaming response as expected")
                print(f"\n📡 Streaming content:")
                
                chunk_count = 0
                total_content = ""
                
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        print(f"   {line}")
                        
                        # Parse SSE data
                        if line.startswith("data: "):
                            chunk_count += 1
                            data_content = line[6:]  # Remove "data: " prefix
                            if data_content.strip() and data_content != "[DONE]":
                                try:
                                    chunk_json = json.loads(data_content)
                                    if chunk_json.get("type") == "content_block_delta":
                                        delta_text = chunk_json.get("delta", {}).get("text", "")
                                        total_content += delta_text
                                except json.JSONDecodeError:
                                    pass  # Ignore malformed JSON in stream
                
                elapsed_time = time.time() - start_time
                print(f"\n✅ Streaming completed in {elapsed_time:.2f}s")
                print(f"📊 Received {chunk_count} chunks")
                if total_content:
                    print(f"💬 Reconstructed content: {total_content}")
                return True
                
            else:
                print(f"❌ ERROR: Expected SSE stream but got {content_type}")
                print(f"Response: {response.text[:300]}...")
                return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False

def test_claude_cli_compatibility():
    """Test the exact request pattern that Claude CLI uses"""
    print_separator("CLAUDE CLI COMPATIBILITY TEST")
    
    print(f"📋 This test simulates the exact request pattern that Claude CLI uses.")
    print(f"📋 Before the fix, this would cause 'Cannot read properties of undefined (reading map)' error.")
    print(f"📋 After the fix, this should return proper JSON that Claude CLI can parse.")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    # This mimics exactly what Claude CLI sends
    payload = {
        "model": "claude-3-sonnet-20240229",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello, can you help me with a simple task?"}
        ]
        # Note: Claude CLI doesn't send stream parameter, expects JSON response
    }
    
    print(f"🔗 URL: {BASE_URL}/v1/messages")
    print(f"📦 Payload (Claude CLI pattern): {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{BASE_URL}/v1/messages", json=payload, headers=headers)
        
        print(f"\n📥 Response:")
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type', 'Not specified')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            
            # Check if we get JSON (what Claude CLI expects)
            if 'application/json' in content_type:
                print(f"✅ SUCCESS: Claude CLI compatible - JSON response received")
                try:
                    response_json = response.json()
                    
                    # Verify it has the structure Claude CLI expects
                    if "content" in response_json and isinstance(response_json["content"], list):
                        print(f"✅ Response structure is compatible with Claude CLI")
                        print(f"📋 Response preview:")
                        print(json.dumps(response_json, indent=2))
                        return True
                    else:
                        print(f"⚠️  Response structure might not be fully compatible")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"❌ ERROR: JSON decode failed - {e}")
                    return False
                    
            elif 'text/event-stream' in content_type:
                print(f"❌ ERROR: Claude CLI incompatible - received streaming response instead of JSON")
                print(f"📋 This would cause the 'map()' error in Claude CLI")
                return False
            else:
                print(f"❌ ERROR: Unexpected content type: {content_type}")
                return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 TESTING /v1/messages ENDPOINT - STREAMING VS NON-STREAMING")
    print("="*80)
    print("This script tests the fix for 'Cannot read properties of undefined (reading map)' error")
    print("that occurred when clients expected JSON responses but received streaming responses.")
    print("="*80)
    
    results = {
        "non_streaming_default": False,
        "non_streaming_explicit": False,
        "streaming": False,
        "claude_cli_compatibility": False
    }
    
    # Test non-streaming (default)
    results["non_streaming_default"] = test_non_streaming_request()
    
    time.sleep(1)  # Brief pause between tests
    
    # Test non-streaming (explicit)
    results["non_streaming_explicit"] = test_explicit_non_streaming_request()
    
    time.sleep(1)  # Brief pause between tests
    
    # Test streaming
    results["streaming"] = test_streaming_request()
    
    time.sleep(1)  # Brief pause between tests
    
    # Test Claude CLI compatibility
    results["claude_cli_compatibility"] = test_claude_cli_compatibility()
    
    # Summary
    print_separator("TEST RESULTS SUMMARY")
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"✅ The /v1/messages endpoint correctly handles both streaming and non-streaming requests")
        print(f"✅ Claude CLI compatibility is restored - no more 'map()' errors")
        print(f"✅ Both Anthropic format responses and SSE streaming work as expected")
    else:
        failed_tests = [name for name, passed in results.items() if not passed]
        print(f"\n❌ SOME TESTS FAILED: {', '.join(failed_tests)}")
        print(f"Please check the proxy configuration and server status")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)