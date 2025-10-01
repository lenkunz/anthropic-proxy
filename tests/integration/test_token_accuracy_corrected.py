#!/usr/bin/env python3
"""
Token Count Accuracy Test - Corrected Version

Tests direct model calls with glm-4.5 and compares tiktoken input token count 
with actual usage returned by the upstream API.

Key findings from logs:
- Anthropic endpoint (glm-4.5 non-streaming) DOES return usage tokens
- OpenAI endpoint (streaming) does NOT return usage tokens  
- glm-4.5-anthropic model is NOT supported by upstream
"""

import requests
import json
import tiktoken
from dotenv import load_dotenv
import os
import time

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def get_tiktoken_count(text, model="gpt-3.5-turbo"):
    """Get tiktoken count for text"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        print(f"⚠️  tiktoken error: {e}")
        # Fallback to rough estimation
        return int(len(text.split()) * 1.3)

def format_message_for_tiktoken(messages, system=None):
    """Format messages for tiktoken counting similar to how the proxy does it"""
    formatted_text = ""
    
    if system:
        formatted_text += f"System: {system}\n"
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        # Handle both string and list content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            content = " ".join(text_parts)
        
        formatted_text += f"{role.capitalize()}: {content}\n"
    
    return formatted_text

def test_direct_model_call(test_name, payload):
    """Test a direct model call and analyze token usage"""
    print(f"\n🧪 Testing: {test_name}")
    print("-" * 60)
    
    # Calculate tiktoken estimate
    messages = payload.get("messages", [])
    system = payload.get("system")
    formatted_text = format_message_for_tiktoken(messages, system)
    
    tiktoken_estimate = get_tiktoken_count(formatted_text)
    print(f"📊 tiktoken estimate: {tiktoken_estimate} tokens")
    print(f"📝 Input text: '{formatted_text.strip()}'")
    print(f"📏 Input length: {len(formatted_text)} chars")
    
    # Show routing info
    model = payload.get("model", "unknown")
    stream = payload.get("stream", False)
    print(f"🔀 Model: {model} | Stream: {stream}")
    
    # Make API call
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        print(f"⏱️  Response time: {elapsed:.2f}s")
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract usage information
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0) if usage else 0
            completion_tokens = usage.get("completion_tokens", 0) if usage else 0
            total_tokens = usage.get("total_tokens", 0) if usage else 0
            
            print(f"✅ API Success!")
            print(f"📈 API Usage Response:")
            print(f"   • Raw usage object: {usage}")
            print(f"   • Prompt tokens: {prompt_tokens}")
            print(f"   • Completion tokens: {completion_tokens}")
            print(f"   • Total tokens: {total_tokens}")
            
            # Calculate accuracy if we have actual usage
            if prompt_tokens > 0:
                accuracy = (tiktoken_estimate / prompt_tokens) * 100
                diff = abs(tiktoken_estimate - prompt_tokens)
                print(f"🎯 Token Count Analysis:")
                print(f"   • tiktoken estimate: {tiktoken_estimate}")
                print(f"   • API actual usage: {prompt_tokens}")
                print(f"   • Difference: {diff} tokens ({diff/prompt_tokens*100:.1f}%)")
                print(f"   • Accuracy: {accuracy:.1f}%")
                
                if 85 <= accuracy <= 115:
                    print("   ✅ Excellent accuracy (85-115%)")
                elif 70 <= accuracy <= 130:
                    print("   ⚠️  Good accuracy (70-130%)")
                else:
                    print("   ❌ Poor accuracy (<70% or >130%)")
            else:
                print("   ⚠️  No token usage returned (expected for streaming)")
            
            # Show response content (truncated)
            content = result.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "")[:100]
                print(f"💬 Response preview: {text_content}...")
            
            return {
                "success": True,
                "tiktoken_estimate": tiktoken_estimate,
                "api_prompt_tokens": prompt_tokens,
                "api_completion_tokens": completion_tokens,
                "api_total_tokens": total_tokens,
                "accuracy": (tiktoken_estimate / prompt_tokens * 100) if prompt_tokens > 0 else 0,
                "response_time": elapsed,
                "has_usage": prompt_tokens > 0
            }
            
        else:
            print(f"❌ API Error: {response.status_code}")
            error_text = response.text[:500]
            print(f"📄 Error response: {error_text}")
            return {"success": False, "error": error_text}
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {"success": False, "error": str(e)}

def run_corrected_token_tests():
    """Run corrected token counting tests focusing on glm-4.5"""
    print("🔍 Token Count Accuracy Test - Corrected Version")
    print("=" * 55)
    print("Based on log analysis:")
    print("• glm-4.5 (non-streaming) → Anthropic endpoint → Returns usage ✓")
    print("• glm-4.5 (streaming) → OpenAI endpoint → No usage ✗")
    print("• glm-4.5-openai → OpenAI endpoint → No usage ✗")  
    print("• glm-4.5-anthropic → Not supported by upstream ✗")
    print()
    
    test_cases = [
        {
            "name": "glm-4.5 Non-streaming (Should have usage)",
            "payload": {
                "model": "glm-4.5",
                "max_tokens": 50,
                "stream": False,  # Non-streaming should route to Anthropic and return usage
                "messages": [
                    {"role": "user", "content": "What is 2+2? Brief answer."}
                ]
            }
        },
        {
            "name": "glm-4.5 Non-streaming with System Message",
            "payload": {
                "model": "glm-4.5", 
                "max_tokens": 100,
                "stream": False,
                "system": "You are a helpful math tutor.",
                "messages": [
                    {"role": "user", "content": "Explain what multiplication is in simple terms."}
                ]
            }
        },
        {
            "name": "glm-4.5 Streaming (No usage expected)",
            "payload": {
                "model": "glm-4.5",
                "max_tokens": 30,
                "stream": True,  # Streaming routes to OpenAI, no usage returned
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        },
        {
            "name": "glm-4.5-openai Non-streaming (No usage expected)",
            "payload": {
                "model": "glm-4.5-openai",  # Forced OpenAI routing
                "max_tokens": 50,
                "stream": False,
                "messages": [
                    {"role": "user", "content": "Count to 3."}
                ]
            }
        },
        {
            "name": "Complex Multi-part Content (Non-streaming)",
            "payload": {
                "model": "glm-4.5",
                "max_tokens": 80,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "I have a question about"},
                            {"type": "text", "text": "token counting accuracy in API calls."}
                        ]
                    }
                ]
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        result = test_direct_model_call(test_case["name"], test_case["payload"])
        result["test_name"] = test_case["name"]
        results.append(result)
        
        # Brief pause between tests
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 55)
    print("📊 CORRECTED TEST RESULTS SUMMARY")
    print("=" * 55)
    
    successful_tests = [r for r in results if r.get("success")]
    usage_tests = [r for r in successful_tests if r.get("has_usage")]
    
    print(f"✅ Successful API calls: {len(successful_tests)}/{len(results)}")
    print(f"📈 Tests with usage data: {len(usage_tests)}/{len(successful_tests)}")
    
    if usage_tests:
        avg_accuracy = sum(r.get("accuracy", 0) for r in usage_tests) / len(usage_tests)
        avg_response_time = sum(r.get("response_time", 0) for r in usage_tests) / len(usage_tests)
        
        print(f"🎯 Token accuracy average: {avg_accuracy:.1f}%")
        print(f"⏱️  Average response time: {avg_response_time:.2f}s")
        
        print(f"\n📋 Usage-Enabled Tests:")
        for result in usage_tests:
            name = result.get("test_name", "Unknown")
            accuracy = result.get("accuracy", 0)
            tiktoken_est = result.get("tiktoken_estimate", 0)
            api_actual = result.get("api_prompt_tokens", 0)
            
            print(f"   • {name}")
            print(f"     tiktoken: {tiktoken_est} | API: {api_actual} | Accuracy: {accuracy:.1f}%")
    
    print(f"\n⚠️  Tests without usage (expected for streaming/OpenAI endpoint):")
    no_usage_tests = [r for r in successful_tests if not r.get("has_usage")]
    for result in no_usage_tests:
        name = result.get("test_name", "Unknown")
        print(f"   • {name}")
    
    failed_tests = [r for r in results if not r.get("success")]
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for result in failed_tests:
            name = result.get("test_name", "Unknown")
            error = result.get("error", "Unknown error")[:100]
            print(f"   • {name}: {error}")

def main():
    # Check service availability
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ Anthropic Proxy not running. Start with: docker compose up -d")
            return
    except:
        print("❌ Cannot connect to Anthropic Proxy. Start with: docker compose up -d")
        return
    
    print("🚀 Anthropic Proxy is running!")
    
    # Run the corrected tests
    run_corrected_token_tests()
    
    print("\n" + "=" * 55)
    print("🎯 KEY FINDINGS:")
    print("   ✅ glm-4.5 non-streaming returns accurate token usage")
    print("   ⚠️  Streaming and OpenAI-forced requests don't return usage")
    print("   📊 tiktoken estimates can be validated against non-streaming calls")
    print("   🔍 Use non-streaming glm-4.5 calls for token accuracy testing")

if __name__ == "__main__":
    main()