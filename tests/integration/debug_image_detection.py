#!/usr/bin/env python3
"""Debug image detection in different payload formats"""

import json
from typing import Dict, List, Optional, Any

def content_block_has_image_debug(cb: Any) -> bool:
    print(f"[DEBUG] content_block_has_image called with: {cb}")
    if not isinstance(cb, dict): 
        print(f"[DEBUG] Not a dict, returning False")
        return False
    t = cb.get("type")
    print(f"[DEBUG] Type: {t}")
    
    if t == "image" and isinstance(cb.get("source"), dict): 
        print(f"[DEBUG] Matched Anthropic image format")
        return True
    if t in ("input_image", "image_url"):
        source = cb.get("source")
        url = cb.get("url") 
        image_url = cb.get("image_url")
        print(f"[DEBUG] Checking image_url type, source={source}, url={url}, image_url={image_url}")
        if source or url or image_url:
            print(f"[DEBUG] Matched OpenAI image_url format")
            return True
    if t == "image" and isinstance(cb.get("image"), (dict, str)): 
        print(f"[DEBUG] Matched alternative image format")
        return True
    print(f"[DEBUG] No match found, returning False")
    return False

def test_debug():
    """Test OpenAI format debug"""
    print("=== Testing OpenAI format with dict ===")
    block1 = {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}
    result1 = content_block_has_image_debug(block1)
    print(f"Result: {result1}\n")
    
    print("=== Testing OpenAI format with string ===")
    block2 = {"type": "image_url", "image_url": "https://example.com/image.jpg"}
    result2 = content_block_has_image_debug(block2)  
    print(f"Result: {result2}\n")
    
    print("=== Testing Anthropic format ===")
    block3 = {"type": "image", "source": {"type": "base64", "data": "abc"}}
    result3 = content_block_has_image_debug(block3)
    print(f"Result: {result3}\n")

if __name__ == "__main__":
    test_debug()