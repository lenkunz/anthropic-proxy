#!/usr/bin/env python3
"""Test image detection in different payload formats"""

import json
from typing import Dict, List, Optional, Any

# Copy the image detection functions from main.py
def content_block_has_image(cb: Any) -> bool:
    if not isinstance(cb, dict): 
        return False
    t = cb.get("type")
    if t == "image" and isinstance(cb.get("source"), dict): 
        return True
    if t in ("input_image", "image_url") and (cb.get("source") or cb.get("url") or cb.get("image_url")): 
        return True
    if t == "image" and isinstance(cb.get("image"), (dict, str)): 
        return True
    return False

def message_has_image(msg: Dict[str, Any]) -> bool:
    if not isinstance(msg, dict): 
        return False
    c = msg.get("content")
    if isinstance(c, list): 
        return any(content_block_has_image(b) for b in c if isinstance(b, dict))
    if isinstance(c, dict) and content_block_has_image(c): 
        return True
    return False

def payload_has_image(payload: Dict[str, Any]) -> bool:
    if not isinstance(payload, dict): 
        return False
    msgs = payload.get("messages")
    if isinstance(msgs, list) and any(message_has_image(m) for m in msgs if isinstance(m, dict)): 
        return True
    atts = payload.get("attachments")
    if isinstance(atts, list):
        for a in atts:
            if isinstance(a, dict) and a.get("type") in ("image","input_image","image_url"): 
                return True
    return False

def test_image_detection():
    """Test various image payload formats"""
    
    # Test 1: OpenAI format with image_url
    test1 = {
        "model": "glm-4.5v",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANS..."}}
                ]
            }
        ]
    }
    print(f"Test 1 (OpenAI image_url format): {payload_has_image(test1)}")
    
    # Test 2: Anthropic format with image source
    test2 = {
        "model": "glm-4.5v", 
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBORw0KGgoAAAANS..."}}
                ]
            }
        ]
    }
    print(f"Test 2 (Anthropic image format): {payload_has_image(test2)}")
    
    # Test 3: Alternative OpenAI format
    test3 = {
        "model": "glm-4.5v",
        "messages": [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": "https://example.com/image.jpg"}
                ]
            }
        ]
    }
    print(f"Test 3 (OpenAI simple image_url): {payload_has_image(test3)}")
    
    # Test 4: Attachments format
    test4 = {
        "model": "glm-4.5v",
        "messages": [{"role": "user", "content": "What's in this image?"}],
        "attachments": [
            {"type": "image", "url": "https://example.com/image.jpg"}
        ]
    }
    print(f"Test 4 (Attachments format): {payload_has_image(test4)}")
    
    # Test 5: Text only (should be False)
    test5 = {
        "model": "glm-4.5",
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ]
    }
    print(f"Test 5 (Text only): {payload_has_image(test5)}")
    
    # Test 6: Debug individual functions
    print("\nDebugging individual functions:")
    
    # Test content_block_has_image with different formats
    block1 = {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}
    print(f"Block 1 (image_url with dict): {content_block_has_image(block1)}")
    
    block2 = {"type": "image_url", "image_url": "https://example.com/image.jpg"}  
    print(f"Block 2 (image_url with string): {content_block_has_image(block2)}")
    
    block3 = {"type": "image", "source": {"type": "base64", "data": "abc"}}
    print(f"Block 3 (Anthropic image): {content_block_has_image(block3)}")
    
    # Test message_has_image 
    msg1 = {
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}
        ]
    }
    print(f"Message 1 (with image_url): {message_has_image(msg1)}")

if __name__ == "__main__":
    test_image_detection()