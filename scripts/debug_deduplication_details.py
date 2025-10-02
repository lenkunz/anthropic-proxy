#!/usr/bin/env python3
"""
Debug script to see exactly what the deduplicated messages look like
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_deduplication_details():
    """Test exactly what happens during deduplication"""
    print("🔍 Testing Deduplication Details...")
    
    try:
        from src.environment_details_manager import get_environment_details_manager
        
        # Test the same message format
        anth_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "First message"},
                    {"type": "text", "text": "<environment_details>\n# VSCode Visible Files\ntest.py, utils.py\n\n# Current Time\nCurrent time in ISO 8601 UTC format: 2025-10-01T17:40:00.000Z\nUser time zone: Asia/Bangkok, UTC+7\n\n# Current Cost\n$0.00\n\n# Current Mode\n<slug>code</slug>\n<name>Code</name>\n<model>glm-4.6-openai</model>\n====\n\nREMINDERS\n\n| # | Content | Status |\n|---|---------|--------|\n| 1 | Test task | Completed |\n\n</environment_details>"}
                ]
            },
            {
                "role": "assistant", 
                "content": [{"type": "text", "text": "I understand you have a test task."}]
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Second message"},
                    {"type": "text", "text": "<environment_details>\n# VSCode Visible Files\ntest.py, utils.py, config.json\n\n# Current Time\nCurrent time in ISO 8601 UTC format: 2025-10-01T17:41:00.000Z\nUser time zone: Asia/Bangkok, UTC+7\n\n# Current Cost\n$0.00\n\n# Current Mode\n<slug>code</slug>\n<name>Code</name>\n<model>glm-4.6-openai</model>\n====\n\nREMINDERS\n\n| # | Content | Status |\n|---|---------|--------|\n| 1 | Second task | In Progress |\n\n</environment_details>"}
                ]
            }
        ]
        
        print("=== ORIGINAL MESSAGES ===")
        for i, msg in enumerate(anth_messages):
            print(f"Message {i} ({msg['role']}):")
            content = msg.get('content', [])
            if isinstance(content, list):
                for j, part in enumerate(content):
                    if isinstance(part, dict) and part.get('type') == 'text':
                        text = part.get('text', '')
                        print(f"  Part {j}: {text[:100]}...")
                        if '<environment_details>' in text:
                            print(f"    ✅ Contains environment_details ({len(text)} chars)")
            print()
        
        # Call deduplication
        env_manager = get_environment_details_manager()
        dedup_result = env_manager.deduplicate_environment_details(anth_messages)
        
        print("=== DEDUPLICATION RESULT ===")
        print(f"Removed blocks: {len(dedup_result.removed_blocks)}")
        print(f"Kept blocks: {len(dedup_result.kept_blocks)}")
        print(f"Tokens saved: {dedup_result.tokens_saved}")
        print()
        
        if dedup_result.removed_blocks:
            print("=== REMOVED BLOCKS ===")
            for i, block in enumerate(dedup_result.removed_blocks):
                print(f"Removed Block {i}:")
                print(f"  Message index: {block.message_index}")
                print(f"  Pattern: {block.pattern_used}")
                print(f"  Content: {block.content[:200]}...")
            print()
        
        if dedup_result.kept_blocks:
            print("=== KEPT BLOCKS ===")
            for i, block in enumerate(dedup_result.kept_blocks):
                print(f"Kept Block {i}:")
                print(f"  Message index: {block.message_index}")
                print(f"  Pattern: {block.pattern_used}")
                print(f"  Content: {block.content[:200]}...")
            print()
        
        print("=== DEDUPLICATED MESSAGES ===")
        for i, msg in enumerate(dedup_result.deduplicated_messages):
            print(f"Deduplicated Message {i} ({msg['role']}):")
            content = msg.get('content', [])
            if isinstance(content, list):
                for j, part in enumerate(content):
                    if isinstance(part, dict) and part.get('type') == 'text':
                        text = part.get('text', '')
                        print(f"  Part {j} ({len(text)} chars): {text[:100]}...")
                        if '<environment_details>' in text:
                            print(f"    ✅ Still contains environment_details")
                        else:
                            print(f"    ❌ No environment_details found")
                        # Show the actual content for debugging
                        if len(text) < 50:
                            print(f"    Full content: '{text}'")
            else:
                text = str(content)
                print(f"  Content ({len(text)} chars): {text[:100]}...")
                if '<environment_details>' in text:
                    print(f"    ✅ Still contains environment_details")
                else:
                    print(f"    ❌ No environment_details found")
            print()
        
        # Count environment details before and after
        original_count = 0
        for msg in anth_messages:
            if msg['role'] == 'user':
                content = msg.get('content', [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            text = part.get('text', '')
                            if '<environment_details>' in text:
                                original_count += 1
        
        dedup_count = 0
        for msg in dedup_result.deduplicated_messages:
            if msg['role'] == 'user':
                content = msg.get('content', [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            text = part.get('text', '')
                            if '<environment_details>' in text:
                                dedup_count += 1
        
        print("=== SUMMARY ===")
        print(f"Original environment_details count: {original_count}")
        print(f"Deduplicated environment_details count: {dedup_count}")
        print(f"Blocks removed by deduplication: {len(dedup_result.removed_blocks)}")
        
        if dedup_count < original_count:
            print("✅ SUCCESS: Environment details were actually removed!")
            return True
        elif len(dedup_result.removed_blocks) > 0:
            print("⚠️  PARTIAL: Blocks were removed but tags might remain")
            print("This could be a bug in the removal logic")
            return False
        else:
            print("❌ FAILURE: No environment details were removed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Deduplication Details Debug...")
    
    success = test_deduplication_details()
    
    print(f"\n🏁 Results:")
    if success:
        print("✅ Deduplication is working correctly")
    else:
        print("❌ Deduplication has issues")