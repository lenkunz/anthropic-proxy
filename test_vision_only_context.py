#!/usr/bin/env python3
"""
Test: Vision-Only Context Management
Verifies that context management only applies to vision/OpenAI endpoint requests.
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

def test_context_management():
    """Test that context management only applies to vision requests."""
    
    print("🧪 Vision-Only Context Management Test")
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
            "name": "Text-only to Anthropic",
            "payload": {
                "model": "glm-4.5",
                "messages": [{"role": "user", "content": "Hello world"}],
                "max_tokens": 20
            },
            "expected_endpoint": "anthropic",
            "expected_context_info": False,
            "description": "Auto-routing text request should go to Anthropic without context management"
        },
        {
            "name": "Force OpenAI text",  
            "payload": {
                "model": "glm-4.5-openai",
                "messages": [{"role": "user", "content": "Hello world"}],
                "max_tokens": 20
            },
            "expected_endpoint": "openai",
            "expected_context_info": True,
            "description": "Forced OpenAI text request should have context management"
        },
        {
            "name": "Force Anthropic text",
            "payload": {
                "model": "glm-4.5-anthropic", 
                "messages": [{"role": "user", "content": "Hello world"}],
                "max_tokens": 20
            },
            "expected_endpoint": "anthropic",
            "expected_context_info": False,
            "description": "Forced Anthropic text request should not have context management"
        }
    ]
    
    results = []
    
    for test in tests:
        print(f"\n📝 {test['name']}")
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
                print(f"   🧠 Context info: {has_context_info} ({'✅' if context_correct else '❌'})")
                
                if context_info:
                    print(f"   📋 Context details:")
                    print(f"      Hard limit: {context_info.get('context_hard_limit')}")
                    print(f"      Utilization: {context_info.get('utilization_percent')}%")
                    print(f"      Available: {context_info.get('available_tokens')} tokens")
                
                results.append({
                    "name": test["name"],
                    "success": success,
                    "endpoint_correct": endpoint_correct,
                    "context_correct": context_correct,
                    "actual_endpoint": actual_endpoint,
                    "has_context_info": has_context_info
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
    print(f"\n📊 Test Results Summary")
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
    print(f"\n🎯 Vision-Only Context Management Verification")
    print("=" * 50)
    
    anthropic_tests = [r for r in results if r.get("success") and r.get("actual_endpoint") == "anthropic"]
    openai_tests = [r for r in results if r.get("success") and r.get("actual_endpoint") == "openai"]
    
    print(f"Anthropic endpoint requests: {len(anthropic_tests)}")
    anthropic_no_context = len([r for r in anthropic_tests if not r.get("has_context_info")])
    print(f"  Without context info: {anthropic_no_context}/{len(anthropic_tests)} {'✅' if anthropic_no_context == len(anthropic_tests) else '❌'}")
    
    print(f"OpenAI endpoint requests: {len(openai_tests)}")
    openai_has_context = len([r for r in openai_tests if r.get("has_context_info")])
    print(f"  With context info: {openai_has_context}/{len(openai_tests)} {'✅' if openai_has_context == len(openai_tests) else '❌'}")
    
    all_pass = passed == total
    behavior_correct = (anthropic_no_context == len(anthropic_tests) and 
                       openai_has_context == len(openai_tests))
    
    print(f"\n🏆 Overall Result: {'✅ SUCCESS' if all_pass and behavior_correct else '❌ FAILURE'}")
    
    if all_pass and behavior_correct:
        print("🎉 Vision-only context management is working correctly!")
        print("   • Text requests to Anthropic: No context management")
        print("   • Requests to OpenAI endpoint: Context management enabled")
    else:
        print("⚠️  Context management behavior needs attention")
    
    return all_pass and behavior_correct

if __name__ == "__main__":
    test_context_management()