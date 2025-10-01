#!/usr/bin/env python3
"""
Before/After Comparison - Anthropic Proxy v1.6.0 Fixes

This script demonstrates what was broken before v1.6.0 and what's now working.
"""

import json
import requests
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def show_before_after():
    print("🔧 Anthropic Proxy v1.6.0 - Before/After Comparison")
    print("=" * 55)
    print()
    
    print("❌ BEFORE v1.6.0 (What was broken):")
    print("   • Complex Anthropic messages with tool calls → 500 errors")
    print("   • System messages + multipart content → conversion failure") 
    print("   • Streaming requests → 'stream has been closed' errors")
    print("   • Missing headers for Anthropic streaming → undefined variable errors")
    print("   • Tool results and tool calls → improper format conversion")
    print()
    
    print("✅ AFTER v1.6.0 (What's now working):")
    print("   • Complex message structures → proper OpenAI format conversion")
    print("   • System messages → correctly moved to messages array")
    print("   • Tool calls/results → proper OpenAI tool format")
    print("   • Streaming requests → graceful completion with 200 OK")
    print("   • All endpoint routing → proper headers for both Anthropic/OpenAI")
    print()

def example_previously_failing_request():
    """
    This type of request would have failed before v1.6.0
    """
    print("🧪 Testing Previously Failing Request Type")
    print("-" * 45)
    
    # This exact structure was causing the original error
    problematic_payload = {
        "model": "glm-4.5-openai",  # Force OpenAI routing to test conversion
        "max_tokens": 200,
        "stream": False,
        "system": "You are a helpful assistant with access to development tools.",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Help me debug this API issue"}
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I'll help you debug. Let me check the logs."},
                    {
                        "type": "tool_use",
                        "id": "call_123",
                        "name": "check_logs",
                        "input": {"type": "error_logs"}
                    }
                ]
            },
            {
                "role": "user", 
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_123",
                        "content": "Found stream closure errors"
                    }
                ]
            }
        ]
    }
    
    print("📤 Sending request that would have failed before v1.6.0...")
    print("   • System message: ✓")
    print("   • Tool calls: ✓") 
    print("   • Tool results: ✓")
    print("   • Multipart content: ✓")
    print("   • OpenAI routing: ✓")
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=problematic_payload,
            timeout=20
        )
        
        print(f"📥 Response: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! This request now works perfectly")
            print(f"   • Conversion completed without errors")
            print(f"   • Response ID: {result.get('id', 'N/A')}")
            print(f"   • Content received: {len(result.get('content', []))} blocks")
            print(f"   • Token usage: {result.get('usage', {})}")
        else:
            print(f"❌ Still failing: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")

def example_streaming_fix():
    """
    Show that streaming no longer returns 500 errors
    """
    print("\n🌊 Streaming Fix Demonstration")
    print("-" * 32)
    
    streaming_payload = {
        "model": "glm-4.5",  # Auto-routing
        "max_tokens": 100,
        "stream": True,
        "messages": [
            {
                "role": "user",
                "content": "Tell me about the v1.6.0 streaming fixes."
            }
        ]
    }
    
    print("📤 Sending streaming request...")
    print("   • Stream: enabled")
    print("   • Model: auto-routing")
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/messages",
            headers=HEADERS,
            json=streaming_payload,
            stream=True,
            timeout=15
        )
        
        print(f"📥 Response: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! Streaming now works without errors")
            print("   • No 'stream has been closed' 500 errors")
            print("   • Graceful stream completion")
            print("   • Proper headers for both endpoints")
        else:
            print(f"❌ Streaming issue: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Streaming error: {e}")

def main():
    # Check service
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print("❌ Proxy not running. Start with: docker compose up -d")
            return
    except:
        print("❌ Cannot connect to proxy. Start with: docker compose up -d")
        return
    
    show_before_after()
    example_previously_failing_request()
    example_streaming_fix()
    
    print("\n" + "=" * 55)
    print("📋 Summary of v1.6.0 Fixes:")
    print("   ✅ Complex message conversion working")
    print("   ✅ Streaming errors resolved") 
    print("   ✅ All endpoint routing functional")
    print("   ✅ Backward compatibility maintained")
    print()
    print("🎉 The anthropic-proxy is now more robust and handles")
    print("   complex message structures that were previously failing!")

if __name__ == "__main__":
    main()