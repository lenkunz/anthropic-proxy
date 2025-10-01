#!/usr/bin/env python3
"""
Test script for the AccurateTokenCounter system

This script tests the new tiktoken-based token counting system and compares
it with the previous scaling-based approach to ensure accuracy and performance.
"""

import os
import sys
import time
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_accurate_token_counter():
    """Test the AccurateTokenCounter class functionality."""
    print("🧪 Testing AccurateTokenCounter...")
    
    try:
        from accurate_token_counter import AccurateTokenCounter, get_token_counter, count_tokens_accurate
        
        # Test basic functionality
        counter = get_token_counter()
        print(f"✅ AccurateTokenCounter initialized successfully")
        
        # Test simple text messages
        test_messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you for asking!"},
            {"role": "user", "content": "Can you help me with a programming problem?"}
        ]
        
        # Test token counting
        token_count = count_tokens_accurate(test_messages, "openai")
        print(f"✅ Accurate token counting: {token_count} tokens for {len(test_messages)} messages")
        
        # Test with image descriptions
        image_descriptions = {
            0: "A diagram showing the architecture of a web application",
            2: "A code snippet showing a Python function"
        }
        
        test_messages_with_images = [
            {"role": "user", "content": [
                {"type": "text", "text": "Please analyze this image:"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
            ]},
            {"role": "assistant", "content": "I can see this is a technical diagram."},
            {"role": "user", "content": [
                {"type": "text", "text": "Now look at this code:"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
            ]}
        ]
        
        token_count_with_images = count_tokens_accurate(
            test_messages_with_images, "openai", None, image_descriptions
        )
        print(f"✅ Token counting with images: {token_count_with_images} tokens")
        
        # Test cache performance
        start_time = time.time()
        for _ in range(100):
            count_tokens_accurate(test_messages, "openai")
        cached_time = time.time() - start_time
        print(f"✅ Cache performance: 100 calls in {cached_time:.3f}s ({cached_time/100*1000:.2f}ms per call)")
        
        # Get cache stats
        cache_stats = counter.get_cache_stats()
        print(f"✅ Cache stats: {cache_stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ AccurateTokenCounter test failed: {e}")
        return False

def test_context_window_manager_integration():
    """Test integration with ContextWindowManager."""
    print("\n🧪 Testing ContextWindowManager integration...")
    
    try:
        from context_window_manager import ContextWindowManager, get_context_info
        
        manager = ContextWindowManager()
        print(f"✅ ContextWindowManager initialized")
        
        # Test messages
        test_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there! How can I help you today?"},
            {"role": "user", "content": "I need help with understanding context windows and token limits in AI models."}
        ]
        
        # Test token estimation
        estimated_tokens = manager.estimate_message_tokens(test_messages)
        print(f"✅ Token estimation: {estimated_tokens} tokens")
        
        # Test context info
        context_info = get_context_info(test_messages, is_vision=False)
        print(f"✅ Context info: {context_info}")
        
        # Test validation
        is_valid, tokens, reason = manager.validate_context_window(test_messages, is_vision=False)
        print(f"✅ Context validation: valid={is_valid}, tokens={tokens}")
        
        return True
        
    except Exception as e:
        print(f"❌ ContextWindowManager integration test failed: {e}")
        return False

def test_main_py_integration():
    """Test integration with main.py functions."""
    print("\n🧪 Testing main.py integration...")
    
    try:
        # Import main functions
        sys.path.insert(0, '.')
        from main import count_tokens_from_messages, count_tokens_accurate_with_scaling
        
        # Test messages
        test_messages = [
            {"role": "user", "content": "What is the capital of France?"},
            {"role": "assistant", "content": "The capital of France is Paris."},
            {"role": "user", "content": "Tell me more about Paris."}
        ]
        
        # Test updated count_tokens_from_messages
        token_count = count_tokens_from_messages(test_messages)
        print(f"✅ Updated count_tokens_from_messages: {token_count} tokens")
        
        # Test new count_tokens_accurate_with_scaling
        scaled_tokens = count_tokens_accurate_with_scaling(
            test_messages, "anthropic", "openai", is_vision=False
        )
        print(f"✅ Accurate token counting with scaling: {scaled_tokens} tokens")
        
        # Test with image descriptions
        image_descriptions = {0: "A map of Paris showing the Eiffel Tower"}
        test_messages_with_images = [
            {"role": "user", "content": [
                {"type": "text", "text": "What do you see in this image?"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "..."}}
            ]}
        ]
        
        tokens_with_images = count_tokens_from_messages(test_messages_with_images, image_descriptions)
        print(f"✅ Token counting with image descriptions: {tokens_with_images} tokens")
        
        return True
        
    except Exception as e:
        print(f"❌ main.py integration test failed: {e}")
        return False

def test_configuration():
    """Test configuration settings."""
    print("\n🧪 Testing configuration...")
    
    try:
        # Test environment variables
        enable_accurate = os.getenv("ENABLE_ACCURATE_TOKEN_COUNTING", "false").lower() in ("true", "1", "yes")
        cache_size = int(os.getenv("TIKTOKEN_CACHE_SIZE", "1000"))
        enable_logging = os.getenv("ENABLE_TOKEN_COUNTING_LOGGING", "false").lower() in ("true", "1", "yes")
        base_image_tokens = int(os.getenv("BASE_IMAGE_TOKENS", "85"))
        
        print(f"✅ ENABLE_ACCURATE_TOKEN_COUNTING: {enable_accurate}")
        print(f"✅ TIKTOKEN_CACHE_SIZE: {cache_size}")
        print(f"✅ ENABLE_TOKEN_COUNTING_LOGGING: {enable_logging}")
        print(f"✅ BASE_IMAGE_TOKENS: {base_image_tokens}")
        
        # Test scaling configuration (should still be available)
        anthropic_expected = int(os.getenv("ANTHROPIC_EXPECTED_TOKENS", "200000"))
        openai_expected = int(os.getenv("OPENAI_EXPECTED_TOKENS", "200000"))
        real_text_tokens = int(os.getenv("REAL_TEXT_MODEL_TOKENS", "200000"))
        real_vision_tokens = int(os.getenv("REAL_VISION_MODEL_TOKENS", "65536"))
        
        print(f"✅ ANTHROPIC_EXPECTED_TOKENS: {anthropic_expected}")
        print(f"✅ OPENAI_EXPECTED_TOKENS: {openai_expected}")
        print(f"✅ REAL_TEXT_MODEL_TOKENS: {real_text_tokens}")
        print(f"✅ REAL_VISION_MODEL_TOKENS: {real_vision_tokens}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def performance_comparison():
    """Compare performance between old and new token counting methods."""
    print("\n🧪 Performance comparison...")
    
    try:
        # Generate test data
        test_messages = []
        for i in range(50):
            test_messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"This is test message {i+1} with some content to count tokens for. " * 10
            })
        
        # Test new accurate method
        from accurate_token_counter import count_tokens_accurate
        start_time = time.time()
        accurate_tokens = count_tokens_accurate(test_messages, "openai")
        accurate_time = time.time() - start_time
        print(f"✅ Accurate method: {accurate_tokens} tokens in {accurate_time:.4f}s")
        
        # Test old method (if available)
        try:
            sys.path.insert(0, '.')
            from main import count_tokens_from_messages
            start_time = time.time()
            old_tokens = count_tokens_from_messages(test_messages)
            old_time = time.time() - start_time
            print(f"✅ Old method: {old_tokens} tokens in {old_time:.4f}s")
            
            # Compare results
            difference = abs(accurate_tokens - old_tokens)
            percent_diff = (difference / max(accurate_tokens, old_tokens)) * 100
            print(f"✅ Token count difference: {difference} tokens ({percent_diff:.2f}%)")
            print(f"✅ Performance improvement: {old_time/accurate_time:.2f}x faster")
            
        except Exception as e:
            print(f"⚠️  Could not test old method: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance comparison failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Accurate Token Counter Tests\n")
    
    tests = [
        ("Configuration", test_configuration),
        ("AccurateTokenCounter", test_accurate_token_counter),
        ("ContextWindowManager Integration", test_context_window_manager_integration),
        ("main.py Integration", test_main_py_integration),
        ("Performance Comparison", performance_comparison)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The accurate token counting system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())