#!/usr/bin/env python3
"""
Test file-based caching and image age auto-switching with cache logging
"""

import os
import time
import json
import requests
import base64
from dotenv import load_dotenv

# Load environment
load_dotenv()
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"

def load_test_image():
    """Load the test image as base64"""
    image_path = "pexels-photo-1108099.jpeg"
    if not os.path.exists(image_path):
        print(f"❌ Test image not found: {image_path}")
        return None
    
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    print(f"✅ Loaded test image ({len(image_data)} chars)")
    return image_data

def make_chat_request(messages, test_name):
    """Make a chat request and return timing info"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    payload = {
        "model": "glm-4.5v",
        "messages": messages,
        "max_tokens": 200,
        "temperature": 0.7
    }
    
    print(f"🔄 {test_name}")
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                               json=payload, headers=headers, timeout=60)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"⏱️ Request completed in {elapsed:.2f}s")
            return elapsed, content
        else:
            print(f"❌ Request failed: {response.status_code} - {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None, None

def main():
    print("🧪 Testing File-Based Cache and Image Age Auto-Switching")
    print("=" * 60)
    
    # Load test image
    image_data = load_test_image()
    if not image_data:
        return
    
    image_url = f"data:image/jpeg;base64,{image_data}"
    
    # Test 1: Image with message count < threshold (should NOT trigger auto-switch)
    print("\n📍 Test 1: Messages below age threshold (no auto-switch)")
    messages_1 = [
        {"role": "user", "content": [
            {"type": "text", "text": "Look at this photo."},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]},
        {"role": "assistant", "content": "I can see the photo. What would you like to know about it?"},
        {"role": "user", "content": "What do you see?"}
    ]
    
    elapsed_1, content_1 = make_chat_request(messages_1, "Messages=3 (below threshold)")
    
    # Test 2: Image with message count >= threshold (should trigger auto-switch and caching)
    print("\n📍 Test 2: Messages at age threshold (should trigger auto-switch)")
    messages_2 = [
        {"role": "user", "content": [
            {"type": "text", "text": "Look at this photo."},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]},
        {"role": "assistant", "content": "I can see the photo. What would you like to know about it?"},
        {"role": "user", "content": "Tell me about the colors."},
        {"role": "assistant", "content": "The image has various colors including..."},
        {"role": "user", "content": "What about the composition?"}
    ]
    
    elapsed_2, content_2 = make_chat_request(messages_2, "Messages=5 (at threshold - should trigger auto-switch)")
    
    # Test 3: Repeat of Test 2 (should use cached description)
    print("\n📍 Test 3: Repeat request (should use cache)")
    elapsed_3, content_3 = make_chat_request(messages_2, "Repeat - should use cached description")
    
    # Check cache directory
    print("\n📂 Checking cache directory:")
    cache_dir = "./cache"
    if os.path.exists(cache_dir):
        cache_files = os.listdir(cache_dir)
        print(f"   Cache files: {len(cache_files)}")
        for f in cache_files[:5]:  # Show first 5 files
            full_path = os.path.join(cache_dir, f)
            size = os.path.getsize(full_path)
            print(f"   - {f} ({size} bytes)")
        if len(cache_files) > 5:
            print(f"   ... and {len(cache_files) - 5} more files")
    else:
        print("   Cache directory not found")
    
    # Performance analysis
    print("\n📊 Performance Analysis:")
    if elapsed_2 and elapsed_3:
        speedup = elapsed_2 / elapsed_3 if elapsed_3 > 0 else 0
        print(f"   First request:  {elapsed_2:.2f}s")
        print(f"   Cached request: {elapsed_3:.2f}s")
        print(f"   Speedup:        {speedup:.1f}x")
    
    print("\n🎉 File-based cache test completed!")

if __name__ == "__main__":
    main()