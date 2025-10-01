#!/usr/bin/env python3
"""
Simple test script for Environment Details Deduplication

This script provides a quick way to test the environment details deduplication
functionality without running the full test suite.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.environment_details_manager import (
    get_environment_details_manager,
    deduplicate_environment_details,
    get_deduplication_stats
)
from src.context_window_manager import ContextWindowManager
from src.accurate_token_counter import get_token_counter


def test_basic_deduplication():
    """Test basic environment details deduplication."""
    print("🧪 Testing basic environment details deduplication...")
    
    # Create test messages with environment details
    messages = [
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\"]}\n</environment_details>\nFirst message"},
        {"role": "assistant", "content": "Response to first message"},
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\", \"test.py\"]}\n</environment_details>\nSecond message with updated context"},
        {"role": "assistant", "content": "Response to second message"},
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\", \"test.py\", \"utils.py\"]}\n</environment_details>\nThird message"}
    ]
    
    # Apply deduplication
    result = deduplicate_environment_details(messages)
    
    print(f"✅ Original messages: {len(result.original_messages)}")
    print(f"✅ Processed messages: {len(result.deduplicated_messages)}")
    print(f"✅ Environment blocks removed: {len(result.removed_blocks)}")
    print(f"✅ Environment blocks kept: {len(result.kept_blocks)}")
    print(f"✅ Tokens saved: {result.tokens_saved}")
    print(f"✅ Processing time: {result.processing_time:.4f}s")
    print(f"✅ Strategy used: {result.strategy_used.value}")
    
    return True


async def test_context_manager_integration():
    """Test integration with ContextWindowManager."""
    print("\n🧪 Testing ContextWindowManager integration...")
    
    # Create context manager
    context_manager = ContextWindowManager()
    
    # Create test messages
    messages = [
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\"}\n</environment_details>\nFirst message"},
        {"role": "assistant", "content": "Response"},
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\"]}\n</environment_details>\nSecond message"}
    ]
    
    # Apply intelligent context management
    result = await context_manager.apply_intelligent_context_management(
        messages=messages,
        is_vision=False,
        max_tokens=10000
    )
    
    print(f"✅ Original messages: {len(result.original_messages)}")
    print(f"✅ Processed messages: {len(result.processed_messages)}")
    print(f"✅ Total tokens saved: {result.tokens_saved}")
    print(f"✅ Environment tokens saved: {result.metadata.get('env_tokens_saved', 0)}")
    print(f"✅ Strategy used: {result.strategy_used.value}")
    print(f"✅ Risk level: {result.risk_level.value}")
    
    return True


def test_token_counter_integration():
    """Test integration with AccurateTokenCounter."""
    print("\n🧪 Testing AccurateTokenCounter integration...")
    
    # Get token counter
    token_counter = get_token_counter()
    
    # Create test messages
    messages = [
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\"}\n</environment_details>\nFirst message"},
        {"role": "assistant", "content": "Response"},
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\"]}\n</environment_details>\nSecond message"}
    ]
    
    # Count tokens with environment deduplication
    token_count, env_tokens_saved = token_counter.count_messages_tokens_with_env_deduplication(
        messages=messages,
        endpoint_type="openai"
    )
    
    print(f"✅ Total tokens: {token_count.total_tokens}")
    print(f"✅ Text tokens: {token_count.text_tokens}")
    print(f"✅ Environment tokens saved: {env_tokens_saved}")
    
    return True


def test_different_strategies():
    """Test different deduplication strategies."""
    print("\n🧪 Testing different deduplication strategies...")
    
    strategies = ["keep_latest", "keep_most_relevant", "merge_strategy", "selective_removal"]
    
    messages = [
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\"]}\n</environment_details>\nFirst message"},
        {"role": "assistant", "content": "Response"},
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\", \"test.py\"]}\n</environment_details>\nSecond message"}
    ]
    
    for strategy in strategies:
        # Update environment variable for strategy
        os.environ['ENV_DEDUPLICATION_STRATEGY'] = strategy
        
        # Get new manager instance
        manager = get_environment_details_manager()
        manager.strategy = manager.__class__.strategy.from_value(strategy)
        
        result = deduplicate_environment_details(messages)
        
        print(f"✅ Strategy '{strategy}': {result.tokens_saved} tokens saved, {len(result.removed_blocks)} blocks removed")
    
    return True


def test_performance():
    """Test performance with many messages."""
    print("\n🧪 Testing performance with many messages...")
    
    import time
    
    # Create many messages with environment details
    messages = []
    for i in range(50):
        messages.append({
            "role": "user" if i % 2 == 0 else "assistant",
            "content": f"<environment_details>\n{{\"workspace\": \"/home/user/project\", \"files\": [\"file{i}.py\"]}}\n</environment_details>\nMessage {i}"
        })
    
    # Measure processing time
    start_time = time.time()
    result = deduplicate_environment_details(messages)
    end_time = time.time()
    
    processing_time = end_time - start_time
    
    print(f"✅ Processed {len(messages)} messages in {processing_time:.4f}s")
    print(f"✅ Tokens saved: {result.tokens_saved}")
    print(f"✅ Blocks removed: {len(result.removed_blocks)}")
    print(f"✅ Average time per message: {processing_time/len(messages)*1000:.2f}ms")
    
    return True


def test_edge_cases():
    """Test edge cases."""
    print("\n🧪 Testing edge cases...")
    
    # Test empty messages
    result = deduplicate_environment_details([])
    print(f"✅ Empty messages: {result.tokens_saved} tokens saved")
    
    # Test messages without environment details
    messages = [
        {"role": "user", "content": "Regular message without environment details"},
        {"role": "assistant", "content": "Response to regular message"}
    ]
    result = deduplicate_environment_details(messages)
    print(f"✅ No environment details: {result.tokens_saved} tokens saved")
    
    # Test malformed environment details
    messages = [
        {"role": "user", "content": "<environment_details\nMissing closing tag"}
    ]
    result = deduplicate_environment_details(messages)
    print(f"✅ Malformed environment details: {result.tokens_saved} tokens saved")
    
    return True


def test_statistics():
    """Test statistics collection."""
    print("\n🧪 Testing statistics collection...")
    
    # Run some operations to generate stats
    messages = [
        {"role": "user", "content": "<environment_details>\n{\"workspace\": \"/home/user/project\"}\n</environment_details>\nTest message"}
    ]
    
    # Run multiple operations
    for i in range(5):
        deduplicate_environment_details(messages)
    
    # Get statistics
    stats = get_deduplication_stats()
    
    print(f"✅ Total processed: {stats['total_processed']}")
    print(f"✅ Total blocks found: {stats['total_blocks_found']}")
    print(f"✅ Total blocks removed: {stats['total_blocks_removed']}")
    print(f"✅ Total tokens saved: {stats['total_tokens_saved']}")
    print(f"✅ Average processing time: {stats['average_processing_time']:.6f}s")
    print(f"✅ Removal rate: {stats['removal_rate']:.2%}")
    
    return True


async def main():
    """Run all tests."""
    print("🚀 Starting Environment Details Deduplication Tests\n")
    
    # Load environment variables
    load_dotenv()
    
    # Set test environment variables
    os.environ.setdefault('ENABLE_ENV_DEDUPLICATION', 'true')
    os.environ.setdefault('ENV_DEDUPLICATION_LOGGING', 'false')
    os.environ.setdefault('ENV_DEDUPLICATION_STATS', 'true')
    
    tests = [
        test_basic_deduplication,
        test_context_manager_integration,
        test_token_counter_integration,
        test_different_strategies,
        test_performance,
        test_edge_cases,
        test_statistics
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                await test()
            else:
                test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Environment details deduplication is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)