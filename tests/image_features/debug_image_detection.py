#!/usr/bin/env python3
"""Debug script to test image detection logic"""

import json
from dotenv import load_dotenv

# Test messages in OpenAI format
test_messages = [
    {"role": "user", "content": [
        {"type": "text", "text": "Here's an image:"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}}
    ]},
    {"role": "assistant", "content": "I can see the image."},
    {"role": "user", "content": "What about AI?"},
    {"role": "assistant", "content": "AI is interesting."},
    {"role": "user", "content": "Tell me more."}
]

# Import the functions from main.py  
import sys
import os
sys.path.append(os.path.dirname(__file__))

# We need to avoid importing the full main.py with fastapi, so let's just test the logic inline
def content_block_has_image(cb):
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

def message_has_image(msg):
    if not isinstance(msg, dict): 
        return False
    c = msg.get("content")
    if isinstance(c, list): 
        return any(content_block_has_image(b) for b in c if isinstance(b, dict))
    if isinstance(c, dict) and content_block_has_image(c): 
        return True
    return False

def payload_has_image(payload):
    if not isinstance(payload, dict): 
        return False
    msgs = payload.get("messages")
    if isinstance(msgs, list) and any(message_has_image(m) for m in msgs if isinstance(m, dict)): 
        return True
    return False

def messages_since_last_image(messages):
    if not isinstance(messages, list):
        return -1
    
    # Search backwards from the end
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], dict) and message_has_image(messages[i]):
            return len(messages) - 1 - i
    return -1

def should_auto_switch_to_text(messages, threshold=3):
    if not isinstance(messages, list) or threshold <= 0:
        return False
        
    messages_since = messages_since_last_image(messages)
    if messages_since == -1:  # No images found
        return False
    
    return messages_since >= threshold

print("🧪 Testing image detection logic")
print(f"Messages: {len(test_messages)}")

for i, msg in enumerate(test_messages):
    has_img = message_has_image(msg)
    print(f"  Message {i} ({msg['role']}): has_image={has_img}")

payload = {"messages": test_messages}
has_images = payload_has_image(payload)
print(f"\nPayload has_images: {has_images}")

messages_since = messages_since_last_image(test_messages)
print(f"Messages since last image: {messages_since}")

should_switch = should_auto_switch_to_text(test_messages, 3)
print(f"Should auto-switch to text (threshold=3): {should_switch}")

should_switch_2 = should_auto_switch_to_text(test_messages, 2)
print(f"Should auto-switch to text (threshold=2): {should_switch_2}")