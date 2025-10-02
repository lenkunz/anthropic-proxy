#!/usr/bin/env python3
"""
Comprehensive test for thinking block functionality on direct API calls and proxy calls
Tests both OpenAI and Anthropic endpoints with thinking parameter
"""

import sys
import os
import json
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
PROXY_BASE_URL = "http://localhost:5000"

# Direct API endpoints
OPENAI_DIRECT = "https://api.z.ai/api/coding/paas/v4/chat/completions"
ANTHROPIC_DIRECT = "https://api.z.ai/api/anthropic/v1/messages"

def test_direct_openai_thinking():
    """Test thinking block on direct OpenAI API call"""
    print("\n=== Testing Direct OpenAI API with Thinking ===")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.6",
        "messages": [
            {
                "role": "user",
                "content": "Solve this step by step: What is 15 * 23 + 7 * 11?"
            }
        ],
        "max_tokens": 500,
        "thinking": {
            "type": "enabled"
        }
    }
    
    try:
        print(f"Making direct call to: {OPENAI_DIRECT}")
        response = requests.post(OPENAI_DIRECT, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Direct OpenAI API call successful")
            
            # Check for thinking block in response
            has_thinking = False
            if 'choices' in data and len(data['choices']) > 0:
                choice = data['choices'][0]
                if 'message' in choice:
                    message = choice['message']
                    
                    # First check for reasoning_content field (GLM-4.6 thinking format)
                    if 'reasoning_content' in message and message['reasoning_content']:
                        has_thinking = True
                        reasoning = message['reasoning_content']
                        print("✅ Thinking block found in reasoning_content field")
                        print(f"Reasoning preview: {reasoning[:200]}...")
                    else:
                        print("⚠️  No reasoning_content field found")
                    
                    # Also check traditional thinking blocks in content
                    if not has_thinking and 'content' in message:
                        content = message['content']
                        if isinstance(content, str):
                            if '<thinking>' in content or 'thinking' in content.lower():
                                has_thinking = True
                                print("✅ Thinking block found in response content")
                            else:
                                print("⚠️  No thinking block found in response content")
                                print(f"Content preview: {content[:200]}...")
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and 'text' in part:
                                    if '<thinking>' in part['text'] or 'thinking' in part['text'].lower():
                                        has_thinking = True
                                        print("✅ Thinking block found in response content")
                                        break
            
            # Check usage information
            if 'usage' in data:
                usage = data['usage']
                print(f"Input tokens: {usage.get('prompt_tokens', 'N/A')}")
                print(f"Output tokens: {usage.get('completion_tokens', 'N/A')}")
                print(f"Total tokens: {usage.get('total_tokens', 'N/A')}")
            
            return has_thinking
        else:
            print(f"❌ Direct OpenAI API call failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Direct OpenAI API call error: {e}")
        return False

def test_direct_anthropic_thinking():
    """Test thinking block on direct Anthropic API call"""
    print("\n=== Testing Direct Anthropic API with Thinking ===")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": "glm-4.6",
        "messages": [
            {
                "role": "user",
                "content": "Solve this step by step: What is 15 * 23 + 7 * 11?"
            }
        ],
        "max_tokens": 500,
        "thinking": {
            "type": "enabled"
        }
    }
    
    try:
        print(f"Making direct call to: {ANTHROPIC_DIRECT}")
        response = requests.post(ANTHROPIC_DIRECT, headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Direct Anthropic API call successful")
            
            # Check for thinking block in response
            has_thinking = False
            if 'content' in data:
                content = data['content']
                for part in content:
                    if isinstance(part, dict) and 'text' in part:
                        text = part['text']
                        if '<thinking>' in text or 'thinking' in text.lower():
                            has_thinking = True
                            print("✅ Thinking block found in response content")
                            break
                if not has_thinking:
                    print("⚠️  No thinking block found in response content")
                    # Show preview of content
                    if content:
                        text_preview = content[0].get('text', '')[:200] if content else ''
                        print(f"Content preview: {text_preview}...")
            
            # Check usage information
            if 'usage' in data:
                usage = data['usage']
                print(f"Input tokens: {usage.get('input_tokens', 'N/A')}")
                print(f"Output tokens: {usage.get('output_tokens', 'N/A')}")
            
            return has_thinking
        else:
            print(f"❌ Direct Anthropic API call failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Direct Anthropic API call error: {e}")
        return False

def test_proxy_openai_thinking():
    """Test thinking block on proxy OpenAI endpoint"""
    print("\n=== Testing Proxy OpenAI Endpoint with Thinking ===")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.6-openai",
        "messages": [
            {
                "role": "user",
                "content": "Solve this step by step: What is 15 * 23 + 7 * 11?"
            }
        ],
        "max_tokens": 500,
        "thinking": {
            "type": "enabled"
        }
    }
    
    try:
        print(f"Making proxy call to: {PROXY_BASE_URL}/v1/chat/completions")
        response = requests.post(f"{PROXY_BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Proxy OpenAI call successful")
            
            # Check for thinking block in response
            has_thinking = False
            if 'choices' in data and len(data['choices']) > 0:
                choice = data['choices'][0]
                if 'message' in choice:
                    message = choice['message']
                    
                    # First check for reasoning_content field (GLM-4.6 thinking format)
                    if 'reasoning_content' in message and message['reasoning_content']:
                        has_thinking = True
                        reasoning = message['reasoning_content']
                        print("✅ Thinking block found in proxy reasoning_content field")
                        print(f"Reasoning preview: {reasoning[:200]}...")
                    else:
                        print("⚠️  No reasoning_content field found in proxy response")
                    
                    # Also check traditional thinking blocks in content
                    if not has_thinking and 'content' in message:
                        content = message['content']
                        if isinstance(content, str):
                            if '<thinking>' in content or 'thinking' in content.lower():
                                has_thinking = True
                                print("✅ Thinking block found in proxy response content")
                            else:
                                print("⚠️  No thinking block found in proxy response content")
                                print(f"Content preview: {content[:200]}...")
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and 'text' in part:
                                    if '<thinking>' in part['text'] or 'thinking' in part['text'].lower():
                                        has_thinking = True
                                        print("✅ Thinking block found in proxy response content")
                                        break
            
            # Check usage information
            if 'usage' in data:
                usage = data['usage']
                print(f"Input tokens: {usage.get('prompt_tokens', 'N/A')}")
                print(f"Output tokens: {usage.get('completion_tokens', 'N/A')}")
                print(f"Total tokens: {usage.get('total_tokens', 'N/A')}")
            
            return has_thinking
        else:
            print(f"❌ Proxy OpenAI call failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Proxy OpenAI call error: {e}")
        return False

def test_proxy_anthropic_thinking():
    """Test thinking block on proxy Anthropic endpoint"""
    print("\n=== Testing Proxy Anthropic Endpoint with Thinking ===")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "glm-4.6-anthropic",
        "messages": [
            {
                "role": "user",
                "content": "Solve this step by step: What is 15 * 23 + 7 * 11?"
            }
        ],
        "max_tokens": 500,
        "thinking": {
            "type": "enabled"
        }
    }
    
    try:
        print(f"Making proxy call to: {PROXY_BASE_URL}/v1/chat/completions")
        response = requests.post(f"{PROXY_BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Proxy Anthropic call successful")
            
            # Check for thinking block in response
            has_thinking = False
            if 'choices' in data and len(data['choices']) > 0:
                choice = data['choices'][0]
                if 'message' in choice:
                    message = choice['message']
                    if 'content' in message:
                        content = message['content']
                        if isinstance(content, str):
                            if '<thinking>' in content or 'thinking' in content.lower():
                                has_thinking = True
                                print("✅ Thinking block found in proxy response content")
                            else:
                                print("⚠️  No thinking block found in proxy response content")
                                print(f"Content preview: {content[:200]}...")
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and 'text' in part:
                                    if '<thinking>' in part['text'] or 'thinking' in part['text'].lower():
                                        has_thinking = True
                                        print("✅ Thinking block found in proxy response content")
                                        break
            
            # Check usage information
            if 'usage' in data:
                usage = data['usage']
                print(f"Input tokens: {usage.get('prompt_tokens', 'N/A')}")
                print(f"Output tokens: {usage.get('completion_tokens', 'N/A')}")
                print(f"Total tokens: {usage.get('total_tokens', 'N/A')}")
            
            return has_thinking
        else:
            print(f"❌ Proxy Anthropic call failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Proxy Anthropic call error: {e}")
        return False

def check_server_health():
    """Check if the proxy server is running"""
    try:
        response = requests.get(f"{PROXY_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Proxy server is running")
            return True
        else:
            print(f"❌ Proxy server health check failed: {response.status_code}")
            return False
    except:
        print("❌ Proxy server is not running or not accessible")
        print("Start the server with: docker compose up -d")
        return False

def main():
    print("=== Comprehensive Thinking Block Test ===")
    print("Testing thinking functionality on direct API calls and proxy calls")
    print("for both OpenAI and Anthropic endpoints.")
    
    results = {}
    
    # Test direct API calls
    print("\n" + "="*60)
    print("DIRECT API CALLS")
    print("="*60)
    
    results['direct_openai'] = test_direct_openai_thinking()
    time.sleep(2)  # Brief pause between calls
    
    results['direct_anthropic'] = test_direct_anthropic_thinking()
    time.sleep(2)
    
    # Test proxy calls
    if check_server_health():
        print("\n" + "="*60)
        print("PROXY CALLS")
        print("="*60)
        
        results['proxy_openai'] = test_proxy_openai_thinking()
        time.sleep(2)
        
        results['proxy_anthropic'] = test_proxy_anthropic_thinking()
    else:
        print("\n⚠️  Skipping proxy tests - server not running")
        results['proxy_openai'] = False
        results['proxy_anthropic'] = False
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    print(f"Direct OpenAI API:        {'✅ PASS' if results['direct_openai'] else '❌ FAIL'}")
    print(f"Direct Anthropic API:      {'✅ PASS' if results['direct_anthropic'] else '❌ FAIL'}")
    print(f"Proxy OpenAI Endpoint:     {'✅ PASS' if results['proxy_openai'] else '❌ FAIL'}")
    print(f"Proxy Anthropic Endpoint:   {'✅ PASS' if results['proxy_anthropic'] else '❌ FAIL'}")
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All thinking block tests passed!")
    else:
        print("⚠️  Some tests failed - check the logs above for details")
    
    return results

if __name__ == "__main__":
    main()