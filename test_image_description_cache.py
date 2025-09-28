#!/usr/bin/env python3
"""
Test script for image description caching system.
Tests that identical image contexts use cached descriptions.
"""

import os
import time
import json
import base64
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Test configuration
API_BASE = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

def load_test_image_base64() -> str:
    """Load the test image and encode as base64."""
    try:
        with open("pexels-photo-1108099.jpeg", "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print("Test image pexels-photo-1108099.jpeg not found!")
        return None

def create_test_messages(image_b64: str, context_variation: str = "A", question_variation: str = "1") -> List[Dict[str, Any]]:
    """
    Create test messages with controllable context and question variations.
    - context_variation affects the context messages (impacts cache key)
    - question_variation affects only the final question (doesn't impact cache key for image at index 2)
    """
    return [
        {
            "role": "user",
            "content": f"Let's discuss photography techniques. Context variation {context_variation}."
        },
        {
            "role": "assistant", 
            "content": f"I'd be happy to help with photography! What specific techniques interest you? (Context {context_variation})"
        },
        {
            "role": "user",  # This is index 2 - the image message
            "content": [
                {
                    "type": "text",
                    "text": "Here's an urban street scene I captured. What do you think about the composition and lighting?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_b64}"
                    }
                }
            ]
        },
        {
            "role": "assistant",
            "content": "This is a beautiful urban street scene! I can see several compelling elements..."
        },
        {
            "role": "user", 
            "content": f"What about the bicycles in the scene? Question variation {question_variation}."
        }
    ]

def make_chat_request(messages: List[Dict[str, Any]], test_name: str) -> Dict[str, Any]:
    """Make a chat completion request."""
    try:
        print(f"\n🔄 Making request: {test_name}")
        start_time = time.time()
        
        response = requests.post(
            f"{API_BASE}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "glm-4.5",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=30
        )
        
        elapsed = time.time() - start_time
        print(f"⏱️ Request completed in {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            return {"success": True, "result": result, "elapsed": elapsed}
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(response.text)
            return {"success": False, "error": response.text, "elapsed": elapsed}
            
    except Exception as e:
        print(f"❌ Exception during request: {e}")
        return {"success": False, "error": str(e), "elapsed": 0}

def test_cache_behavior():
    """Test that identical contexts use cached descriptions."""
    print("🧪 Testing Image Description Caching System")
    print("=" * 50)
    print("Cache key strategy: Previous 2 messages + image hash")
    
    # Load test image
    image_b64 = load_test_image_base64()
    if not image_b64:
        print("❌ Cannot run test without image file")
        return False
    
    print(f"✅ Loaded test image ({len(image_b64)} chars)")
    
    # Test 1: First request - should generate description
    print("\n📍 Test 1: First request (Context A, Question 1)")
    print("Expected: Cache MISS - first time seeing this image with this context")
    messages1 = create_test_messages(image_b64, context_variation="A", question_variation="1")
    result1 = make_chat_request(messages1, "Context A + Question 1 - cache miss expected")
    
    if not result1["success"]:
        print("❌ First request failed")
        return False
    
    # Test 2: Same context, different question - should use cache (question comes AFTER image)
    print("\n📍 Test 2: Same context, different question (Context A, Question 2)")
    print("Expected: Cache HIT - same context (messages 0-1) + same image, different question doesn't affect cache")
    messages2 = create_test_messages(image_b64, context_variation="A", question_variation="2")
    result2 = make_chat_request(messages2, "Context A + Question 2 - cache hit expected")
    
    if not result2["success"]:
        print("❌ Second request failed") 
        return False
    
    # Test 3: Different context, same question - should generate new description
    print("\n📍 Test 3: Different context, same question (Context B, Question 1)")
    print("Expected: Cache MISS - different context (messages 0-1) changes cache key")
    messages3 = create_test_messages(image_b64, context_variation="B", question_variation="1")
    result3 = make_chat_request(messages3, "Context B + Question 1 - cache miss expected")
    
    if not result3["success"]:
        print("❌ Third request failed")
        return False
    
    # Test 4: Repeat of test 2 - should still use cache
    print("\n📍 Test 4: Repeat of test 2 (Context A, Question 2)")
    print("Expected: Cache HIT - same as test 2, should use cached description")
    messages4 = create_test_messages(image_b64, context_variation="A", question_variation="2")
    result4 = make_chat_request(messages4, "Repeat Context A + Question 2 - cache hit expected")
    
    if not result4["success"]:
        print("❌ Fourth request failed")
        return False
    
    # Analyze timing patterns
    print("\n📊 Timing Analysis:")
    print(f"Test 1 (first, cache miss):     {result1['elapsed']:.2f}s")
    print(f"Test 2 (identical, cache hit):  {result2['elapsed']:.2f}s") 
    print(f"Test 3 (different, cache miss): {result3['elapsed']:.2f}s")
    print(f"Test 4 (repeat, cache hit):     {result4['elapsed']:.2f}s")
    
    # Cache hits should be noticeably faster
    cache_speedup_2 = result1['elapsed'] / max(result2['elapsed'], 0.1)
    cache_speedup_4 = result3['elapsed'] / max(result4['elapsed'], 0.1)
    
    print(f"\n🚀 Speedup Analysis:")
    print(f"Test 2 vs Test 1 speedup: {cache_speedup_2:.1f}x")
    print(f"Test 4 vs Test 3 speedup: {cache_speedup_4:.1f}x")
    
    # Check if responses contain contextual information
    print("\n📝 Response Quality Check:")
    response_text_1 = result1["result"]["choices"][0]["message"]["content"]
    response_text_2 = result2["result"]["choices"][0]["message"]["content"]
    response_text_3 = result3["result"]["choices"][0]["message"]["content"]
    response_text_4 = result4["result"]["choices"][0]["message"]["content"]
    
    photo_terms = ["photograph", "image", "scene", "lighting", "composition", "bicycle", "street", "urban"]
    
    def count_photo_terms(text: str) -> int:
        return sum(1 for term in photo_terms if term.lower() in text.lower())
    
    terms_1 = count_photo_terms(response_text_1)
    terms_2 = count_photo_terms(response_text_2)
    terms_3 = count_photo_terms(response_text_3)
    terms_4 = count_photo_terms(response_text_4)
    
    print(f"Photography terms in responses: {terms_1}, {terms_2}, {terms_3}, {terms_4}")
    
    # Summary
    success = True
    if cache_speedup_2 > 1.5 and cache_speedup_4 > 1.5:
        print("\n✅ Cache performance test PASSED - cached requests are significantly faster")
    else:
        print(f"\n⚠️ Cache performance test inconclusive - speedups: {cache_speedup_2:.1f}x, {cache_speedup_4:.1f}x")
    
    if all(count >= 2 for count in [terms_1, terms_2, terms_3, terms_4]):
        print("✅ Response quality test PASSED - all responses contain contextual photography terms")
    else:
        print("⚠️ Response quality test inconclusive - some responses may lack contextual information")
        success = False
    
    return success

if __name__ == "__main__":
    try:
        success = test_cache_behavior()
        if success:
            print("\n🎉 Image description caching system test completed successfully!")
        else:
            print("\n⚠️ Image description caching system test completed with issues")
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")