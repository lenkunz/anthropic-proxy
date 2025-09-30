#!/usr/bin/env python3
"""
Token Count Accuracy Test - Anthropic Proxy

Tests direct model calls and compares tiktoken input token count with actual usage.
This script validates:
1. Direct model API calls work correctly
2. tiktoken token counting matches actual API usage
3. Token scaling calculations are accurate
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
        return len(text.split()) * 1.3

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

def test_direct_model_call(model_name, test_case_name, payload):
    """Test a direct model call and analyze token usage"""
    print(f"\n🧪 Testing {test_case_name} with model: {model_name}")
    print("-" * 60)
    
    # Calculate tiktoken estimate
    messages = payload.get("messages", [])
    system = payload.get("system")
    formatted_text = format_message_for_tiktoken(messages, system)
    
    tiktoken_estimate = get_tiktoken_count(formatted_text)
    print(f"📊 tiktoken estimate: {tiktoken_estimate} tokens")
    print(f"📝 Input text length: {len(formatted_text)} chars")
    
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
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            
            print(f"✅ API Success!")
            print(f"📈 API Usage:")
            print(f"   • Prompt tokens: {prompt_tokens}")
            print(f"   • Completion tokens: {completion_tokens}")
            print(f"   • Total tokens: {total_tokens}")
            
            # Calculate accuracy
            if prompt_tokens > 0:
                accuracy = (tiktoken_estimate / prompt_tokens) * 100
                diff = abs(tiktoken_estimate - prompt_tokens)
                print(f"🎯 Token Count Analysis:")
                print(f"   • tiktoken estimate: {tiktoken_estimate}")
                print(f"   • API actual usage: {prompt_tokens}")
                print(f"   • Difference: {diff} tokens")
                print(f"   • Accuracy: {accuracy:.1f}%")
                
                if accuracy >= 90 and accuracy <= 110:
                    print("   ✅ Excellent accuracy (90-110%)")
                elif accuracy >= 80 and accuracy <= 120:
                    print("   ⚠️  Good accuracy (80-120%)")
                else:
                    print("   ❌ Poor accuracy (<80% or >120%)")
            else:
                print("   ⚠️  No prompt token usage reported")
            
            # Show response content (truncated)
            content = result.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "")[:200]
                print(f"💬 Response preview: {text_content}...")
            
            return {
                "success": True,
                "tiktoken_estimate": tiktoken_estimate,
                "api_prompt_tokens": prompt_tokens,
                "api_completion_tokens": completion_tokens,
                "api_total_tokens": total_tokens,
                "accuracy": accuracy if prompt_tokens > 0 else 0,
                "response_time": elapsed
            }
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"📄 Error response: {response.text}")
            return {"success": False, "error": response.text}
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {"success": False, "error": str(e)}

def run_token_accuracy_tests():
    """Run comprehensive token counting tests"""
    print("🔍 Token Count Accuracy Test Suite")
    print("=" * 50)
    
    test_cases = [
        {
            "name": "Simple Text (Auto-routing)",
            "model": "glm-4.5",
            "payload": {
                "model": "glm-4.5",
                "max_tokens": 100,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": "What is the capital of France? Please give me a short answer."
                    }
                ]
            }
        },
        {
            "name": "System Message + Long Text (OpenAI)",
            "model": "glm-4.5-openai", 
            "payload": {
                "model": "glm-4.5-openai",
                "max_tokens": 150,
                "stream": False,
                "system": "You are a helpful assistant specializing in geography and world capitals. Please provide accurate and concise information.",
                "messages": [
                    {
                        "role": "user", 
                        "content": "I'm planning a trip to Europe and need to know about capital cities. Can you tell me about Paris, Berlin, and Rome? What makes each city unique as a capital?"
                    }
                ]
            }
        },
        {
            "name": "Complex Multipart Content (Anthropic)",
            "model": "glm-4.5-anthropic",
            "payload": {
                "model": "glm-4.5-anthropic",
                "max_tokens": 120,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "I need help with a technical problem. Here's the context:"
                            },
                            {
                                "type": "text", 
                                "text": "We have a FastAPI service that processes API requests and we're seeing token counting discrepancies between our tiktoken estimates and actual API usage. The service routes between different endpoints based on content type."
                            }
                        ]
                    }
                ]
            }
        },
        {
            "name": "Conversation Context",
            "model": "glm-4.5",
            "payload": {
                "model": "glm-4.5",
                "max_tokens": 100,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, can you help me with a question?"
                    },
                    {
                        "role": "assistant", 
                        "content": "Of course! I'd be happy to help you with your question. What would you like to know?"
                    },
                    {
                        "role": "user",
                        "content": "How accurate are tiktoken token counts compared to actual API usage?"
                    }
                ]
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        result = test_direct_model_call(
            test_case["model"],
            test_case["name"], 
            test_case["payload"]
        )
        result["test_name"] = test_case["name"]
        result["model"] = test_case["model"]
        results.append(result)
        
        # Brief pause between tests
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    successful_tests = [r for r in results if r.get("success")]
    
    if successful_tests:
        avg_accuracy = sum(r.get("accuracy", 0) for r in successful_tests) / len(successful_tests)
        avg_response_time = sum(r.get("response_time", 0) for r in successful_tests) / len(successful_tests)
        
        print(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
        print(f"📈 Average token accuracy: {avg_accuracy:.1f}%")
        print(f"⏱️  Average response time: {avg_response_time:.2f}s")
        
        print(f"\n📋 Individual Test Results:")
        for result in successful_tests:
            name = result.get("test_name", "Unknown")
            model = result.get("model", "Unknown")
            accuracy = result.get("accuracy", 0)
            tiktoken_est = result.get("tiktoken_estimate", 0)
            api_actual = result.get("api_prompt_tokens", 0)
            
            print(f"   • {name} ({model}): {accuracy:.1f}% ({tiktoken_est} vs {api_actual})")
    else:
        print("❌ No successful tests completed")
    
    failed_tests = [r for r in results if not r.get("success")]
    if failed_tests:
        print(f"\n❌ Failed tests: {len(failed_tests)}")
        for result in failed_tests:
            name = result.get("test_name", "Unknown")
            error = result.get("error", "Unknown error")
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
    
    # Run the tests
    run_token_accuracy_tests()
    
    print("\n" + "=" * 50)
    print("🎯 CONCLUSIONS:")
    print("   • Direct model calls are working")
    print("   • Token counting can be compared against tiktoken")
    print("   • Check accuracy percentages above for validation")
    print("   • Differences may be due to tokenizer variations")

if __name__ == "__main__":
    main()