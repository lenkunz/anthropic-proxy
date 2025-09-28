#!/usr/bin/env python3
"""
Test script for image age auto-switching feature.

This script tests the new IMAGE_AGE_THRESHOLD functionality that automatically
switches to text endpoints when images are more than N messages old.
"""

import json
import os
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use environment variable for API key
API_KEY = os.getenv("SERVER_API_KEY")
if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

BASE_URL = "http://localhost:5000"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Sample base64 image (1x1 transparent PNG)
SAMPLE_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAG/fzQhxQAAAABJRU5ErkJggg=="

def create_test_messages(scenario: str) -> List[Dict[str, Any]]:
    """Create test message scenarios for different image age cases."""
    
    if scenario == "recent_image":
        # Image in the last message - should use vision endpoint
        return [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
            {"role": "user", "content": [
                {"type": "text", "text": "Can you analyze this image?"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
            ]}
        ]
    
    elif scenario == "old_image_threshold_3":
        # Image is 3 messages old (at threshold) - should switch to text
        return [
            {"role": "user", "content": [
                {"type": "text", "text": "Here's an image to analyze:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
            ]},
            {"role": "assistant", "content": "I can see the image you shared."},
            {"role": "user", "content": "What do you think about it?"},
            {"role": "assistant", "content": "It's a simple image."},
            {"role": "user", "content": "Tell me more about machine learning."}
        ]
    
    elif scenario == "old_image_threshold_5":
        # Image is 5 messages old - definitely should switch to text
        return [
            {"role": "user", "content": [
                {"type": "text", "text": "Here's an image:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
            ]},
            {"role": "assistant", "content": "I can see the image."},
            {"role": "user", "content": "What about AI?"},
            {"role": "assistant", "content": "AI is interesting."},
            {"role": "user", "content": "Tell me about neural networks."},
            {"role": "assistant", "content": "Neural networks are complex."},
            {"role": "user", "content": "Explain deep learning concepts."}
        ]
    
    elif scenario == "multiple_images_mixed":
        # One recent image, one old image - should keep recent, remove old
        return [
            {"role": "user", "content": [
                {"type": "text", "text": "Old image:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
            ]},
            {"role": "assistant", "content": "I see the old image."},
            {"role": "user", "content": "Some discussion here."},
            {"role": "assistant", "content": "Continuing the conversation."},
            {"role": "user", "content": [
                {"type": "text", "text": "Here's a recent image:"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
            ]}
        ]
    
    elif scenario == "text_only":
        # No images - should use text endpoint
        return [
            {"role": "user", "content": "Hello, tell me about AI."},
            {"role": "assistant", "content": "AI is fascinating."},
            {"role": "user", "content": "What about machine learning?"},
            {"role": "assistant", "content": "ML is a subset of AI."},
            {"role": "user", "content": "Explain neural networks."}
        ]
    
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

def test_image_age_switching(scenario: str, expected_endpoint: str, expected_has_images: bool):
    """Test image age switching for a specific scenario."""
    print(f"\n🧪 Testing scenario: {scenario}")
    print(f"   Expected endpoint: {expected_endpoint}")
    print(f"   Expected has_images: {expected_has_images}")
    
    messages = create_test_messages(scenario)
    payload = {
        "model": "glm-4.5",  # Auto-routing model
        "messages": messages,
        "max_tokens": 100,
        "temperature": 0.1
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            headers=HEADERS,
            json=payload,
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we have context_info to determine actual routing
            context_info = data.get("context_info", {})
            endpoint_type = context_info.get("endpoint_type", "unknown")
            
            # Check for image auto-switch indicators in the response
            response_text = ""
            if "choices" in data and len(data["choices"]) > 0:
                response_text = data["choices"][0].get("message", {}).get("content", "")
            
            # Look for our truncation message
            has_truncation_message = "image was provided earlier" in response_text.lower()
            
            print(f"   ✅ Response received ({response.status_code}) in {elapsed:.2f}s")
            print(f"   📡 Actual endpoint: {endpoint_type}")
            print(f"   🖼️  Image truncation applied: {has_truncation_message}")
            print(f"   📝 Response preview: {response_text[:100]}...")
            
            # Validate expectations
            success = True
            if expected_endpoint != "unknown" and endpoint_type != expected_endpoint:
                print(f"   ❌ Endpoint mismatch: expected {expected_endpoint}, got {endpoint_type}")
                success = False
            
            if scenario in ["old_image_threshold_3", "old_image_threshold_5"] and not has_truncation_message:
                print(f"   ❌ Expected truncation message for old images, but not found")
                success = False
            
            if scenario == "text_only" and has_truncation_message:
                print(f"   ❌ Unexpected truncation message for text-only scenario")
                success = False
            
            return success
            
        else:
            print(f"   ❌ Request failed with status {response.status_code}")
            print(f"   📄 Error: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Request error after {elapsed:.2f}s: {e}")
        return False
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"   ❌ Unexpected error after {elapsed:.2f}s: {e}")
        return False

def main():
    """Run comprehensive image age switching tests."""
    print("🚀 Image Age Auto-Switching Test Suite")
    print(f"📍 Testing against: {BASE_URL}")
    print(f"🔐 Using API key: {API_KEY[:10]}..." if API_KEY else "❌ No API key")
    
    # Test scenarios with expected outcomes
    test_cases = [
        ("recent_image", "openai", True),  # Recent image should use vision
        ("old_image_threshold_3", "anthropic", False),  # Old image should switch to text  
        ("old_image_threshold_5", "anthropic", False),  # Very old image should switch to text
        ("text_only", "anthropic", False),  # Text only should use text endpoint
        ("multiple_images_mixed", "openai", True),  # Should keep recent image, use vision
    ]
    
    results = []
    
    for scenario, expected_endpoint, expected_has_images in test_cases:
        success = test_image_age_switching(scenario, expected_endpoint, expected_has_images)
        results.append((scenario, success))
    
    # Summary
    print(f"\n📊 Test Results Summary:")
    successful_tests = sum(1 for _, success in results if success)
    total_tests = len(results)
    
    for scenario, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {scenario}")
    
    print(f"\n🏆 Overall Result: {successful_tests}/{total_tests} tests passed")
    
    if successful_tests == total_tests:
        print("✅ All image age auto-switching tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)