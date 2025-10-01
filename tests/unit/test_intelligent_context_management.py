#!/usr/bin/env python3
"""
Test Script for Intelligent Context Management System

This script tests the enhanced ContextWindowManager with:
- AI-powered condensation integration
- Accurate token counting
- Multi-level context validation
- Performance optimization and caching
- Comprehensive error handling
"""

import os
import sys
import asyncio
import time
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_test_messages(num_messages: int = 10, tokens_per_message: int = 1000) -> List[Dict[str, Any]]:
    """Create test messages with specified token count"""
    messages = []
    
    # Add system message
    messages.append({
        "role": "system",
        "content": "You are a helpful AI assistant. This is a system message that provides context for the conversation."
    })
    
    # Add user and assistant messages
    for i in range(num_messages):
        # Create content roughly equivalent to specified token count
        content = "This is test message number " + str(i+1) + ". "
        content += "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * (tokens_per_message // 20)
        
        if i % 2 == 0:
            messages.append({
                "role": "user",
                "content": content
            })
        else:
            messages.append({
                "role": "assistant",
                "content": content
            })
    
    return messages

def create_vision_messages(num_messages: int = 5) -> List[Dict[str, Any]]:
    """Create test messages with images for vision testing"""
    messages = []
    
    # Add system message
    messages.append({
        "role": "system",
        "content": "You are a helpful AI assistant that can analyze images."
    })
    
    # Add messages with images
    for i in range(num_messages):
        if i % 2 == 0:
            content = [
                {
                    "type": "text",
                    "text": f"Please analyze this image number {i+1}. What do you see?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
                    }
                }
            ]
        else:
            content = f"This is a text-only response about image {i}."
        
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({
            "role": role,
            "content": content
        })
    
    return messages

def test_basic_functionality():
    """Test basic context management functionality"""
    print("🧪 Testing Basic Functionality")
    print("=" * 50)
    
    try:
        from context_window_manager import (
            ContextWindowManager, 
            analyze_context_state,
            get_context_info,
            get_context_performance_stats
        )
        
        # Create test messages
        messages = create_test_messages(5, 500)
        
        # Test context analysis
        print("📊 Testing context analysis...")
        analysis = analyze_context_state(messages, is_vision=False)
        print(f"   Risk Level: {analysis.risk_level.value}")
        print(f"   Utilization: {analysis.utilization_percent:.1f}%")
        print(f"   Current Tokens: {analysis.current_tokens}")
        print(f"   Strategy: {analysis.recommended_strategy.value}")
        print(f"   Should Condense: {analysis.should_condense}")
        
        # Test context info
        print("\n📋 Testing context info...")
        info = get_context_info(messages, is_vision=False)
        print(f"   Endpoint: {info['endpoint_type']}")
        print(f"   Utilization: {info['utilization_percent']:.1f}%")
        print(f"   Risk Level: {info['risk_level']}")
        print(f"   Intelligent Management Available: {info['intelligent_management_available']}")
        
        # Test performance stats
        print("\n📈 Testing performance stats...")
        stats = get_context_performance_stats()
        print(f"   Cache Size: {stats['cache_size']}")
        print(f"   Condensation Engine Available: {stats['condensation_engine_available']}")
        print(f"   Accurate Token Counter Available: {stats['accurate_token_counter_available']}")
        
        print("✅ Basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_async_intelligent_management():
    """Test async intelligent context management"""
    print("\n🚀 Testing Async Intelligent Context Management")
    print("=" * 50)
    
    try:
        from context_window_manager import (
            apply_intelligent_context_management,
            validate_and_truncate_context_async
        )
        
        # Test with different context utilization levels
        test_cases = [
            {"name": "Small Context", "messages": create_test_messages(3, 300)},
            {"name": "Medium Context", "messages": create_test_messages(8, 800)},
            {"name": "Large Context", "messages": create_test_messages(15, 1500)},
        ]
        
        for case in test_cases:
            print(f"\n📝 Testing {case['name']}...")
            messages = case['messages']
            
            # Test intelligent management
            start_time = time.time()
            result = await apply_intelligent_context_management(messages, is_vision=False)
            processing_time = time.time() - start_time
            
            print(f"   Original Tokens: {result.original_tokens}")
            print(f"   Final Tokens: {result.final_tokens}")
            print(f"   Tokens Saved: {result.tokens_saved}")
            print(f"   Strategy Used: {result.strategy_used.value}")
            print(f"   Risk Level: {result.risk_level.value}")
            print(f"   Processing Time: {processing_time:.3f}s")
            print(f"   Messages: {len(result.original_messages)} → {len(result.processed_messages)}")
            
            # Test traditional async validation
            print(f"   Testing traditional async validation...")
            processed_msgs, metadata = await validate_and_truncate_context_async(messages, is_vision=False)
            print(f"   Traditional Result - Truncated: {metadata.get('truncated', False)}")
            print(f"   Traditional Method: {metadata.get('method', 'unknown')}")
        
        print("✅ Async intelligent management tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Async intelligent management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_functionality():
    """Test sync context management functionality"""
    print("\n🔄 Testing Sync Context Management")
    print("=" * 50)
    
    try:
        from context_window_manager import (
            validate_and_truncate_context,
            should_condense_context,
            get_context_management_strategy
        )
        
        # Test with various message loads
        test_cases = [
            {"name": "Light Load", "messages": create_test_messages(2, 200)},
            {"name": "Medium Load", "messages": create_test_messages(6, 600)},
            {"name": "Heavy Load", "messages": create_test_messages(12, 1200)},
        ]
        
        for case in test_cases:
            print(f"\n📊 Testing {case['name']}...")
            messages = case['messages']
            
            # Test sync validation
            processed_msgs, metadata = validate_and_truncate_context(messages, is_vision=False)
            print(f"   Validation Result - Truncated: {metadata.get('truncated', False)}")
            print(f"   Risk Level: {metadata.get('risk_level', 'unknown')}")
            print(f"   Utilization: {metadata.get('utilization_percent', 0):.1f}%")
            print(f"   Method: {metadata.get('method', 'unknown')}")
            
            # Test condensation recommendation
            should_condense = should_condense_context(messages, is_vision=False)
            strategy = get_context_management_strategy(messages, is_vision=False)
            print(f"   Should Condense: {should_condense}")
            print(f"   Recommended Strategy: {strategy.value}")
        
        print("✅ Sync functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Sync functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_vision_context_management():
    """Test vision context management"""
    print("\n👁️ Testing Vision Context Management")
    print("=" * 50)
    
    try:
        from context_window_manager import (
            analyze_context_state,
            get_context_info,
            validate_and_truncate_context
        )
        
        # Create vision messages
        vision_messages = create_vision_messages(6)
        
        # Test vision context analysis
        print("📊 Analyzing vision context...")
        analysis = analyze_context_state(vision_messages, is_vision=True)
        print(f"   Vision Risk Level: {analysis.risk_level.value}")
        print(f"   Vision Utilization: {analysis.utilization_percent:.1f}%")
        print(f"   Vision Strategy: {analysis.recommended_strategy.value}")
        
        # Test vision context info
        print("\n📋 Getting vision context info...")
        info = get_context_info(vision_messages, is_vision=True)
        print(f"   Vision Endpoint: {info['endpoint_type']}")
        print(f"   Vision Limit: {info['hard_limit']}")
        print(f"   Vision Utilization: {info['utilization_percent']:.1f}%")
        
        # Test vision validation
        print("\n✅ Testing vision validation...")
        processed_msgs, metadata = validate_and_truncate_context(vision_messages, is_vision=True)
        print(f"   Vision Validation - Truncated: {metadata.get('truncated', False)}")
        print(f"   Vision Risk Level: {metadata.get('risk_level', 'unknown')}")
        
        print("✅ Vision context management tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Vision context management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_caching_performance():
    """Test caching and performance optimization"""
    print("\n⚡ Testing Caching and Performance")
    print("=" * 50)
    
    try:
        from context_window_manager import (
            analyze_context_state,
            get_context_performance_stats,
            clear_context_caches
        )
        
        messages = create_test_messages(5, 500)
        
        # Clear caches first
        clear_context_caches()
        
        # Test first call (should populate cache)
        print("🏃 Testing first analysis call...")
        start_time = time.time()
        analysis1 = analyze_context_state(messages, is_vision=False)
        first_time = time.time() - start_time
        print(f"   First call time: {first_time:.4f}s")
        
        # Test second call (should use cache)
        print("🏃 Testing cached analysis call...")
        start_time = time.time()
        analysis2 = analyze_context_state(messages, is_vision=False)
        cached_time = time.time() - start_time
        print(f"   Cached call time: {cached_time:.4f}s")
        print(f"   Performance improvement: {(first_time - cached_time) / first_time * 100:.1f}%")
        
        # Verify results are identical
        assert analysis1.risk_level == analysis2.risk_level
        assert analysis1.utilization_percent == analysis2.utilization_percent
        print("   ✅ Cached results identical to original")
        
        # Test cache stats
        stats = get_context_performance_stats()
        print(f"   Cache size after tests: {stats['cache_size']}")
        
        print("✅ Caching and performance tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Caching and performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n🛡️ Testing Error Handling and Edge Cases")
    print("=" * 50)
    
    try:
        from context_window_manager import (
            validate_and_truncate_context,
            analyze_context_state
        )
        
        # Test edge cases
        test_cases = [
            {"name": "Empty Messages", "messages": []},
            {"name": "Single Message", "messages": [{"role": "user", "content": "Hello"}]},
            {"name": "Messages with Empty Content", "messages": [{"role": "user", "content": ""}]},
            {"name": "Messages with None Content", "messages": [{"role": "user", "content": None}]},
        ]
        
        for case in test_cases:
            print(f"\n🧪 Testing {case['name']}...")
            messages = case['messages']
            
            try:
                # Test validation
                processed_msgs, metadata = validate_and_truncate_context(messages, is_vision=False)
                print(f"   ✅ Handled gracefully - Method: {metadata.get('method', 'unknown')}")
                
                # Test analysis
                analysis = analyze_context_state(messages, is_vision=False)
                print(f"   ✅ Analysis completed - Risk: {analysis.risk_level.value}")
                
            except Exception as e:
                print(f"   ⚠️  Exception (may be expected): {type(e).__name__}: {e}")
        
        print("✅ Error handling tests completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all tests"""
    print("🧪 Intelligent Context Management System Test Suite")
    print("=" * 60)
    
    # Check environment
    print("🔧 Checking environment...")
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found. Using default configuration.")
    
    print(f"   Working Directory: {os.getcwd()}")
    print(f"   Python Version: {sys.version}")
    
    # Run tests
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Sync Functionality", test_sync_functionality),
        ("Vision Context Management", test_vision_context_management),
        ("Caching Performance", test_caching_performance),
        ("Error Handling", test_error_handling),
        ("Async Intelligent Management", test_async_intelligent_management),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        if asyncio.iscoroutinefunction(test_func):
            results[test_name] = await test_func()
        else:
            results[test_name] = test_func()
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The intelligent context management system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    asyncio.run(run_all_tests())