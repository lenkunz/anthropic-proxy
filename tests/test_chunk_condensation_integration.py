#!/usr/bin/env python3
"""
Integration tests for chunk-based condensation system with existing API endpoints

This test suite validates that the chunk management system integrates properly
with the existing condensation engine and context window management.
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
from unittest.mock import Mock, patch, AsyncMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from message_condenser import AICondensationEngine, CondensationResult, CondensationStrategy
from context_window_manager import ContextWindowManager
from message_chunk_manager import MessageChunkManager, MessageChunk, ChunkState, get_chunk_manager

class TestChunkCondensationIntegration:
    """Test integration between chunk management and condensation systems"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables for chunk management
        self.env_patches = [
            patch('message_chunk_manager.ENABLE_CHUNK_BASED_CONDENSATION', True),
            patch('message_chunk_manager.CHUNK_SIZE_MESSAGES', 3),
            patch('message_chunk_manager.CHUNK_MAX_TOKENS', 100),
            patch('message_chunk_manager.CHUNK_OVERLAP_MESSAGES', 1),
            patch('message_chunk_manager.CACHE_DIR', self.temp_dir),
            patch('message_chunk_manager.ENABLE_CHUNK_PERSISTENCE', True),
            patch('message_chunk_manager.SKIP_CONDENSED_CHUNKS', True),
            patch('message_chunk_manager.CHUNK_AGE_THRESHOLD', 1800)
        ]
        
        # Mock environment variables for condensation
        self.condensation_patches = [
            patch('message_condenser.ENABLE_AI_CONDENSATION', True),
            patch('message_condenser.CONDENSATION_MIN_MESSAGES', 2),
            patch('message_condenser.CONDENSATION_CAUTION_THRESHOLD', 0.7),
            patch('message_condenser.CONDENSATION_WARNING_THRESHOLD', 0.8),
            patch('message_condenser.CONDENSATION_CRITICAL_THRESHOLD', 0.9),
            patch('message_condenser.CONDENSATION_CACHE_TTL', 3600)
        ]
        
        # Mock environment variables for context management
        self.context_patches = [
            patch('context_window_manager.ENABLE_AI_CONDENSATION', True),
            patch('context_window_manager.CONDENSATION_DEFAULT_STRATEGY', 'conversation_summary'),
            patch('context_window_manager.REAL_TEXT_MODEL_TOKENS', 200000),
            patch('context_window_manager.REAL_VISION_MODEL_TOKENS', 65536)
        ]
        
        for p in self.env_patches + self.condensation_patches + self.context_patches:
            p.start()
        
        # Initialize components
        self.chunk_manager = get_chunk_manager()
        self.condensation_engine = AICondensationEngine()
        self.context_manager = ContextWindowManager()
    
    def teardown_method(self):
        """Clean up after each test"""
        for p in self.env_patches + self.condensation_patches + self.context_patches:
            p.stop()
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_condensation_engine_chunk_integration(self):
        """Test that AICondensationEngine integrates with chunk management"""
        # Verify chunk manager is available in condensation engine
        assert self.condensation_engine.chunk_manager is not None
        assert hasattr(self.condensation_engine, 'condense_messages_chunked')
    
    def test_context_manager_chunk_integration(self):
        """Test that ContextWindowManager integrates with chunk management"""
        # Verify chunk manager is available in context manager
        assert self.context_manager.chunk_manager is not None
    
    @pytest.mark.asyncio
    async def test_chunk_based_condensation_flow(self):
        """Test complete chunk-based condensation flow"""
        # Create test messages
        messages = [
            {"role": "user", "content": f"Hello, this is message {i} with some content to make it longer."}
            for i in range(8)  # Enough to create multiple chunks
        ]
        
        current_tokens = 500  # Simulate high token count
        max_tokens = 200      # Target for condensation
        
        # Test chunk-based condensation
        result = await self.condensation_engine.condense_messages_chunked(
            messages=messages,
            current_tokens=current_tokens,
            max_tokens=max_tokens,
            preferred_strategy="conversation_summary",
            is_vision=False,
            image_descriptions=None
        )
        
        # Verify result structure
        assert isinstance(result, CondensationResult)
        assert result.success is True
        assert len(result.condensed_messages) > 0
        assert result.original_tokens == current_tokens
        assert result.strategy_used in ["chunk_based", "chunk_cached"]
        
        # Verify metadata
        assert "metadata" in result.__dict__
        if result.metadata:
            assert "total_chunks" in result.metadata
    
    @pytest.mark.asyncio
    async def test_chunk_caching_behavior(self):
        """Test that condensed chunks are cached and reused"""
        messages = [
            {"role": "user", "content": f"Test message {i}"} 
            for i in range(6)
        ]
        
        # First condensation should process chunks
        result1 = await self.condensation_engine.condense_messages_chunked(
            messages=messages,
            current_tokens=300,
            max_tokens=150,
            is_vision=False
        )
        
        # Get chunks after first condensation
        chunks = self.chunk_manager.identify_message_chunks(messages, is_vision=False)
        
        # Mark some chunks as condensed to simulate caching
        if chunks:
            self.chunk_manager.mark_chunk_condensed(
                chunks[0], 
                "Cached summary content", 
                "conversation_summary", 
                50
            )
        
        # Second condensation should use cached chunks
        result2 = await self.condensation_engine.condense_messages_chunked(
            messages=messages,
            current_tokens=300,
            max_tokens=150,
            is_vision=False
        )
        
        # Verify both operations succeeded
        assert result1.success is True
        assert result2.success is True
        
        # Second operation should be faster (from cache) or show cache usage
        if result2.metadata:
            assert "chunks_from_cache" in result2.metadata
    
    @pytest.mark.asyncio
    async def test_context_manager_with_chunk_condensation(self):
        """Test context manager using chunk-based condensation"""
        messages = [
            {"role": "user", "content": f"Long message {i} with lots of content to consume tokens. " * 10}
            for i in range(10)
        ]
        
        # Apply intelligent context management (should use chunk-based condensation)
        result = await self.context_manager.apply_intelligent_context_management(
            messages=messages,
            is_vision=False,
            max_tokens=5000
        )
        
        # Verify result
        assert result is not None
        assert len(result.processed_messages) > 0
        assert result.original_tokens >= result.final_tokens
        
        # Should have used chunk-based condensation if available
        if hasattr(result.metadata, 'get') and result.metadata:
            action = result.metadata.get('action', '')
            assert action in ['ai_condensation', 'none_required', 'monitoring', 'emergency_truncation']
    
    @pytest.mark.asyncio
    async def test_vision_request_chunk_handling(self):
        """Test chunk handling for vision requests"""
        messages = [
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": f"Message {i} with text"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{'x' * 1000}"}}
                ]
            }
            for i in range(4)
        ]
        
        # Test chunk-based condensation for vision
        result = await self.condensation_engine.condense_messages_chunked(
            messages=messages,
            current_tokens=800,
            max_tokens=400,
            is_vision=True,
            image_descriptions={"0_0": f"Image description {i}" for i in range(4)}
        )
        
        # Verify result
        assert isinstance(result, CondensationResult)
        if result.success:
            assert len(result.condensed_messages) > 0
            # Should handle image content appropriately
            for msg in result.condensed_messages:
                if isinstance(msg.get('content'), list):
                    # Verify structure is maintained
                    assert any(item.get('type') in ['text', 'image_url'] for item in msg['content'])
    
    @pytest.mark.asyncio
    async def test_chunk_state_persistence(self):
        """Test that chunk state persists across operations"""
        messages = [
            {"role": "user", "content": f"Persistent message {i}"}
            for i in range(6)
        ]
        
        # First, identify chunks
        chunks = self.chunk_manager.identify_message_chunks(messages, is_vision=False)
        
        if chunks:
            # Mark first chunk as condensed
            self.chunk_manager.mark_chunk_condensed(
                chunks[0], 
                "Persistent summary", 
                "key_point_extraction", 
                30
            )
            
            # Verify state is tracked
            assert self.chunk_manager.is_chunk_condensed(chunks[0]) == True
            
            # Create new chunk manager instance (simulating restart)
            new_chunk_manager = MessageChunkManager()
            
            # Re-identify same chunks
            new_chunks = new_chunk_manager.identify_message_chunks(messages, is_vision=False)
            
            # Verify state persistence (if enabled)
            if new_chunks and len(new_chunks) > 0:
                # The content hash should be the same, allowing state recovery
                assert new_chunks[0].content_hash == chunks[0].content_hash
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self):
        """Test error handling and fallback to traditional condensation"""
        messages = [
            {"role": "user", "content": "Error test message"}
        ]
        
        # Mock chunk manager to raise an exception
        with patch.object(self.condensation_engine, 'chunk_manager', None):
            # Should fall back to traditional condensation
            result = await self.condensation_engine.condense_messages_chunked(
                messages=messages,
                current_tokens=100,
                max_tokens=50,
                is_vision=False
            )
            
            # Should still work with fallback
            assert isinstance(result, CondensationResult)
    
    def test_performance_stats_integration(self):
        """Test that performance stats include chunk information"""
        # Get condensation engine stats
        condensation_stats = self.condensation_engine.get_cache_stats()
        assert "cache_size" in condensation_stats
        
        # Get chunk stats
        chunk_stats = self.condensation_engine.get_chunk_stats()
        assert isinstance(chunk_stats, dict)
        
        if chunk_stats.get("chunk_management_available"):
            assert "chunks_cache_size" in chunk_stats
            assert "chunk_states" in chunk_stats
    
    @pytest.mark.asyncio
    async def test_chunk_strategy_selection(self):
        """Test that appropriate condensation strategies are selected for chunks"""
        messages = [
            {"role": "user", "content": f"Strategy test message {i}"}
            for i in range(12)  # Enough to trigger different strategies
        ]
        
        result = await self.condensation_engine.condense_messages_chunked(
            messages=messages,
            current_tokens=600,
            max_tokens=200,
            is_vision=False
        )
        
        # Verify a strategy was selected
        assert result.strategy_used in ["chunk_based", "chunk_cached", "conversation_summary", 
                                       "key_point_extraction", "progressive_summarization", 
                                       "smart_truncation"]
    
    def test_configuration_validation(self):
        """Test that configuration values are properly applied"""
        # Verify chunk manager has correct configuration
        assert self.chunk_manager.persistence_dir == Path(self.temp_dir) / "chunks"
        
        # Verify condensation engine has chunk manager
        assert self.condensation_engine.chunk_manager is not None
        
        # Verify context manager has chunk manager
        assert self.context_manager.chunk_manager is not None

class TestChunkEdgeCases:
    """Test edge cases and error scenarios"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        self.env_patches = [
            patch('message_chunk_manager.ENABLE_CHUNK_BASED_CONDENSATION', True),
            patch('message_chunk_manager.CACHE_DIR', self.temp_dir),
            patch('message_chunk_manager.CHUNK_SIZE_MESSAGES', 2),  # Small chunks
            patch('message_chunk_manager.CHUNK_MAX_TOKENS', 50)     # Small token limit
        ]
        
        for p in self.env_patches:
            p.start()
        
        self.chunk_manager = MessageChunkManager()
        self.condensation_engine = AICondensationEngine()
    
    def teardown_method(self):
        """Clean up after each test"""
        for p in self.env_patches:
            p.stop()
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.asyncio
    async def test_empty_message_list(self):
        """Test handling of empty message lists"""
        result = await self.condensation_engine.condense_messages_chunked(
            messages=[],
            current_tokens=0,
            max_tokens=100,
            is_vision=False
        )
        
        assert isinstance(result, CondensationResult)
        assert len(result.condensed_messages) == 0
    
    @pytest.mark.asyncio
    async def test_single_message(self):
        """Test handling of single message"""
        messages = [{"role": "user", "content": "Single message"}]
        
        result = await self.condensation_engine.condense_messages_chunked(
            messages=messages,
            current_tokens=10,
            max_tokens=100,
            is_vision=False
        )
        
        assert isinstance(result, CondensationResult)
        # Should not condense single message if below threshold
    
    @pytest.mark.asyncio
    async def test_very_large_message_list(self):
        """Test handling of very large message lists"""
        messages = [
            {"role": "user", "content": f"Large message {i}"}
            for i in range(100)  # Very large list
        ]
        
        result = await self.condensation_engine.condense_messages_chunked(
            messages=messages,
            current_tokens=5000,
            max_tokens=1000,
            is_vision=False
        )
        
        assert isinstance(result, CondensationResult)
        if result.success:
            assert len(result.condensed_messages) < len(messages)  # Should be condensed
    
    def test_malformed_message_content(self):
        """Test handling of malformed message content"""
        malformed_messages = [
            {"role": "invalid", "content": None},
            {"role": "user", "content": {"invalid": "structure"}},
            {"content": "missing_role"}
        ]
        
        # Should handle gracefully
        chunks = self.chunk_manager.identify_message_chunks(malformed_messages, is_vision=False)
        assert len(chunks) >= 1  # Should create fallback chunks

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])