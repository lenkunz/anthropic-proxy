#!/usr/bin/env python3
"""
Debug script to check what format messages are in when deduplication is called
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
PROXY_BASE_URL = "http://localhost:5000"

def test_message_format_during_deduplication():
    """Test what format messages are in when deduplication happens"""
    print("🔍 Testing Message Format During Deduplication...")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return False
    
    # Temporarily modify the environment details manager to log what it receives
    print("Creating a test to see what messages look like during deduplication...")
    
    # Let's create a simple test that calls the deduplication directly
    try:
        from src.environment_details_manager import get_environment_details_manager
        
        # Test the same message format that should be sent to deduplication
        # This should be in Anthropic format after conversion from OpenAI
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
        
        print("Testing direct deduplication with Anthropic format messages...")
        
        # Count environment details before deduplication
        original_env_count = 0
        for msg in anth_messages:
            if msg['role'] == 'user':
                content = msg.get('content', [])
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get('type') == 'text':
                            text = part.get('text', '')
                            if '<environment_details>' in text:
                                original_env_count += 1
                                print(f"Found environment_details in message: {text[:100]}...")
        
        print(f"Original environment details count: {original_env_count}")
        
        # Call deduplication directly
        env_manager = get_environment_details_manager()
        if env_manager and env_manager.enabled:
            print(f"Environment manager enabled: {env_manager.enabled}")
            print(f"Deduplication strategy: {env_manager.strategy.value}")
            print(f"Available patterns: {len(env_manager.compiled_patterns)}")
            
            # Test detection first
            all_blocks = []
            for i, message in enumerate(anth_messages):
                content = env_manager._extract_message_content(message)
                print(f"Message {i} extracted content: {content[:200]}...")
                blocks = env_manager.detect_environment_details(content, i)
                all_blocks.extend(blocks)
                print(f"Message {i} detected blocks: {len(blocks)}")
            
            print(f"Total blocks detected: {len(all_blocks)}")
            
            if all_blocks:
                for i, block in enumerate(all_blocks):
                    print(f"Block {i}: pattern={block.pattern_used}, length={len(block.content)}")
                    print(f"Content preview: {block.content[:100]}...")
            
            # Now test full deduplication
            dedup_result = env_manager.deduplicate_environment_details(anth_messages)
            
            print(f"Deduplication result:")
            print(f"  Original messages: {len(dedup_result.original_messages)}")
            print(f"  Deduplicated messages: {len(dedup_result.deduplicated_messages)}")
            print(f"  Removed blocks: {len(dedup_result.removed_blocks)}")
            print(f"  Kept blocks: {len(dedup_result.kept_blocks)}")
            print(f"  Tokens saved: {dedup_result.tokens_saved}")
            print(f"  Strategy used: {dedup_result.strategy_used.value}")
            
            # Count environment details after deduplication
            dedup_env_count = 0
            for msg in dedup_result.deduplicated_messages:
                if msg['role'] == 'user':
                    content = msg.get('content', [])
                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get('type') == 'text':
                                text = part.get('text', '')
                                if '<environment_details>' in text:
                                    dedup_env_count += 1
            
            print(f"Environment details after deduplication: {dedup_env_count}")
            
            if dedup_env_count < original_env_count:
                print("✅ SUCCESS: Deduplication worked when called directly!")
                return True
            else:
                print("❌ FAILURE: Deduplication did not work even when called directly")
                return False
        else:
            print("❌ Environment manager not enabled")
            return False
            
    except Exception as e:
        print(f"❌ Error testing direct deduplication: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Message Format Debug...")
    
    success = test_message_format_during_deduplication()
    
    print(f"\n🏁 Results:")
    if success:
        print("✅ Direct deduplication test passed")
    else:
        print("❌ Direct deduplication test failed")
        print("💡 This indicates an issue with the deduplication logic itself")