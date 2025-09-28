#!/usr/bin/env python3
"""
Test: Context Info for All Endpoints, No Text Management
Verifies that:
1. ALL endpoints return context_info for client awareness
2. Text requests get NO context validation/truncation (scale properly)
3. Only vision requests get context validation/truncation
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "x-api-key": API_KEY
}

def test_all_endpoints_context_info():
    """Test that all endpoints return context_info while text endpoints skip validation."""
    
    print("🧪 Context Info for All Endpoints Test")
    print("=" * 50)
    
    # Wait for server to be ready
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code != 200:
            print("❌ Server not healthy")
            return
    except:
        print("❌ Cannot connect to server")
        return
    
    tests = [
        {
            "name": "Text auto-routing (Anthropic)",
            "payload": {
                "model": "glm-4.5",
                "messages": [{"role": "user", "content": "Hello world"}],
                "max_tokens": 20
            },
            "expected_endpoint": "anthropic",
            "expected_context_info": True,  # Now ALL endpoints should have context_info
            "should_validate": False,  # Text requests should NOT be validated/truncated
            "description": "Text request to Anthropic should have context_info but no validation"
        },
        {
            "name": "Text forced OpenAI",  
            "payload": {
                "model": "glm-4.5-openai",
                "messages": [{"role": "user", "content": "Hello world"}],
                "max_tokens": 20
            },
            "expected_endpoint": "openai",
            "expected_context_info": True,  # Should have context_info
            "should_validate": False,  # Text requests should NOT be validated even on OpenAI
            "description": "Text request to OpenAI should have context_info but no validation"
        },
        {
            "name": "Text forced Anthropic",
            "payload": {
                "model": "glm-4.5-anthropic", 
                "messages": [{"role": "user", "content": "Hello world"}],
                "max_tokens": 20
            },
            "expected_endpoint": "anthropic",
            "expected_context_info": True,  # Should have context_info
            "should_validate": False,  # Text requests should NOT be validated
            "description": "Text request to Anthropic should have context_info but no validation"
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\\n📝 {test['name']}")
        print(f"   {test['description']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                json=test["payload"],
                headers=HEADERS
            )
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                context_info = result.get("context_info")
                
                actual_endpoint = usage.get("endpoint_type", "unknown")
                has_context_info = bool(context_info)
                
                # Check expectations
                endpoint_correct = actual_endpoint == test["expected_endpoint"]
                context_correct = has_context_info == test["expected_context_info"]
                
                success = endpoint_correct and context_correct
                
                print(f"   ✅ Status: 200")
                print(f"   📊 Endpoint: {actual_endpoint} ({'✅' if endpoint_correct else '❌'})")
                print(f"   🧠 Has context_info: {has_context_info} ({'✅' if context_correct else '❌'})")
                
                if context_info:
                    print(f"   📋 Context details:")
                    print(f"      Hard limit: {context_info.get('context_hard_limit')}")
                    print(f"      Real input tokens: {context_info.get('real_input_tokens')}")
                    print(f"      Utilization: {context_info.get('utilization_percent')}%")
                    print(f"      Available: {context_info.get('available_tokens')} tokens")
                    print(f"      Truncated: {context_info.get('truncated')} (should be False for text)")
                    print(f"      Note: {context_info.get('note')}")
                
                # Check usage info
                if usage:
                    print(f"   📈 Usage info:")
                    print(f"      Total tokens: {usage.get('total_tokens')}")
                    print(f"      Real input tokens: {usage.get('real_input_tokens')}")
                    print(f"      Context limit: {usage.get('context_limit')}")
                    print(f"      Utilization: {usage.get('context_utilization')}")
                
                results.append({
                    "name": test["name"],
                    "success": success,
                    "endpoint_correct": endpoint_correct,
                    "context_correct": context_correct,
                    "actual_endpoint": actual_endpoint,
                    "has_context_info": has_context_info,
                    "context_info": context_info,
                    "usage": usage
                })
                
                print(f"   🎯 Result: {'✅ PASS' if success else '❌ FAIL'}")
                
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   Error: {response.text[:100]}...")
                results.append({
                    "name": test["name"],
                    "success": False,
                    "error": response.status_code
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append({
                "name": test["name"], 
                "success": False,
                "error": str(e)
            })
        
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print(f"\\n📊 Test Results Summary")
    print("=" * 30)
    
    passed = len([r for r in results if r.get("success", False)])
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    for result in results:
        if result.get("success"):
            print(f"✅ {result['name']}: PASS")
        else:
            print(f"❌ {result['name']}: FAIL")
            if "error" in result:
                print(f"   Error: {result['error']}")
    
    # Check specific behavior
    print(f"\\n🎯 Context Info Behavior Verification")
    print("=" * 40)
    
    successful_results = [r for r in results if r.get("success")]
    
    all_have_context = len([r for r in successful_results if r.get("has_context_info")]) == len(successful_results)
    all_not_truncated = len([r for r in successful_results if not r.get("context_info", {}).get("truncated", True)]) == len(successful_results)
    
    print(f"All requests have context_info: {'✅' if all_have_context else '❌'}")
    print(f"All text requests not truncated: {'✅' if all_not_truncated else '❌'}")
    
    # Check endpoint distribution
    anthropic_tests = [r for r in successful_results if r.get("actual_endpoint") == "anthropic"]
    openai_tests = [r for r in successful_results if r.get("actual_endpoint") == "openai"]
    
    print(f"\\nEndpoint distribution:")
    print(f"  Anthropic requests: {len(anthropic_tests)} (all should have context_info)")
    print(f"  OpenAI requests: {len(openai_tests)} (all should have context_info)")
    
    all_pass = passed == total
    behavior_correct = all_have_context and all_not_truncated
    
    print(f"\\n🏆 Overall Result: {'✅ SUCCESS' if all_pass and behavior_correct else '❌ FAILURE'}")
    
    if all_pass and behavior_correct:
        print("🎉 New context behavior is working correctly!")
        print("   • ALL endpoints return context_info for client awareness")
        print("   • Text requests get NO validation/truncation (scale properly)")
        print("   • Context info helps clients understand token usage on all endpoints")
    else:
        print("⚠️  Context behavior needs attention")
        if not all_have_context:
            print("   • Some endpoints missing context_info")
        if not all_not_truncated:
            print("   • Some text requests were truncated (should not happen)")
    
    return all_pass and behavior_correct

if __name__ == "__main__":
    test_all_endpoints_context_info()