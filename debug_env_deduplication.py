#!/usr/bin/env python3
"""
Debug script to test environment details deduplication
"""

import sys
import os
sys.path.append('src')

from environment_details_manager import deduplicate_environment_details, get_deduplication_stats

def test_environment_deduplication():
    """Test environment details deduplication with sample data"""
    
    # Create test messages with multiple environment details
    messages = [
        {
            "role": "user",
            "content": "Hello! Here's my environment:\n<environment_details>\nWorkspace: /home/user/project\nFiles: main.py, utils.py\n</environment_details>\n\nHow can I help you?"
        },
        {
            "role": "assistant", 
            "content": "I can help you with your project."
        },
        {
            "role": "user",
            "content": "Thanks! Here's my updated environment:\n<environment_details>\nWorkspace: /home/user/project\nFiles: main.py, utils.py, new_file.py\nCurrent directory: /home/user/project\n</environment_details>\n\nWhat do you think?"
        },
        {
            "role": "assistant",
            "content": "Great! I see you added new_file.py"
        },
        {
            "role": "user", 
            "content": "Yes! Environment info again:\n<environment_details>\nWorkspace: /home/user/project\nFiles: main.py, utils.py, new_file.py, another.py\nCurrent directory: /home/user/project\n</environment_details>\n\nLet's continue."
        }
    ]
    
    print("=== BEFORE DEDUPLICATION ===")
    for i, msg in enumerate(messages):
        if msg["role"] == "user":
            print(f"Message {i}: {msg['content'][:100]}...")
            if "<environment_details>" in msg["content"]:
                print("  -> Contains environment details")
    
    # Apply deduplication
    print("\n=== APPLYING DEDUPLICATION ===")
    result = deduplicate_environment_details(messages)
    
    print(f"Strategy used: {result.strategy_used}")
    print(f"Blocks removed: {len(result.removed_blocks)}")
    print(f"Blocks kept: {len(result.kept_blocks)}")
    print(f"Tokens saved: {result.tokens_saved}")
    
    print("\n=== AFTER DEDUPLICATION ===")
    for i, msg in enumerate(result.deduplicated_messages):
        if msg["role"] == "user":
            print(f"Message {i}: {msg['content'][:100]}...")
            if "<environment_details>" in msg["content"]:
                print("  -> Still contains environment details")
            else:
                print("  -> Environment details removed")
    
    print("\n=== STATS ===")
    stats = get_deduplication_stats()
    print(f"Total processed: {stats.get('total_processed', 0)}")
    print(f"Total blocks removed: {stats.get('total_blocks_removed', 0)}")
    print(f"Total tokens saved: {stats.get('total_tokens_saved', 0)}")
    
    return result

if __name__ == "__main__":
    test_environment_deduplication()