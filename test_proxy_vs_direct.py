#!/usr/bin/env python3
"""Test our proxy routing vs direct upstream to ensure they match"""

import requests
import json
import base64
import os
import copy
from dotenv import load_dotenv

load_dotenv()

def test_proxy_vs_direct():
    """Compare proxy routing with direct upstream call"""
    api_key = os.getenv("SERVER_API_KEY")
    openai_base = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
    
    # Small test image
    small_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yAAAAABJRU5ErkJggg=="
    
    # OpenAI format payload (what client sends to our proxy)
    openai_payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What do you see in this image?"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{small_png_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    print("🔄 Testing our proxy image routing...")
    print("📤 Sending OpenAI format to proxy...")
    
    # Test 1: Send OpenAI format to our proxy
    try:
        proxy_response = requests.post(
            "http://localhost:5000/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=openai_payload,
            timeout=30
        )
        
        print(f"📥 Proxy Status: {proxy_response.status_code}")
        
        if proxy_response.status_code == 200:
            try:
                proxy_data = proxy_response.json()
                print(f"✅ Proxy SUCCESS! Model: {proxy_data.get('model', 'unknown')}")
                proxy_content = proxy_data.get('choices', [{}])[0].get('message', {}).get('content', '')[:100]
                print(f"   Proxy Response: {proxy_content}...")
            except Exception as e:
                print(f"✅ Proxy SUCCESS! (JSON error: {e})")
        else:
            try:
                proxy_error = proxy_response.json()
                print(f"❌ Proxy FAILED: {json.dumps(proxy_error, indent=2)}")
            except:
                print(f"❌ Proxy FAILED: {proxy_response.text[:200]}...")
    
    except Exception as e:
        print(f"❌ Proxy REQUEST FAILED: {e}")
    
    print("\n" + "="*60)
    print("🔄 Testing direct upstream with OpenAI format...")
    print("📤 Sending OpenAI format directly to upstream...")
    
    # Test 2: Send OpenAI format directly to upstream vision endpoint
    try:
        direct_payload = copy.deepcopy(openai_payload)
        direct_payload["model"] = "glm-4.5v"

        direct_response = requests.post(
            f"{openai_base.rstrip('/')}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json=direct_payload,
            timeout=30
        )
        
        print(f"📥 Direct Status: {direct_response.status_code}")
        
        if direct_response.status_code == 200:
            try:
                direct_data = direct_response.json()
                print(f"✅ Direct SUCCESS! Model: {direct_data.get('model', 'unknown')}")
                direct_content = direct_data.get('choices', [{}])[0].get('message', {}).get('content', '')[:100]
                print(f"   Direct Response: {direct_content}...")
            except Exception as e:
                print(f"✅ Direct SUCCESS! (JSON error: {e})")
        else:
            try:
                direct_error = direct_response.json()
                print(f"❌ Direct FAILED: {json.dumps(direct_error, indent=2)}")
            except:
                print(f"❌ Direct FAILED: {direct_response.text[:200]}...")
    
    except Exception as e:
        print(f"❌ Direct REQUEST FAILED: {e}")
    
    print("\n" + "="*60)
    print("📊 CONCLUSION:")
    print("   If both succeed, our proxy routing is working correctly!")
    print("   If proxy fails but direct succeeds, there's a routing or payload bug.")
    print("   If both fail, there might be an upstream issue.")

if __name__ == "__main__":
    test_proxy_vs_direct()
