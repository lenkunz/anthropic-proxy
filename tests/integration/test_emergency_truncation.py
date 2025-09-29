#!/usr/bin/env python3
"""
Test to demonstrate when emergency truncation actually occurs
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

def create_truly_massive_conversation():
    """Create a conversation that exceeds vision model hard limits (65K tokens)"""
    
    # Create a truly massive conversation that would exceed 65K tokens
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    
    # Add many messages with long content to exceed 65K token limit
    for i in range(50):
        # Each message ~2000 tokens = 100K total tokens (exceeds 65K vision limit)
        long_content = f"This is message {i}. " + "Here is very detailed information about topic {i}. " * 300
        
        messages.append({"role": "user", "content": long_content})
        messages.append({"role": "assistant", "content": f"Thank you for the detailed information about topic {i}. " + "I understand your request and here is my comprehensive response. " * 200})
    
    # Final user message
    messages.append({"role": "user", "content": "Now please tell me about image processing techniques with lots of detail."})
    
    return messages

def test_emergency_truncation():
    print("🚨 Testing Emergency Truncation (Hard Limit Exceeded)")
    print("=" * 60)
    
    messages = create_truly_massive_conversation()
    
    # Use tiktoken for accurate token counting
    try:
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        total_tokens = 0
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                total_tokens += len(encoding.encode(content))
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        total_tokens += len(encoding.encode(item.get('text', '')))
        
        total_chars = sum(len(str(msg)) for msg in messages)
        print(f"📊 Massive Conversation Created:")
        print(f"   Messages: {len(messages)}")
        print(f"   Exact tokens: {total_tokens:,}")
        print(f"   Characters: {total_chars:,}")
    except Exception as e:
        # Fallback to rough estimation
        total_chars = sum(len(str(msg)) for msg in messages)
        estimated_tokens = total_chars // 3
        print(f"📊 Massive Conversation Created:")
        print(f"   Messages: {len(messages)}")
        print(f"   Estimated tokens: ~{estimated_tokens:,}")
    print(f"   Vision model limit: 65,536 tokens")
    print(f"   Expected: Emergency truncation should occur!")
    print()
    
    # Test with vision model (glm-4.5 auto-routing should detect images and use vision endpoint)
    # But we'll add an image to force vision endpoint
    messages_with_image = messages + [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Here's an image to analyze:"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}}
        ]
    }]
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "glm-4.5",
            "messages": messages_with_image,
            "max_tokens": 100,
            "stream": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        print(f"✅ SUCCESS: {content[:200]}...")
        
        # Check for truncation in logs by checking if we see truncation messages
        print("🔍 Check docker logs to see emergency truncation in action!")
        
    else:
        print(f"❌ FAILED: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_emergency_truncation()