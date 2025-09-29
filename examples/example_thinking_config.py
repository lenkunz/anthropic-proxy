#!/usr/bin/env python3
"""
Example: Testing Different Thinking Parameter Configurations
Demonstrates how to test the proxy with different ENABLE_ZAI_THINKING settings.

This example shows how the thinking parameter affects:
1. OpenAI endpoint requests (where thinking is added)
2. Anthropic endpoint requests (where thinking is NOT added)
3. How to verify the configuration is working

Usage:
1. Set ENABLE_ZAI_THINKING=true in your .env file
2. Restart proxy: docker compose down && docker compose up -d  
3. Run this script: python example_thinking_config.py
"""

import os
import json
import time
from dotenv import load_dotenv
import requests

# Load environment variables
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

def test_endpoint_routing():
    """Test different model variants to verify thinking parameter behavior."""
    
    print("🔍 Testing Thinking Parameter Configuration")
    print("=" * 50)
    
    # Test data: model variant -> expected endpoint -> should have thinking
    test_cases = [
        ("glm-4.5", "Text-only auto-routing", "anthropic", False),
        ("glm-4.5-openai", "Force OpenAI routing", "openai", True),
        ("glm-4.5-anthropic", "Force Anthropic routing", "anthropic", False),
    ]
    
    results = []
    
    for model, description, expected_endpoint, should_have_thinking in test_cases:
        print(f"\n📝 Testing: {model}")
        print(f"   Description: {description}")
        print(f"   Expected endpoint: {expected_endpoint}")
        print(f"   Should have thinking parameter: {should_have_thinking}")
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello, this is a test message."}],
            "max_tokens": 50
        }
        
        try:
            response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                                   json=payload, 
                                   headers=HEADERS)
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                actual_endpoint = usage.get("endpoint_type", "unknown")
                
                # Check if endpoint matches expectation
                endpoint_correct = actual_endpoint == expected_endpoint
                
                print(f"   ✅ Request successful")
                print(f"   📊 Actual endpoint: {actual_endpoint}")
                print(f"   🎯 Endpoint correct: {'✅' if endpoint_correct else '❌'}")
                
                results.append({
                    "model": model,
                    "expected_endpoint": expected_endpoint,
                    "actual_endpoint": actual_endpoint,
                    "endpoint_correct": endpoint_correct,
                    "should_have_thinking": should_have_thinking,
                    "success": True
                })
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text}")
                results.append({
                    "model": model,
                    "success": False,
                    "error": response.text
                })
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append({
                "model": model,
                "success": False,
                "error": str(e)
            })
        
        time.sleep(1)  # Small delay for log ordering
    
    return results

def check_log_evidence():
    """Check upstream request logs for thinking parameter evidence."""
    log_file = "logs/upstream_requests.json"
    
    print(f"\n🔍 Checking {log_file} for thinking parameter evidence...")
    
    if not os.path.exists(log_file):
        print(f"❌ Log file {log_file} does not exist")
        return False
    
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-10:]  # Check last 10 entries
            
        openai_with_thinking = 0
        anthropic_without_thinking = 0
        
        for line in recent_lines:
            try:
                log_entry = json.loads(line.strip())
                endpoint_type = log_entry.get("endpoint_type", "")
                payload = log_entry.get("payload", {})
                
                # Check for thinking parameter
                has_thinking = "thinking" in payload
                
                if endpoint_type == "openai" and has_thinking:
                    openai_with_thinking += 1
                    thinking_value = payload.get("thinking", {})
                    print(f"   ✅ Found OpenAI request with thinking: {thinking_value}")
                    
                elif endpoint_type == "anthropic" and not has_thinking:
                    anthropic_without_thinking += 1
                    print(f"   ✅ Found Anthropic request without thinking (correct)")
                    
            except (json.JSONDecodeError, KeyError):
                continue
        
        print(f"\n📊 Log Analysis Results:")
        print(f"   OpenAI requests with thinking: {openai_with_thinking}")
        print(f"   Anthropic requests without thinking: {anthropic_without_thinking}")
        
        return openai_with_thinking > 0
        
    except Exception as e:
        print(f"❌ Error reading log file: {e}")
        return False

def print_configuration_help():
    """Print help information about thinking parameter configuration."""
    print(f"\n💡 Configuration Help")
    print("=" * 25)
    print("1. Environment Variable: ENABLE_ZAI_THINKING")
    print("   • Default: true")
    print("   • Controls automatic thinking parameter injection")
    print("   • Only affects OpenAI endpoint requests")
    print("")
    print("2. When ENABLE_ZAI_THINKING=true:")
    print("   • OpenAI requests get: {\"thinking\": {\"type\": \"enabled\"}}")
    print("   • Anthropic requests: no thinking parameter added")
    print("")
    print("3. Model Routing:")
    print("   • glm-4.5 (text) → Anthropic endpoint → no thinking")
    print("   • glm-4.5 (images) → OpenAI endpoint → thinking added")
    print("   • glm-4.5-openai → OpenAI endpoint → thinking added")
    print("   • glm-4.5-anthropic → Anthropic endpoint → no thinking")
    print("")
    print("4. To Disable Thinking Parameter:")
    print("   • Set ENABLE_ZAI_THINKING=false in .env")
    print("   • Restart proxy: docker compose restart")
    print("")
    print("5. Verification:")
    print("   • Check logs/upstream_requests.json for full payloads")
    print("   • OpenAI requests should include thinking parameter")
    print("   • Anthropic requests should NOT include thinking parameter")

def main():
    """Run the configuration test."""
    
    # Check proxy health first
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code != 200:
            print("❌ Proxy is not healthy")
            return
    except:
        print("❌ Cannot connect to proxy. Is it running?")
        return
    
    print("🧠 z.ai Thinking Parameter Configuration Test")
    print("=" * 50)
    
    # Get current ENABLE_ZAI_THINKING setting
    thinking_enabled = os.getenv("ENABLE_ZAI_THINKING", "true").lower() in ("true", "1", "yes")
    print(f"Current ENABLE_ZAI_THINKING setting: {thinking_enabled}")
    
    # Test endpoint routing
    results = test_endpoint_routing()
    
    # Check logs for evidence
    found_thinking = check_log_evidence()
    
    # Summary
    print(f"\n📋 Test Summary")
    print("=" * 20)
    successful_tests = len([r for r in results if r.get("success")])
    total_tests = len(results)
    
    print(f"Successful tests: {successful_tests}/{total_tests}")
    
    if found_thinking:
        print("✅ Thinking parameter evidence found in logs")
    else:
        print("ℹ️  No thinking parameter evidence in recent logs")
    
    if thinking_enabled and found_thinking:
        print("🎉 Configuration appears to be working correctly!")
    elif not thinking_enabled:
        print("ℹ️  Thinking parameter is disabled (ENABLE_ZAI_THINKING=false)")
    else:
        print("⚠️  Configuration may need attention")
    
    # Print configuration help
    print_configuration_help()

if __name__ == "__main__":
    main()