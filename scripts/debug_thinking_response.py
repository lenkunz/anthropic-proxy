#!/usr/bin/env python3
"""
Debug script to examine the actual response content from thinking block requests
"""

import os
import json
import httpx
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
OPENAI_UPSTREAM = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
ANTHROPIC_UPSTREAM = os.getenv("UPSTREAM_BASE", "https://api.z.ai/api/anthropic")

async def test_direct_openai_thinking():
    """Test direct OpenAI API call with thinking parameter"""
    print("🔍 Testing Direct OpenAI API with thinking parameter...")
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.6",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Think step by step."},
            {"role": "user", "content": "Solve this step by step: What is 15 * 23 + 7 * 11?"}
        ],
        "temperature": 0,
        "thinking": {"type": "enabled"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{OPENAI_UPSTREAM}/chat/completions",
                headers=headers,
                json=payload
            )
            
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                content = response.json()
                print(f"Response keys: {list(content.keys())}")
                
                # Check for thinking blocks in different locations
                if 'choices' in content and content['choices']:
                    choice = content['choices'][0]
                    print(f"Choice keys: {list(choice.keys())}")
                    
                    if 'message' in choice:
                        message = choice['message']
                        print(f"Message keys: {list(message.keys())}")
                        print(f"Content preview: {str(message.get('content', ''))[:200]}...")
                        
                        # Check for thinking in content
                        content_text = message.get('content', '')
                        if '<thinking>' in content_text:
                            print("✅ Found <thinking> tags in content!")
                            # Extract thinking block
                            start = content_text.find('<thinking>')
                            end = content_text.find('</thinking>')
                            if start != -1 and end != -1:
                                thinking_content = content_text[start:end + 10]
                                print(f"Thinking block: {thinking_content}")
                        
                        # Check for thinking as separate field
                        if 'thinking' in message:
                            print(f"✅ Found thinking field: {message['thinking']}")
                
                # Check for thinking at root level
                if 'thinking' in content:
                    print(f"✅ Found thinking at root: {content['thinking']}")
                    
                print(f"Full response: {json.dumps(content, indent=2)}")
            else:
                print(f"Error response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_direct_anthropic_thinking():
    """Test direct Anthropic API call with thinking parameter"""
    print("\n🔍 Testing Direct Anthropic API with thinking parameter...")
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": "glm-4.6",
        "max_tokens": 2000,
        "messages": [
            {"role": "user", "content": "Solve this step by step: What is 15 * 23 + 7 * 11?"}
        ],
        "thinking": {"type": "enabled"}
    }
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{ANTHROPIC_UPSTREAM}/v1/messages",
                headers=headers,
                json=payload
            )
            
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                content = response.json()
                print(f"Response keys: {list(content.keys())}")
                
                # Check for thinking blocks
                if 'content' in content and content['content']:
                    for content_block in content['content']:
                        print(f"Content block type: {content_block.get('type')}")
                        if content_block.get('type') == 'text':
                            text = content_block.get('text', '')
                            print(f"Text preview: {text[:200]}...")
                            
                            if '<thinking>' in text:
                                print("✅ Found <thinking> tags in Anthropic response!")
                                start = text.find('<thinking>')
                                end = text.find('</thinking>')
                                if start != -1 and end != -1:
                                    thinking_content = text[start:end + 10]
                                    print(f"Thinking block: {thinking_content}")
                
                # Check for thinking at root level
                if 'thinking' in content:
                    print(f"✅ Found thinking at root: {content['thinking']}")
                    
                print(f"Full response: {json.dumps(content, indent=2)}")
            else:
                print(f"Error response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting thinking block response debugging...\n")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return
    
    await test_direct_openai_thinking()
    await test_direct_anthropic_thinking()
    
    print("\n🏁 Debugging complete!")

if __name__ == "__main__":
    asyncio.run(main())