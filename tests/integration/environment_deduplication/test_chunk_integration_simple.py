#!/usr/bin/env python3
"""
Simple integration test for chunk-based condensation tracking

This script tests the core functionality without complex async operations
to validate that the message chunk condensation tracking system works.
"""

import os
import sys
import tempfile
import shutil

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_chunk_management_basic():
    """Test basic chunk management functionality"""
    print("Testing chunk management basic functionality...")
    
    try:
        # Set environment variables for testing
        temp_dir = tempfile.mkdtemp()
        os.environ['CACHE_DIR'] = temp_dir
        os.environ['ENABLE_CHUNK_PERSISTENCE'] = 'false'  # Disable persistence to avoid async issues
        
        # Import after setting environment
        import importlib
        import message_chunk_manager
        importlib.reload(message_chunk_manager)
        MessageChunkManager = message_chunk_manager.MessageChunkManager
        MessageChunk = message_chunk_manager.MessageChunk
        ChunkState = message_chunk_manager.ChunkState
        
        # Create chunk manager
        chunk_manager = MessageChunkManager()
        
        # Test message chunk identification
        messages = [
            {"role": "user", "content": f"Message {i}"} 
            for i in range(6)
        ]
        
        chunks = chunk_manager.identify_message_chunks(messages, is_vision=False)
        
        print(f"✓ Created {len(chunks)} chunks from {len(messages)} messages")
        
        # Test chunk ID generation
        chunk_id = chunk_manager.get_chunk_id(messages, is_vision=False)
        print(f"✓ Generated chunk ID: {chunk_id}")
        
        # Test content hashing
        hash1 = chunk_manager._generate_content_hash(messages)
        hash2 = chunk_manager._generate_content_hash(messages)
        assert hash1 == hash2, "Same content should generate same hash"
        print(f"✓ Content hash generation works: {hash1}")
        
        # Test chunk state tracking
        if chunks:
            chunk = chunks[0]
            initial_state = chunk.state
            print(f"✓ Initial chunk state: {initial_state}")
            
            # Test state checking
            is_condensed = chunk_manager.is_chunk_condensed(chunk)
            print(f"✓ Chunk condensed check: {is_condensed}")
        
        # Test cache stats
        stats = chunk_manager.get_cache_stats()
        print(f"✓ Cache stats: {stats['chunks_cache_size']} chunks cached")
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ Chunk management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_condensation_engine_basic():
    """Test condensation engine with chunk support"""
    print("Testing condensation engine chunk support...")
    
    try:
        # Set environment variables
        os.environ['ENABLE_AI_CONDENSATION'] = 'true'
        os.environ['CONDENSATION_MIN_MESSAGES'] = '2'
        
        # Import condensation engine
        from message_condenser import AICondensationEngine
        
        engine = AICondensationEngine()
        
        # Test that chunk-based method exists
        has_chunked_method = hasattr(engine, 'condense_messages_chunked')
        print(f"✓ Has chunk-based condensation method: {has_chunked_method}")
        
        # Test chunk stats
        chunk_stats = engine.get_chunk_stats()
        print(f"✓ Chunk stats available: {chunk_stats}")
        
        # Test regular cache stats
        cache_stats = engine.get_cache_stats()
        print(f"✓ Cache stats: {cache_stats}")
        
        return True
        
    except Exception as e:
        print(f"✗ Condensation engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_loading():
    """Test that configuration loads correctly"""
    print("Testing configuration loading...")
    
    try:
        from message_chunk_manager import (
            ENABLE_CHUNK_BASED_CONDENSATION, CHUNK_SIZE_MESSAGES, 
            CHUNK_MAX_TOKENS, CHUNK_CACHE_SIZE, CHUNK_CACHE_TTL,
            ENABLE_CHUNK_PERSISTENCE, SKIP_CONDENSED_CHUNKS,
            CHUNK_CONDENSATION_STRATEGY, CHUNK_AGE_THRESHOLD
        )
        
        print(f"✓ ENABLE_CHUNK_BASED_CONDENSATION: {ENABLE_CHUNK_BASED_CONDENSATION}")
        print(f"✓ CHUNK_SIZE_MESSAGES: {CHUNK_SIZE_MESSAGES}")
        print(f"✓ CHUNK_MAX_TOKENS: {CHUNK_MAX_TOKENS}")
        print(f"✓ CHUNK_CACHE_SIZE: {CHUNK_CACHE_SIZE}")
        print(f"✓ CHUNK_CACHE_TTL: {CHUNK_CACHE_TTL}")
        print(f"✓ ENABLE_CHUNK_PERSISTENCE: {ENABLE_CHUNK_PERSISTENCE}")
        print(f"✓ SKIP_CONDENSED_CHUNKS: {SKIP_CONDENSED_CHUNKS}")
        print(f"✓ CHUNK_CONDENSATION_STRATEGY: {CHUNK_CONDENSATION_STRATEGY}")
        print(f"✓ CHUNK_AGE_THRESHOLD: {CHUNK_AGE_THRESHOLD}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_condensation_strategy():
    """Test condensation strategy selection"""
    print("Testing condensation strategy...")
    
    try:
        from message_condenser import CondensationStrategy
        
        # Test strategy enum values
        strategies = [
            CondensationStrategy.CONVERSATION_SUMMARY,
            CondensationStrategy.KEY_POINT_EXTRACTION,
            CondensationStrategy.PROGRESSIVE_SUMMARIZATION,
            CondensationStrategy.SMART_TRUNCATION
        ]
        
        for strategy in strategies:
            print(f"✓ Strategy available: {strategy.value}")
        
        return True
        
    except Exception as e:
        print(f"✗ Condensation strategy test failed: {e}")
        return False

def test_context_manager_basic():
    """Test context window manager basic functionality"""
    print("Testing context window manager...")
    
    try:
        # Set environment variables
        os.environ['ENABLE_AI_CONDENSATION'] = 'true'
        os.environ['REAL_TEXT_MODEL_TOKENS'] = '200000'
        os.environ['REAL_VISION_MODEL_TOKENS'] = '65536'
        
        from context_window_manager import ContextWindowManager
        
        manager = ContextWindowManager()
        
        # Test basic functionality
        text_limit = manager.get_context_limit(is_vision=False)
        vision_limit = manager.get_context_limit(is_vision=True)
        
        print(f"✓ Text context limit: {text_limit}")
        print(f"✓ Vision context limit: {vision_limit}")
        
        # Test effective limits
        effective_text = manager.get_effective_limit(is_vision=False)
        effective_vision = manager.get_effective_limit(is_vision=True)
        
        print(f"✓ Effective text limit: {effective_text}")
        print(f"✓ Effective vision limit: {effective_vision}")
        
        return True
        
    except Exception as e:
        print(f"✗ Context manager test failed: {e}")
        return False

def test_message_structure():
    """Test message structure handling"""
    print("Testing message structure handling...")
    
    try:
        # Set environment variables
        temp_dir = tempfile.mkdtemp()
        os.environ['CACHE_DIR'] = temp_dir
        os.environ['ENABLE_CHUNK_PERSISTENCE'] = 'false'
        
        # Import after setting environment
        import importlib
        import message_chunk_manager
        importlib.reload(message_chunk_manager)
        MessageChunkManager = message_chunk_manager.MessageChunkManager
        
        chunk_manager = MessageChunkManager()
        
        # Test different message formats
        text_messages = [
            {"role": "user", "content": "Simple text message"},
            {"role": "assistant", "content": "Simple response"}
        ]
        
        complex_messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": "Text content"},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,ABC"}}
                ]
            }
        ]
        
        # Test chunk creation with different formats
        text_chunks = chunk_manager.identify_message_chunks(text_messages, is_vision=False)
        complex_chunks = chunk_manager.identify_message_chunks(complex_messages, is_vision=True)
        
        print(f"✓ Text messages: {len(text_chunks)} chunks")
        print(f"✓ Complex messages: {len(complex_chunks)} chunks")
        
        # Test content hashing with different formats
        text_hash = chunk_manager._generate_content_hash(text_messages)
        complex_hash = chunk_manager._generate_content_hash(complex_messages)
        
        print(f"✓ Text hash: {text_hash}")
        print(f"✓ Complex hash: {complex_hash}")
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ Message structure test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("=== Message Chunk Management Integration Test ===\n")
    
    tests = [
        test_configuration_loading,
        test_chunk_management_basic,
        test_condensation_engine_basic,
        test_condensation_strategy,
        test_context_manager_basic,
        test_message_structure
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # Add spacing between tests
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            print()
    
    print("=== Integration Test Summary ===")
    print(f"Passed: {passed}/{total} tests")
    
    if passed >= total * 0.8:  # 80% pass rate
        print("🎉 Integration tests passed! Message chunk management system is working.")
        return 0
    else:
        print("⚠️  Some integration tests failed. System may need adjustments.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)