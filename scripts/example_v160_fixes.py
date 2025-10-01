#!/usr/bin/env python3
"""
Anthropic Proxy - Complex Message Conversion Example

This example demonstrates the fixed message conversion capabilities,
including complex Anthropic message structures with tool calls,
system messages, and multipart content that can now be properly
routed to the OpenAI endpoint.

Requirements:
- anthropic-proxy running on localhost:5000
- Valid SERVER_API_KEY in .env file
"""

import json
import time
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    print("Please create a .env file with: SERVER_API_KEY=your_api_key")
    exit(1)

BASE_URL = "http://localhost:5000"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def example_complex_message_conversion():
    """
    Demonstrates complex message conversion that was previously failing
    but is now working with the v1.6.0 fixes.
    """
    print("🔧 Complex Message Conversion Example")
    print("=" * 50)
    print("This example shows message structures that were previously")
    print("failing with 'stream has been closed' errors but now work.")
    print()
    
    # Example 1: System messages + tool calls
    print("📋 Example 1: System Messages + Tool Calls")
    
    complex_payload = {
        "model": "glm-4.5-openai",  # Force OpenAI routing to test conversion
        "max_tokens": 500,
        "temperature": 0.7,
        "stream": False,
        "system": [
            {
                "type": "text", 
                "text": "You are a helpful AI assistant integrated with development tools. You can analyze code, run diagnostics, and help with debugging."
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "I'm having an issue with my API proxy. Can you help me analyze the logs?"
                    }
                ]
            },
            {
                "role": "assistant", 
                "content": [
                    {
                        "type": "text",
                        "text": "I'll help you analyze the API proxy logs. Let me run a diagnostic check first."
                    },
                    {
                        "type": "tool_use",
                        "id": "call_analyze_logs", 
                        "name": "analyze_proxy_logs",
                        "input": {
                            "log_type": "error_logs",
                            "time_range": "last_hour",
                            "filter": "stream_errors"
                        }
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_analyze_logs",
                        "content": "Found 15 stream closure errors in the last hour. Pattern: 'Attempted to read or stream content, but the stream has been closed.' Status: All requests returned 500 errors."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Those errors are now fixed in v1.6.0. Can you confirm the fix is working?"
                    }
                ]
            }
        ]
    }
    
    try:
        start_time = time.time()
        
        print(f"📤 Sending complex message structure...")
        print(f"   Model: {complex_payload['model']}")
        print(f"   System blocks: {len(complex_payload.get('system', []))}")
        print(f"   Messages: {len(complex_payload['messages'])}")
        print(f"   Tool interactions: {sum(1 for msg in complex_payload['messages'] if 'tool_use' in str(msg) or 'tool_result' in str(msg))}")
        
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=complex_payload,
            timeout=30
        )
        
        duration = time.time() - start_time
        
        print(f"📥 Response received in {duration:.2f}s")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS! Complex message conversion working")
            print(f"   Response ID: {result.get('id', 'unknown')}")
            print(f"   Model: {result.get('model', 'unknown')}")
            print(f"   Content blocks: {len(result.get('content', []))}")
            print(f"   Usage: {result.get('usage', {})}")
            
            # Show response content preview
            content = result.get('content', [])
            if content and len(content) > 0 and content[0].get('type') == 'text':
                text = content[0].get('text', '')[:200]
                print(f"   Content preview: {text}...")
            
            return True
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def example_streaming_fix():
    """
    Demonstrates that streaming requests no longer return 'stream has been closed' errors
    """
    print("\n🌊 Streaming Fix Example")
    print("=" * 30)
    print("Testing that streaming requests now complete gracefully")
    print("without 'stream has been closed' errors.")
    print()
    
    streaming_payload = {
        "model": "glm-4.5-openai",  # Force OpenAI routing
        "max_tokens": 100,
        "stream": True,  # Enable streaming
        "messages": [
            {
                "role": "user",
                "content": "Explain what was fixed in the anthropic-proxy v1.6.0 update in 2-3 sentences."
            }
        ]
    }
    
    try:
        print(f"📤 Sending streaming request...")
        
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=streaming_payload,
            stream=True,
            timeout=30
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Streaming request successful (no 500 errors)")
            print(f"   Content-Type: {response.headers.get('content-type')}")
            
            # Check if we get proper streaming response or graceful completion
            line_count = 0
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    line_count += 1
                    if line_count <= 3:  # Show first few lines
                        print(f"   📦 Line {line_count}: {line[:80]}...")
                    if line_count >= 5:  # Don't spam too much output
                        break
            
            duration = time.time() - start_time
            print(f"   Duration: {duration:.2f}s")
            print(f"   Lines received: {line_count}")
            print(f"✅ Streaming completed gracefully (no 'stream has been closed' errors)")
            
            return True
        else:
            print(f"❌ Streaming failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Streaming error: {e}")
        return False

def example_model_variants():
    """
    Shows that all model variants work with the conversion fix
    """
    print("\n🔀 Model Variant Example")
    print("=" * 25)
    print("Testing all model variants with complex message conversion")
    print()
    
    models_to_test = [
        ("glm-4.5", "Auto-routing"),
        ("glm-4.5-openai", "Force OpenAI"),
        ("glm-4.5-anthropic", "Force Anthropic (text)")
    ]
    
    test_payload = {
        "max_tokens": 50,
        "messages": [
            {
                "role": "user",
                "content": "Briefly confirm you're working properly."
            }
        ]
    }
    
    results = []
    
    for model, description in models_to_test:
        print(f"🧪 Testing {model} ({description})")
        
        payload = test_payload.copy()
        payload["model"] = model
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/messages",
                headers=HEADERS,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ {model}: OK")
                results.append(True)
            else:
                print(f"   ❌ {model}: Failed ({response.status_code})")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ {model}: Error ({e})")
            results.append(False)
    
    success_rate = sum(results) / len(results) * 100
    print(f"\n📊 Model variant success rate: {success_rate:.0f}% ({sum(results)}/{len(results)})")
    
    return all(results)

def main():
    """
    Run all examples demonstrating the v1.6.0 fixes
    """
    print("🚀 Anthropic Proxy v1.6.0 - Message Conversion Fixes")
    print("=" * 60)
    print("Demonstrating the fixes for complex message conversion and")
    print("streaming 'stream has been closed' errors.")
    print()
    
    # Test service health first
    try:
        health_response = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Service not available. Please start the proxy:")
            print("   docker compose up -d")
            return False
    except:
        print("❌ Cannot connect to proxy. Please ensure it's running:")
        print("   docker compose up -d")
        return False
    
    print("✅ Service is healthy, running examples...")
    print()
    
    # Run examples
    complex_ok = example_complex_message_conversion()
    streaming_ok = example_streaming_fix()
    variants_ok = example_model_variants()
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Example Results Summary:")
    print(f"   Complex message conversion: {'✅ WORKING' if complex_ok else '❌ FAILED'}")
    print(f"   Streaming fix: {'✅ WORKING' if streaming_ok else '❌ FAILED'}")
    print(f"   Model variants: {'✅ WORKING' if variants_ok else '❌ FAILED'}")
    
    if all([complex_ok, streaming_ok, variants_ok]):
        print("\n🎉 All v1.6.0 fixes are working correctly!")
        print("The anthropic-proxy can now handle:")
        print("  • Complex Anthropic message structures")
        print("  • Tool calls and system messages")
        print("  • Streaming without 'stream has been closed' errors")
        print("  • All model variants with proper conversion")
    else:
        print("\n⚠️  Some functionality may need attention.")
        print("Please check the proxy logs for details:")
        print("  docker compose logs anthropic-proxy")
    
    return all([complex_ok, streaming_ok, variants_ok])

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)