#!/usr/bin/env python3
"""
OpenAI Endpoint Token Accuracy Test

Tests tiktoken accuracy specifically against the OpenAI endpoint (glm-4.5-openai)
to avoid Anthropic endpoint token scaling and get raw token counts.
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

def get_tiktoken_count(text, model="gpt-4"):
    """Get tiktoken count for text using GPT-4 encoding"""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception as e:
        print(f"⚠️  tiktoken error: {e}")
        # Fallback to cl100k_base encoding (GPT-4/ChatGPT)
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except:
            return int(len(text.split()) * 1.3)

def format_messages_for_tiktoken(messages, system=None):
    """Format messages for tiktoken counting (OpenAI chat format)"""
    formatted_text = ""
    
    if system:
        formatted_text += f"<system>{system}</system>\n"
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        # Handle both string and list content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
                elif isinstance(part, str):
                    text_parts.append(part)
            content = " ".join(text_parts)
        
        formatted_text += f"<{role}>{content}</{role}>\n"
    
    return formatted_text

def test_openai_endpoint_accuracy(test_name, payload):
    """Test OpenAI endpoint token accuracy"""
    print(f"\n🧪 Testing: {test_name}")
    print("-" * 60)
    
    # Calculate tiktoken estimate
    messages = []
    system_content = None
    
    # Handle different payload formats
    if "messages" in payload:
        messages = payload["messages"]
    if "system" in payload:
        system_content = payload["system"]
    
    formatted_text = format_messages_for_tiktoken(messages, system_content)
    tiktoken_estimate = get_tiktoken_count(formatted_text)
    
    print(f"📊 tiktoken estimate: {tiktoken_estimate} tokens")
    print(f"📝 Formatted text: '{formatted_text.strip()[:200]}...'")
    print(f"📏 Text length: {len(formatted_text)} chars")
    
    # Show routing info
    model = payload.get("model", "unknown")
    endpoint = "OpenAI (forced)" if "openai" in model else "Auto"
    print(f"🔀 Model: {model} | Endpoint: {endpoint}")
    
    # Make API call to /v1/chat/completions (OpenAI-compatible)
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
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
                print(f"   • Difference: {diff} tokens ({diff/max(prompt_tokens,1)*100:.1f}%)")
                print(f"   • Accuracy: {accuracy:.1f}%")
                
                if 90 <= accuracy <= 110:
                    print("   ✅ Excellent accuracy (90-110%)")
                elif 80 <= accuracy <= 120:
                    print("   ⚠️  Good accuracy (80-120%)")
                elif 70 <= accuracy <= 130:
                    print("   ⚠️  Fair accuracy (70-130%)")
                else:
                    print("   ❌ Poor accuracy (<70% or >130%)")
            else:
                print("   ⚠️  No token usage returned")
            
            # Show response content (truncated)
            choices = result.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", "")[:100]
                print(f"💬 Response preview: {content}...")
            
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

def run_openai_endpoint_tests():
    """Run token accuracy tests specifically on OpenAI endpoint"""
    print("🔍 OpenAI Endpoint Token Accuracy Test")
    print("=" * 50)
    print("Testing tiktoken accuracy against OpenAI endpoint only")
    print("This avoids Anthropic endpoint token scaling")
    print()
    
    test_cases = [
        {
            "name": "Simple Request (OpenAI Forced)",
            "payload": {
                "model": "glm-4.5-openai",  # Force OpenAI endpoint
                "max_tokens": 50,
                "stream": False,
                "messages": [
                    {"role": "user", "content": "What is 2+2?"}
                ]
            }
        },
        {
            "name": "With System Message (OpenAI Forced)",
            "payload": {
                "model": "glm-4.5-openai",
                "max_tokens": 100,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "You are a helpful math tutor."},
                    {"role": "user", "content": "Explain basic multiplication"}
                ]
            }
        },
        {
            "name": "Conversation Context (OpenAI Forced)",
            "payload": {
                "model": "glm-4.5-openai",
                "max_tokens": 80,
                "stream": False,
                "messages": [
                    {"role": "user", "content": "Hello there"},
                    {"role": "assistant", "content": "Hi! How can I help?"},
                    {"role": "user", "content": "Tell me about token counting"}
                ]
            }
        },
        {
            "name": "Longer Content (OpenAI Forced)",
            "payload": {
                "model": "glm-4.5-openai",
                "max_tokens": 120,
                "stream": False,
                "messages": [
                    {
                        "role": "user", 
                        "content": "I'm working on a project that involves API token counting and I need to understand how accurate different tokenization methods are compared to the actual API usage. Can you explain the key factors that affect token count accuracy?"
                    }
                ]
            }
        },
        {
            "name": "Auto-routing for comparison",
            "payload": {
                "model": "glm-4.5",  # Auto-routing (should go to OpenAI for /v1/chat/completions)
                "max_tokens": 40,
                "stream": False,
                "messages": [
                    {"role": "user", "content": "Quick test"}
                ]
            }
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        result = test_openai_endpoint_accuracy(test_case["name"], test_case["payload"])
        result["test_name"] = test_case["name"]
        results.append(result)
        
        # Brief pause between tests
        time.sleep(1)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 OPENAI ENDPOINT TEST RESULTS")
    print("=" * 50)
    
    successful_tests = [r for r in results if r.get("success")]
    usage_tests = [r for r in successful_tests if r.get("has_usage")]
    
    print(f"✅ Successful API calls: {len(successful_tests)}/{len(results)}")
    print(f"📈 Tests with usage data: {len(usage_tests)}/{len(successful_tests)}")
    
    if usage_tests:
        accuracies = [r.get("accuracy", 0) for r in usage_tests]
        avg_accuracy = sum(accuracies) / len(accuracies)
        min_accuracy = min(accuracies)
        max_accuracy = max(accuracies)
        avg_response_time = sum(r.get("response_time", 0) for r in usage_tests) / len(usage_tests)
        
        print(f"🎯 Token accuracy stats:")
        print(f"   • Average: {avg_accuracy:.1f}%")
        print(f"   • Range: {min_accuracy:.1f}% - {max_accuracy:.1f}%")
        print(f"⏱️  Average response time: {avg_response_time:.2f}s")
        
        print(f"\n📋 Detailed Results:")
        for result in usage_tests:
            name = result.get("test_name", "Unknown")
            accuracy = result.get("accuracy", 0)
            tiktoken_est = result.get("tiktoken_estimate", 0)
            api_actual = result.get("api_prompt_tokens", 0)
            
            status = "✅" if 90 <= accuracy <= 110 else "⚠️" if 70 <= accuracy <= 130 else "❌"
            print(f"   {status} {name}")
            print(f"      tiktoken: {tiktoken_est} | API: {api_actual} | Accuracy: {accuracy:.1f}%")
    
    no_usage_tests = [r for r in successful_tests if not r.get("has_usage")]
    if no_usage_tests:
        print(f"\n⚠️  Tests without usage data:")
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
    
    # Run the OpenAI endpoint tests
    run_openai_endpoint_tests()
    
    print("\n" + "=" * 50)
    print("🎯 KEY FINDINGS:")
    print("   📊 Testing tiktoken accuracy against OpenAI endpoint only")
    print("   🔍 No Anthropic endpoint token scaling interference")
    print("   📈 Direct comparison of tiktoken vs actual API usage")
    print("   💡 Use these results to validate token estimation accuracy")

if __name__ == "__main__":
    main()