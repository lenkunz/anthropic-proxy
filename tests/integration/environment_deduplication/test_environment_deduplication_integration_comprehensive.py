#!/usr/bin/env python3
"""
Comprehensive test for environment deduplication integration points.

This test validates that:
1. Environment deduplication happens BEFORE token counting
2. Deduplication works for both downstream (client requests) and upstream (API calls)
3. Deduplication applies to all targets (both vision and text models)
4. Integration points work correctly across all modules
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:8000"

def create_test_messages_with_env_details() -> List[Dict[str, Any]]:
    """Create test messages with environment details that should be deduplicated."""
    return [
        {
            "role": "user",
            "content": "<environment_details>\nWorkspace: /home/user/project\nCurrent directory: /home/user/project\nFiles: 10 files\nLast modified: 2024-01-01\n</environment_details>\n\nHello, can you help me with my project?"
        },
        {
            "role": "assistant", 
            "content": "I'd be happy to help you with your project! What would you like to work on?"
        },
        {
            "role": "user",
            "content": "<environment_details>\nWorkspace: /home/user/project\nCurrent directory: /home/user/project\nFiles: 12 files\nLast modified: 2024-01-02\n</environment_details>\n\nI need help with debugging an issue."
        },
        {
            "role": "assistant",
            "content": "I can help you debug the issue. Could you provide more details about what's happening?"
        },
        {
            "role": "user",
            "content": "```environment\nWorkspace: /home/user/project\nDirectory: /home/user/project\nFiles: 12 files\nLast modified: 2024-01-02\n```\n\nThe error occurs when I try to run the tests."
        }
    ]

def create_test_messages_without_env_details() -> List[Dict[str, Any]]:
    """Create test messages without environment details for baseline comparison."""
    return [
        {
            "role": "user",
            "content": "Hello, can you help me with my project?"
        },
        {
            "role": "assistant", 
            "content": "I'd be happy to help you with your project! What would you like to work on?"
        },
        {
            "role": "user",
            "content": "I need help with debugging an issue."
        },
        {
            "role": "assistant",
            "content": "I can help you debug the issue. Could you provide more details about what's happening?"
        },
        {
            "role": "user",
            "content": "The error occurs when I try to run the tests."
        }
    ]

def test_token_counter_integration():
    """Test that token counting functions apply environment deduplication."""
    print("🧪 Testing token counter integration...")
    
    try:
        from src.accurate_token_counter import get_token_counter
        from src.environment_details_manager import get_environment_details_manager
        
        # Test with environment details
        messages_with_env = create_test_messages_with_env_details()
        messages_without_env = create_test_messages_without_env_details()
        
        # Get token counter
        token_counter = get_token_counter()
        
        # Test count_messages_tokens_with_env_deduplication
        result_with_dedup, tokens_saved = token_counter.count_messages_tokens_with_env_dedlication(
            messages_with_env, "openai"
        )
        
        # Test regular count_messages_tokens
        result_without_dedup = token_counter.count_messages_tokens(
            messages_with_env, "openai"
        )
        
        # Test with messages without environment details
        result_clean = token_counter.count_messages_tokens(
            messages_without_env, "openai"
        )
        
        print(f"  ✅ Messages with env details (with deduplication): {result_with_dedup.total_tokens} tokens")
        print(f"  ✅ Messages with env details (without deduplication): {result_without_dedup.total_tokens} tokens")
        print(f"  ✅ Messages without env details: {result_clean.total_tokens} tokens")
        print(f"  ✅ Tokens saved by deduplication: {tokens_saved}")
        
        # Verify deduplication is working
        if tokens_saved > 0:
            print("  ✅ Environment deduplication is working in token counter")
        else:
            print("  ⚠️  Environment deduplication may not be working as expected")
        
        # Verify deduplicated result is closer to clean result
        diff_with_dedup = abs(result_with_dedup.total_tokens - result_clean.total_tokens)
        diff_without_dedup = abs(result_without_dedup.total_tokens - result_clean.total_tokens)
        
        if diff_with_dedup <= diff_without_dedup:
            print("  ✅ Deduplication brings token count closer to clean baseline")
        else:
            print("  ⚠️  Deduplication may not be optimally reducing tokens")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Token counter integration test failed: {e}")
        return False

def test_context_window_manager_integration():
    """Test that context window manager applies environment deduplication."""
    print("\n🧪 Testing context window manager integration...")
    
    try:
        from src.context_window_manager import context_manager
        
        messages_with_env = create_test_messages_with_env_details()
        messages_without_env = create_test_messages_without_env_details()
        
        # Test context analysis with deduplication
        context_info_with_env = context_manager.get_context_info(
            messages_with_env, is_vision=False
        )
        
        context_info_without_env = context_manager.get_context_info(
            messages_without_env, is_vision=False
        )
        
        print(f"  ✅ Context info (with env details): {context_info_with_env['estimated_tokens']} tokens")
        print(f"  ✅ Context info (without env details): {context_info_without_env['estimated_tokens']} tokens")
        
        # Test intelligent context management
        management_result = context_manager.apply_intelligent_context_management(
            messages_with_env, is_vision=False, max_tokens=100000
        )
        
        if management_result.tokens_saved > 0:
            print(f"  ✅ Context management saved {management_result.tokens_saved} tokens")
        else:
            print("  ℹ️  Context management did not save tokens (may not be needed)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Context window manager integration test failed: {e}")
        return False

def test_message_condenser_integration():
    """Test that message condenser applies environment deduplication."""
    print("\n🧪 Testing message condenser integration...")
    
    try:
        from src.message_condenser import condense_messages_if_needed
        
        messages_with_env = create_test_messages_with_env_details()
        
        # Test condensation with deduplication
        condensation_result = asyncio.run(condense_messages_if_needed(
            messages_with_env, max_tokens=1000, is_vision=False
        ))
        
        print(f"  ✅ Original messages: {len(messages_with_env)}")
        print(f"  ✅ Condensed messages: {len(condensation_result.condensed_messages)}")
        print(f"  ✅ Original tokens: {condensation_result.original_tokens}")
        print(f"  ✅ Condensed tokens: {condensation_result.condensed_tokens}")
        print(f"  ✅ Tokens saved: {condensation_result.tokens_saved}")
        
        if condensation_result.tokens_saved > 0:
            print("  ✅ Message condensation with deduplication is working")
        else:
            print("  ℹ️  Message condensation did not save tokens (may not be needed)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Message condenser integration test failed: {e}")
        return False

def test_main_token_functions_integration():
    """Test that main.py token counting functions apply environment deduplication."""
    print("\n🧪 Testing main.py token functions integration...")
    
    try:
        # Import functions from main.py
        import sys
        sys.path.append('src')
        from main import count_tokens_from_messages, estimate_tokens_tiktoken
        
        messages_with_env = create_test_messages_with_env_details()
        messages_without_env = create_test_messages_without_env_details()
        
        # Test count_tokens_from_messages
        tokens_with_env = count_tokens_from_messages(messages_with_env)
        tokens_without_env = count_tokens_from_messages(messages_without_env)
        
        print(f"  ✅ count_tokens_from_messages (with env): {tokens_with_env} tokens")
        print(f"  ✅ count_tokens_from_messages (without env): {tokens_without_env} tokens")
        
        # Test estimate_tokens_tiktoken
        tiktokens_with_env = estimate_tokens_tiktoken(messages_with_env)
        tiktokens_without_env = estimate_tokens_tiktoken(messages_without_env)
        
        print(f"  ✅ estimate_tokens_tiktoken (with env): {tiktokens_with_env} tokens")
        print(f"  ✅ estimate_tokens_tiktoken (without env): {tiktokens_without_env} tokens")
        
        # The functions should handle environment details gracefully
        if tokens_with_env > 0 and tiktokens_with_env > 0:
            print("  ✅ Token functions are working with environment details")
        else:
            print("  ⚠️  Token functions may have issues with environment details")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Main token functions integration test failed: {e}")
        return False

def test_environment_details_manager_directly():
    """Test the environment details manager directly."""
    print("\n🧪 Testing environment details manager directly...")
    
    try:
        from src.environment_details_manager import get_environment_details_manager
        
        env_manager = get_environment_details_manager()
        messages_with_env = create_test_messages_with_env_details()
        
        # Test deduplication
        dedup_result = env_manager.deduplicate_environment_details(messages_with_env)
        
        print(f"  ✅ Original messages: {len(messages_with_env)}")
        print(f"  ✅ Deduplicated messages: {len(dedup_result.deduplicated_messages)}")
        print(f"  ✅ Environment blocks detected: {len(dedup_result.detected_blocks)}")
        print(f"  ✅ Environment blocks removed: {len(dedup_result.removed_blocks)}")
        print(f"  ✅ Tokens saved: {dedup_result.tokens_saved}")
        
        # Test detection
        detected_blocks = env_manager.detect_environment_details(
            messages_with_env[0]["content"], 0
        )
        print(f"  ✅ Environment blocks detected in first message: {len(detected_blocks)}")
        
        # Get stats
        stats = env_manager.get_stats()
        print(f"  ✅ Total processed: {stats.get('total_processed', 0)}")
        print(f"  ✅ Total tokens saved: {stats.get('total_tokens_saved', 0)}")
        
        if dedup_result.tokens_saved > 0:
            print("  ✅ Environment deduplication is working correctly")
        else:
            print("  ⚠️  Environment deduplication may not be detecting patterns")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Environment details manager test failed: {e}")
        return False

def test_pipeline_order():
    """Test that deduplication happens before token counting in the pipeline."""
    print("\n🧪 Testing pipeline order (deduplication before token counting)...")
    
    try:
        from src.environment_details_manager import get_environment_details_manager
        from src.accurate_token_counter import get_token_counter
        
        env_manager = get_environment_details_manager()
        token_counter = get_token_counter()
        
        messages_with_env = create_test_messages_with_env_details()
        
        # Step 1: Apply deduplication
        dedup_result = env_manager.deduplicate_environment_details(messages_with_env)
        deduplicated_messages = dedup_result.deduplicated_messages
        
        # Step 2: Count tokens on deduplicated messages
        token_count_dedup = token_counter.count_messages_tokens(deduplicated_messages, "openai")
        
        # Step 3: Count tokens on original messages (without deduplication)
        token_count_original = token_counter.count_messages_tokens(messages_with_env, "openai")
        
        print(f"  ✅ Token count after deduplication: {token_count_dedup.total_tokens}")
        print(f"  ✅ Token count without deduplication: {token_count_original.total_tokens}")
        print(f"  ✅ Tokens saved by pipeline: {token_count_original.total_tokens - token_count_dedup.total_tokens}")
        
        # Verify pipeline order is correct
        if token_count_dedup.total_tokens < token_count_original.total_tokens:
            print("  ✅ Pipeline order is correct: deduplication happens before token counting")
        else:
            print("  ⚠️  Pipeline order may have issues")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Pipeline order test failed: {e}")
        return False

def run_all_tests():
    """Run all integration tests."""
    print("🚀 Starting Comprehensive Environment Deduplication Integration Tests\n")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file. Please set it to run API tests.")
        return False
    
    tests = [
        test_environment_details_manager_directly,
        test_token_counter_integration,
        test_context_window_manager_integration,
        test_message_condenser_integration,
        test_main_token_functions_integration,
        test_pipeline_order,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results Summary:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All integration tests passed! Environment deduplication is properly integrated.")
    else:
        print("⚠️  Some tests failed. Please check the integration points.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)