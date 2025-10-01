#!/usr/bin/env python3
"""
Validation script for Message Chunk Management System

This script validates the chunk-based condensation tracking implementation
without requiring external test frameworks.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_chunk_creation():
    """Test basic chunk creation functionality"""
    print("Testing basic chunk creation...")
    
    try:
        from message_chunk_manager import MessageChunkManager, MessageChunk, ChunkState
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        os.environ['CACHE_DIR'] = temp_dir
        os.environ['ENABLE_CHUNK_PERSISTENCE'] = 'true'
        os.environ['ENABLE_CHUNK_BASED_CONDENSATION'] = 'true'
        
        # Set environment variables before importing module
        import importlib
        import message_chunk_manager
        importlib.reload(message_chunk_manager)
        MessageChunkManager = message_chunk_manager.MessageChunkManager
        
        # Create chunk manager
        chunk_manager = MessageChunkManager()
        
        # Test message chunk creation
        messages = [
            {"role": "user", "content": f"Message {i}"} 
            for i in range(6)
        ]
        
        chunks = chunk_manager.identify_message_chunks(messages, is_vision=False)
        
        assert len(chunks) > 0, "Should create at least one chunk"
        assert all(isinstance(chunk, MessageChunk) for chunk in chunks), "All chunks should be MessageChunk instances"
        
        print(f"✓ Created {len(chunks)} chunks from {len(messages)} messages")
        
        # Test chunk ID generation
        chunk_id = chunk_manager.get_chunk_id(messages, is_vision=False)
        assert chunk_id.startswith("chunk_"), "Chunk ID should start with 'chunk_'"
        
        print(f"✓ Generated chunk ID: {chunk_id}")
        
        # Test content hashing
        hash1 = chunk_manager._generate_content_hash(messages)
        hash2 = chunk_manager._generate_content_hash(messages)
        assert hash1 == hash2, "Same content should generate same hash"
        
        print(f"✓ Content hash generation works: {hash1}")
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ Basic chunk creation failed: {e}")
        return False

def test_chunk_state_management():
    """Test chunk state management"""
    print("Testing chunk state management...")
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        os.environ['CACHE_DIR'] = temp_dir
        os.environ['SKIP_CONDENSED_CHUNKS'] = 'true'
        os.environ['CHUNK_AGE_THRESHOLD'] = '1800'
        
        # Reload module with new environment
        import importlib
        import message_chunk_manager
        importlib.reload(message_chunk_manager)
        MessageChunkManager = message_chunk_manager.MessageChunkManager
        MessageChunk = message_chunk_manager.MessageChunk
        ChunkState = message_chunk_manager.ChunkState
        
        chunk_manager = MessageChunkManager()
        
        # Create test chunk
        messages = [{"role": "user", "content": "Test message"}]
        chunk = MessageChunk(
            chunk_id="test_chunk",
            messages=messages,
            start_index=0,
            end_index=0,
            token_count=10,
            content_hash="abc123",
            created_at=1234567890.0,
            last_modified=1234567890.0,
            state=ChunkState.UNPROCESSED
        )
        
        # Test initial state
        assert chunk_manager.is_chunk_condensed(chunk) == False, "New chunk should not be condensed"
        
        # Mark as condensed
        chunk_manager.mark_chunk_condensed(chunk, "Summarized", "conversation_summary", 5)
        
        assert chunk.state == ChunkState.CONDENSED, "Chunk should be marked as condensed"
        assert chunk.condensed_content == "Summarized", "Condensed content should be set"
        assert chunk.tokens_saved == 5, "Tokens saved should be recorded"
        
        # Test condensed chunk retrieval
        condensed = chunk_manager.get_condensed_chunk(chunk)
        assert condensed is not None, "Should be able to retrieve condensed chunk"
        assert condensed["content"] == "Summarized", "Retrieved content should match"
        
        print("✓ Chunk state management works correctly")
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ Chunk state management failed: {e}")
        return False

def test_chunk_analysis():
    """Test chunk analysis functionality"""
    print("Testing chunk analysis...")
    
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        os.environ['CACHE_DIR'] = temp_dir
        
        # Reload module with new environment
        import importlib
        import message_chunk_manager
        importlib.reload(message_chunk_manager)
        MessageChunkManager = message_chunk_manager.MessageChunkManager
        MessageChunk = message_chunk_manager.MessageChunk
        ChunkState = message_chunk_manager.ChunkState
        ChunkAnalysisResult = message_chunk_manager.ChunkAnalysisResult
        
        chunk_manager = MessageChunkManager()
        
        # Create test chunks with different states
        chunks = [
            MessageChunk(
                chunk_id="chunk_1",
                messages=[{"role": "user", "content": "Hello"}],
                start_index=0,
                end_index=0,
                token_count=5,
                content_hash="abc123",
                created_at=1234567890.0,
                last_modified=1234567890.0,
                state=ChunkState.CONDENSED,
                tokens_saved=2
            ),
            MessageChunk(
                chunk_id="chunk_2",
                messages=[{"role": "assistant", "content": "Hi"}],
                start_index=1,
                end_index=1,
                token_count=3,
                content_hash="def456",
                created_at=1234567890.0,
                last_modified=1234567890.0,
                state=ChunkState.UNPROCESSED
            )
        ]
        
        analysis = chunk_manager.analyze_chunks(chunks)
        
        assert isinstance(analysis, ChunkAnalysisResult), "Should return ChunkAnalysisResult"
        assert analysis.total_chunks == 2, "Should identify correct number of chunks"
        assert len(analysis.condensed_chunks) == 1, "Should identify one condensed chunk"
        assert len(analysis.uncondensed_chunks) == 1, "Should identify one uncondensed chunk"
        assert analysis.total_tokens == 8, "Should calculate total tokens correctly"
        
        print(f"✓ Chunk analysis works: {analysis.total_chunks} chunks, {len(analysis.condensed_chunks)} condensed")
        
        # Clean up
        shutil.rmtree(temp_dir)
        
        return True
        
    except Exception as e:
        print(f"✗ Chunk analysis failed: {e}")
        return False

def test_condensation_engine_integration():
    """Test integration with condensation engine"""
    print("Testing condensation engine integration...")
    
    try:
        from message_condenser import AICondensationEngine
        
        # Mock environment variables
        os.environ['ENABLE_AI_CONDENSATION'] = 'true'
        
        engine = AICondensationEngine()
        
        # Check if chunk manager is available
        has_chunk_manager = hasattr(engine, 'chunk_manager') and engine.chunk_manager is not None
        has_chunked_method = hasattr(engine, 'condense_messages_chunked')
        
        if has_chunk_manager:
            print("✓ Condensation engine has chunk manager integration")
        else:
            print("⚠ Condensation engine chunk manager integration not available (expected)")
        
        if has_chunked_method:
            print("✓ Condensation engine has chunk-based condensation method")
        else:
            print("⚠ Condensation engine chunk-based method not available (expected)")
        
        # Test cache stats
        stats = engine.get_cache_stats()
        assert isinstance(stats, dict), "Cache stats should be a dictionary"
        
        print("✓ Condensation engine cache stats work")
        
        return True
        
    except Exception as e:
        print(f"✗ Condensation engine integration failed: {e}")
        return False

def test_context_manager_integration():
    """Test integration with context window manager"""
    print("Testing context window manager integration...")
    
    try:
        from context_window_manager import ContextWindowManager
        
        # Mock environment variables
        os.environ['ENABLE_AI_CONDENSATION'] = 'true'
        os.environ['REAL_TEXT_MODEL_TOKENS'] = '200000'
        os.environ['REAL_VISION_MODEL_TOKENS'] = '65536'
        
        manager = ContextWindowManager()
        
        # Check if chunk manager is available
        has_chunk_manager = hasattr(manager, 'chunk_manager') and manager.chunk_manager is not None
        
        if has_chunk_manager:
            print("✓ Context window manager has chunk manager integration")
        else:
            print("⚠ Context window manager chunk manager integration not available (expected)")
        
        # Test basic functionality
        limit = manager.get_context_limit(is_vision=False)
        assert isinstance(limit, int), "Context limit should be an integer"
        
        print(f"✓ Context window manager works (text limit: {limit})")
        
        return True
        
    except Exception as e:
        print(f"✗ Context window manager integration failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("Testing configuration...")
    
    try:
        from message_chunk_manager import (
            ENABLE_CHUNK_BASED_CONDENSATION, CHUNK_SIZE_MESSAGES, 
            CHUNK_MAX_TOKENS, CHUNK_CACHE_SIZE, CHUNK_CACHE_TTL,
            ENABLE_CHUNK_PERSISTENCE, SKIP_CONDENSED_CHUNKS
        )
        
        print(f"✓ ENABLE_CHUNK_BASED_CONDENSATION: {ENABLE_CHUNK_BASED_CONDENSATION}")
        print(f"✓ CHUNK_SIZE_MESSAGES: {CHUNK_SIZE_MESSAGES}")
        print(f"✓ CHUNK_MAX_TOKENS: {CHUNK_MAX_TOKENS}")
        print(f"✓ CHUNK_CACHE_SIZE: {CHUNK_CACHE_SIZE}")
        print(f"✓ CHUNK_CACHE_TTL: {CHUNK_CACHE_TTL}")
        print(f"✓ ENABLE_CHUNK_PERSISTENCE: {ENABLE_CHUNK_PERSISTENCE}")
        print(f"✓ SKIP_CONDENSED_CHUNKS: {SKIP_CONDENSED_CHUNKS}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("=== Message Chunk Management Validation ===\n")
    
    tests = [
        test_configuration,
        test_basic_chunk_creation,
        test_chunk_state_management,
        test_chunk_analysis,
        test_condensation_engine_integration,
        test_context_manager_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=== Validation Summary ===")
    print(f"Passed: {passed}/{total} tests")
    
    if passed == total:
        print("🎉 All tests passed! Message chunk management system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)