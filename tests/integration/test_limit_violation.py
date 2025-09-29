#!/usr/bin/env python3
"""
Test context limit violation detection

This shows how clients can see when they're approaching or exceeding limits.
"""

import requests
import json
import os
from dotenv import load_dotenv
import tiktoken

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

def create_massive_conversation():
    """Create a conversation that definitely exceeds vision model limits"""
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    
    # Create 80K+ tokens of conversation
    for i in range(40):
        long_content = f"Message {i}: " + "This is a very detailed explanation with comprehensive information covering all aspects of the topic. " * 300
        
        messages.append({"role": "user", "content": long_content})
        messages.append({"role": "assistant", "content": f"Response {i}: " + "I understand your request and here is my comprehensive response with detailed analysis. " * 200})
    
    messages.append({"role": "user", "content": "Now provide a final summary with an image analysis."})
    
    # Add an image to force vision endpoint  
    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": "Here's an image to analyze:"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}}
        ]
    })
    
    return messages

def test_limit_violation():
    print("🚨 Testing Context Limit Violation Detection")
    print("=" * 60)
    
    messages = create_massive_conversation()
    
    # Estimate size
    total_chars = sum(len(str(msg)) for msg in messages)
    estimated_tokens = total_chars // 3
    
    print(f"📊 Massive Conversation:")
    print(f"   Messages: {len(messages)}")
    print(f"   Estimated tokens: ~{estimated_tokens:,}")
    print(f"   Vision model limit: 65,536 tokens")
    print(f"   Expected: Should show limit violation and emergency truncation")
    print()
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "glm-4.5",  # Auto-routing with image will go to vision endpoint
            "messages": messages,
            "max_tokens": 100,
            "stream": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print("✅ Response received (proxy handled the overflow!)")
        
        # Check context information
        context_info = data.get("context_info", {})
        usage = data.get("usage", {})
        
        if context_info:
            print(f"\n📊 Context Analysis:")
            print(f"   🎯 Real input tokens: {context_info.get('real_input_tokens', 'N/A'):,}")
            print(f"   🎯 Context limit: {context_info.get('context_hard_limit', 'N/A'):,} ({context_info.get('endpoint_type', 'unknown')})")
            print(f"   🎯 Utilization: {context_info.get('utilization_percent', 'N/A')}%")
            print(f"   🎯 Available: {context_info.get('available_tokens', 'N/A'):,} tokens")
            
            if context_info.get('truncated', False):
                print(f"\n⚠️  EMERGENCY TRUNCATION OCCURRED:")
                print(f"   📉 Original: {context_info.get('original_tokens', 'N/A'):,} tokens")
                print(f"   📉 Final: {context_info.get('real_input_tokens', 'N/A'):,} tokens") 
                print(f"   📉 Messages removed: {context_info.get('messages_removed', 'N/A')}")
                print(f"   📉 Reason: {context_info.get('truncation_reason', 'Unknown')}")
                print(f"   💡 Client note: {context_info.get('client_note', 'Unknown')}")
            else:
                print(f"\n✨ No truncation occurred!")
                
            print(f"\n💡 Client Action Required:")
            utilization = context_info.get('utilization_percent', 0)
            if utilization > 80:
                print(f"   🔴 CRITICAL: >80% utilization - reduce context immediately")
            elif utilization > 60:
                print(f"   🟡 WARNING: >60% utilization - consider reducing context")
            else:
                print(f"   🟢 SAFE: <60% utilization - context managed well")
        
        # Show usage information
        if usage:
            print(f"\n📈 Token Usage:")
            print(f"   Input: {usage.get('prompt_tokens', 'N/A')} (scaled for compatibility)")  
            print(f"   Output: {usage.get('completion_tokens', 'N/A')}")
            print(f"   Total: {usage.get('total_tokens', 'N/A')}")
            
            if usage.get('real_input_tokens'):
                print(f"   Real Input: {usage.get('real_input_tokens', 'N/A')} (actual count)")
                print(f"   Endpoint: {usage.get('endpoint_type', 'N/A')}")
        
        # Show response preview
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        print(f"\n💬 Response Preview:")
        print(f"   {content[:150]}...")
        
    else:
        print(f"❌ Request failed: {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error details: {error_data}")
        except:
            print(f"Error text: {response.text[:200]}")

if __name__ == "__main__":
    test_limit_violation()