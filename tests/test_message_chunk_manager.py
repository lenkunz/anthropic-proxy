#!/usr/bin/env python3
"""
Comprehensive tests for Message Chunk Management System

This test suite validates the chunk-based condensation tracking system,
including chunk identification, caching, condensation state tracking,
and integration with the existing condensation system.
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from message_chunk_manager import (
    MessageChunkManager, MessageChunk, ChunkState, ChunkAnalysisResult,
    get_chunk_manager, ENABLE_CHUNK_BASED_CONDENSATION
)

class TestMessageChunk:
    """Test MessageChunk dataclass and related functionality"""
    
    def test_message_chunk_creation(self):
        """Test creating a MessageChunk with all fields"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        chunk = MessageChunk(
            chunk_id="test_chunk_1",
            messages=messages,
            start_index=0,
            end_index=1,
            token_count=10,
            content_hash="abc123",
            created_at=1234567890.0,
            last_modified=1234567890.0,
            state=ChunkState.UNPROCESSED
        )
        
        assert chunk.chunk_id == "test_chunk_1"
        assert chunk.messages == messages
        assert chunk.start_index == 0
        assert chunk.end_index == 1
        assert chunk.token_count == 10
        assert chunk.state == ChunkState.UNPROCESSED
        assert chunk.condensation_strategy is None
        assert chunk.tokens_saved == 0
    
    def test_chunk_state_enum(self):
        """Test ChunkState enum values"""
        assert ChunkState.UNPROCESSED.value == "unprocessed"
        assert ChunkState.CONDENSING.value == "condensing"
        assert ChunkState.CONDENSED.value == "condensed"
        assert ChunkState.MODIFIED.value == "modified"
        assert ChunkState.EXPIRED.value == "expired"

class TestMessageChunkManager:
    """Test MessageChunkManager class functionality"""
    
    def setup_method(self):
        """Set up test environment before each test"""
        # Create temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        self.env_patches = [
            patch('message_chunk_manager.ENABLE_CHUNK_BASED_CONDENSATION', True),
            patch('message_chunk_manager.CHUNK_SIZE_MESSAGES', 3),
            patch('message_chunk_manager.CHUNK_MAX_TOKENS', 100),
            patch('message_chunk_manager.CHUNK_OVERLAP_MESSAGES', 1),
            patch('message_chunk_manager.CHUNK_CACHE_SIZE', 10),
            patch('message_chunk_manager.CHUNK_CACHE_TTL', 3600),
            patch('message_chunk_manager.ENABLE_CHUNK_PERSISTENCE', True),
            patch('message_chunk_manager.CACHE_DIR', self.temp_dir),
            patch('message_chunk_manager.SKIP_CONDENSED_CHUNKS', True),
            patch('message_chunk_manager.CHUNK_AGE_THRESHOLD', 1800)
        ]
        
        for p in self.env_patches:
            p.start()
        
        # Create chunk manager instance
        self.chunk_manager = MessageChunkManager()
    
    def teardown_method(self):
        """Clean up after each test"""
        # Stop patches
        for p in self.env_patches:
            p.stop()
        
        # Clean up temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_chunk_manager_initialization(self):
        """Test chunk manager initializes correctly"""
        assert self.chunk_manager is not None
        assert self.chunk_manager.chunks_cache == {}
        assert self.chunk_manager.chunk_state_cache == {}
        assert self.chunk_manager.persistence_dir == Path(self.temp_dir) / "chunks"
    
    def test_generate_content_hash(self):
        """Test content hash generation"""
        messages1 = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        
        messages2 = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        
        messages3 = [
            {"role": "user", "content": "Different"},
            {"role": "assistant", "content": "Content"}
        ]
        
        hash1 = self.chunk_manager._generate_content_hash(messages1)
        hash2 = self.chunk_manager._generate_content_hash(messages2)
        hash3 = self.chunk_manager._generate_content_hash(messages3)
        
        # Same content should produce same hash
        assert hash1 == hash2
        # Different content should produce different hash
        assert hash1 != hash3
        # Hash should be 16 characters long
        assert len(hash1) == 16
    
    def test_create_message_chunks_small_list(self):
        """Test chunk creation with small message list"""
        messages = [
            {"role": "user", "content": f"Message {i}"} 
            for i in range(2)  # Less than chunk size
        ]
        
        chunks = self.chunk_manager._create_message_chunks(messages, is_vision=False)
        
        # Should create single chunk
        assert len(chunks) == 1
        assert chunks[0].start_index == 0
        assert chunks[0].end_index == 1
        assert len(chunks[0].messages) == 2
        assert chunks[0].state == ChunkState.UNPROCESSED
    
    def test_create_message_chunks_large_list(self):
        """Test chunk creation with large message list"""
        messages = [
            {"role": "user", "content": f"Message {i}"} 
            for i in range(8)  # More than chunk size (3)
        ]
        
        chunks = self.chunk_manager._create_message_chunks(messages, is_vision=False)
        
        # Should create multiple chunks
        assert len(chunks) > 1
        
        # Verify chunk boundaries
        for i, chunk in enumerate(chunks):
            assert len(chunk.messages) <= 3  # Should not exceed chunk size
            assert chunk.start_index >= 0
            assert chunk.end_index < len(messages)
            assert chunk.state == ChunkState.UNPROCESSED
    
    def test_identify_message_chunks_with_caching(self):
        """Test chunk identification with caching"""
        messages = [
            {"role": "user", "content": f"Message {i}"} 
            for i in range(6)
        ]
        
        # First call should create chunks
        chunks1 = self.chunk_manager.identify_message_chunks(messages, is_vision=False)
        assert len(chunks1) > 1
        
        # Second call should use cache
        chunks2 = self.chunk_manager.identify_message_chunks(messages, is_vision=False)
        assert len(chunks2) == len(chunks1)
        
        # Verify chunks are the same objects (cached)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.chunk_id == c2.chunk_id
    
    def test_get_chunk_id(self):
        """Test chunk ID generation"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
        
        chunk_id1 = self.chunk_manager.get_chunk_id(messages, is_vision=False)
        chunk_id2 = self.chunk_manager.get_chunk_id(messages, is_vision=True)
        chunk_id3 = self.chunk_manager.get_chunk_id(messages, is_vision=False)
        
        # Same messages and vision setting should produce same ID
        assert chunk_id1 == chunk_id3
        # Different vision setting should produce different ID
        assert chunk_id1 != chunk_id2
        # ID should start with "chunk_"
        assert chunk_id1.startswith("chunk_")
    
    def test_is_chunk_condensed(self):
        """Test chunk condensation state checking"""
        messages = [{"role": "user", "content": "Hello"}]
        chunk = MessageChunk(
            chunk_id="test_chunk",
            messages=messages,
            start_index=0,
            end_index=0,
            token_count=5,
            content_hash="abc123",
            created_at=1234567890.0,
            last_modified=1234567890.0,
            state=ChunkState.CONDENSED,
            condensed_content="Summarized",
            condensation_timestamp=1234567890.0,
            tokens_saved=3
        )
        
        # Should be condensed (recent)
        assert self.chunk_manager.is_chunk_condensed(chunk) == True
        
        # Should not be condensed (expired)
        chunk.condensation_timestamp = 1234567890.0 - 2000  # Older than threshold
        assert self.chunk_manager.is_chunk_condensed(chunk) == False
        assert chunk.state == ChunkState.EXPIRED
    
    def test_mark_chunk_condensed(self):
        """Test marking chunk as condensed"""
        messages = [{"role": "user", "content": "Hello"}]
        chunk = MessageChunk(
            chunk_id="test_chunk",
            messages=messages,
            start_index=0,
            end_index=0,
            token_count=5,
            content_hash="abc123",
            created_at=1234567890.0,
            last_modified=1234567890.0,
            state=ChunkState.UNPROCESSED
        )
        
        # Mark as condensed
        self.chunk_manager.mark_chunk_condensed(
            chunk, 
            "Summarized content", 
            "conversation_summary", 
            2
        )
        
        # Verify chunk is marked correctly
        assert chunk.state == ChunkState.CONDENSED
        assert chunk.condensed_content == "Summarized content"
        assert chunk.condensation_strategy == "conversation_summary"
        assert chunk.tokens_saved == 2
        assert chunk.condensation_timestamp is not None
    
    def test_get_condensed_chunk(self):
        """Test getting condensed version of chunk"""
        messages = [{"role": "user", "content": "Hello"}]
        chunk = MessageChunk(
            chunk_id="test_chunk",
            messages=messages,
            start_index=0,
            end_index=0,
            token_count=5,
            content_hash="abc123",
            created_at=1234567890.0,
            last_modified=1234567890.0,
            state=ChunkState.CONDENSED,
            condensed_content="Summarized",
            condensation_strategy="conversation_summary",
            condensation_timestamp=1234567890.0,
            tokens_saved=3
        )
        
        condensed = self.chunk_manager.get_condensed_chunk(chunk)
        
        assert condensed is not None
        assert condensed["role"] == "assistant"
        assert condensed["content"] == "Summarized"
        assert condensed["type"] == "condensed_chunk"
        assert condensed["chunk_id"] == "test_chunk"
        assert condensed["tokens_saved"] == 3
    
    def test_update_chunk(self):
        """Test updating chunk with new messages"""
        original_messages = [{"role": "user", "content": "Hello"}]
        new_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        chunk = MessageChunk(
            chunk_id="test_chunk",
            messages=original_messages,
            start_index=0,
            end_index=0,
            token_count=5,
            content_hash="abc123",
            created_at=1234567890.0,
            last_modified=1234567890.0,
            state=ChunkState.CONDENSED
        )
        
        # Update chunk
        updated_chunk = self.chunk_manager.update_chunk(chunk, new_messages)
        
        # Verify update
        assert updated_chunk.messages == new_messages
        assert updated_chunk.state == ChunkState.MODIFIED
        assert updated_chunk.last_modified > chunk.last_modified
        assert updated_chunk.content_hash != chunk.content_hash
    
    def test_analyze_chunks(self):
        """Test chunk analysis functionality"""
        # Create chunks with different states
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
            ),
            MessageChunk(
                chunk_id="chunk_3",
                messages=[{"role": "user", "content": "How are you?"}],
                start_index=2,
                end_index=2,
                token_count=4,
                content_hash="ghi789",
                created_at=1234567890.0,
                last_modified=1234567890.0,
                state=ChunkState.MODIFIED
            )
        ]
        
        analysis = self.chunk_manager.analyze_chunks(chunks)
        
        assert isinstance(analysis, ChunkAnalysisResult)
        assert analysis.total_chunks == 3
        assert lenanalysis.condensed_chunks == 1
        assert len(analysis.uncondensed_chunks) == 2  # UNPROCESSED + MODIFIED
        assert len(analysis.modified_chunks) == 1
        assert analysis.total_tokens == 12
        assert analysis.estimated_condensation_savings >= 2  # At least the actual savings
    
    def test_get_cache_stats(self):
        """Test cache statistics retrieval"""
        stats = self.chunk_manager.get_cache_stats()
        
        assert isinstance(stats, dict)
        assert "chunks_cache_size" in stats
        assert "state_cache_size" in stats
        assert "chunk_states" in stats
        assert "persistence_enabled" in stats
        assert stats["persistence_enabled"] == True
        assert stats["chunk_size_messages"] == 3
        assert stats["chunk_max_tokens"] == 100
    
    def test_clear_caches(self):
        """Test cache clearing functionality"""
        # Add some data to caches
        self.chunk_manager.chunks_cache["test"] = []
        self.chunk_manager.chunk_state_cache["test"] = (ChunkState.CONDENSED, 1234567890.0)
        
        # Clear caches
        self.chunk_manager.clear_caches()
        
        # Verify caches are empty
        assert len(self.chunk_manager.chunks_cache) == 0
        assert len(self.chunk_manager.chunk_state_cache) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_chunks(self):
        """Test cleanup of expired chunks"""
        # Add some expired state cache entries
        old_timestamp = 1234567890.0  # Very old timestamp
        self.chunk_manager.chunk_state_cache["expired1"] = (ChunkState.CONDENSED, old_timestamp)
        self.chunk_manager.chunk_state_cache["expired2"] = (ChunkState.UNPROCESSED, old_timestamp)
        
        # Clean up expired chunks
        cleaned_count = await self.chunk_manager.cleanup_expired_chunks()
        
        # Verify expired entries were removed
        assert cleaned_count >= 2
        assert len(self.chunk_manager.chunk_state_cache) == 0
    
    def test_fallback_chunks_when_disabled(self):
        """Test fallback chunk creation when chunk-based condensation is disabled"""
        with patch('message_chunk_manager.ENABLE_CHUNK_BASED_CONDENSATION', False):
            messages = [
                {"role": "user", "content": f"Message {i}"} 
                for i in range(10)
            ]
            
            chunks = self.chunk_manager.identify_message_chunks(messages, is_vision=False)
            
            # Should create single fallback chunk
            assert len(chunks) == 1
            assert chunks[0].metadata.get("fallback") == True
            assert len(chunks[0].messages) == 10

class TestGlobalChunkManager:
    """Test global chunk manager instance functionality"""
    
    def test_get_chunk_manager_singleton(self):
        """Test that get_chunk_manager returns singleton instance"""
        manager1 = get_chunk_manager()
        manager2 = get_chunk_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, MessageChunkManager)

class TestChunkIntegration:
    """Test integration with existing systems"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        self.env_patches = [
            patch('message_chunk_manager.ENABLE_CHUNK_BASED_CONDENSATION', True),
            patch('message_chunk_manager.CACHE_DIR', self.temp_dir),
            patch('message_chunk_manager.ENABLE_CHUNK_PERSISTENCE', True)
        ]
        
        for p in self.env_patches:
            p.start()
        
        self.chunk_manager = MessageChunkManager()
    
    def teardown_method(self):
        """Clean up after each test"""
        for p in self.env_patches:
            p.stop()
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('message_chunk_manager.count_tokens_accurate')
    def test_token_counting_integration(self, mock_count_tokens):
        """Test integration with token counting system"""
        mock_count_tokens.return_value = 10
        
        messages = [{"role": "user", "content": "Hello"}]
        chunks = self.chunk_manager.identify_message_chunks(messages, is_vision=False)
        
        # Verify token counting was called
        mock_count_tokens.assert_called()
        assert chunks[0].token_count == 10
    
    def test_error_handling(self):
        """Test error handling in chunk operations"""
        # Test with invalid messages
        invalid_messages = [{"invalid": "structure"}]
        
        # Should handle gracefully and return fallback chunks
        chunks = self.chunk_manager.identify_message_chunks(invalid_messages, is_vision=False)
        assert len(chunks) >= 1  # Should at least create fallback chunks

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])