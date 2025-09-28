#!/usr/bin/env python3
"""
Test Client-Controlled Context Management

This tests the new behavior where proxy only truncates when absolutely necessary.
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

def test_scenario(name, messages, model):
    print(f"\n🧪 Testing: {name}")
    print(f"   Model: {model}")
    print(f"   Messages: {len(messages)}")
    
    # Estimate total characters to give sense of size
    total_chars = sum(len(str(msg)) for msg in messages)
    print(f"   Estimated size: ~{total_chars} chars (~{total_chars//3} tokens)")
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": model,
            "messages": messages,
            "max_tokens": 50,  # Small response to test input handling
            "stream": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        print(f"   ✅ SUCCESS: {content[:100]}...")
        
        # Check for truncation warnings
        if "truncated" in str(data).lower():
            print(f"   ⚠️  Truncation occurred")
        else:
            print(f"   ✨ No truncation - client managed context naturally")
    else:
        print(f"   ❌ FAILED: {response.status_code} - {response.text}")

def main():
    print("Testing Client-Controlled Context Management")
    print("=" * 50)
    
    # Test 1: Normal conversation - should NOT truncate
    normal_conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "Tell me about its history."}
    ]
    
    # Test 2: Large conversation - still might not truncate on vision
    large_conversation = normal_conversation + [
        {"role": "assistant", "content": "Paris has a rich history spanning over 2,000 years. " + "Here's more detail. " * 500},
        {"role": "user", "content": "What about the landmarks?"},
        {"role": "assistant", "content": "Paris is famous for many landmarks including the Eiffel Tower, Louvre Museum, Notre-Dame Cathedral. " + "More information follows. " * 200},
        {"role": "user", "content": "Now tell me about French cuisine in detail."}
    ]
    
    # Test 3: MASSIVE conversation - this should trigger emergency truncation
    massive_conversation = large_conversation + [
        {"role": "assistant", "content": "French cuisine is renowned worldwide. " + "A very long explanation follows with extensive details about every aspect of French cooking, history, techniques, regional specialties, famous chefs, and cultural significance. " * 2000},
        {"role": "user", "content": "Tell me more about wine pairing."}
    ]
    
    # Test on different models
    test_scenario("Normal conversation with vision model", normal_conversation, "glm-4.5")
    test_scenario("Large conversation with vision model", large_conversation, "glm-4.5")  
    test_scenario("MASSIVE conversation with vision model", massive_conversation, "glm-4.5")

if __name__ == "__main__":
    main()