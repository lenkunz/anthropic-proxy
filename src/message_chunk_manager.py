#!/usr/bin/env python3
"""
Message Chunk Management System for Anthropic Proxy

This module provides intelligent message chunk management to avoid re-condensing
already processed chunks, especially for image endpoints. It implements chunk-based
caching, condensation state tracking, and intelligent chunk identification.

Key Features:
- Message chunk identification with content-based hashing
- Condensation state tracking with persistent storage
- Chunk-based caching to avoid re-condensation
- Intelligent chunk boundary detection
- Integration with existing condensation system
"""

import os
import json
import hashlib
import time
import asyncio
import aiofiles
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path
import pickle

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import existing components
try:
    from .accurate_token_counter import count_tokens_accurate
    from .async_logging import log_error_fire_and_forget
except ImportError:
    # Fallback implementations
    def count_tokens_accurate(messages, **kwargs):
        return sum(len(str(msg.get('content', ''))) for msg in messages)
    
    def log_error_fire_and_forget(error_msg, **kwargs):
        print(f"[ERROR] {error_msg}")

# Configuration
ENABLE_CHUNK_BASED_CONDENSATION = os.getenv("ENABLE_CHUNK_BASED_CONDENSATION", "true").lower() in ("true", "1", "yes")
CHUNK_SIZE_MESSAGES = int(os.getenv("CHUNK_SIZE_MESSAGES", "8"))
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "4000"))
CHUNK_OVERLAP_MESSAGES = int(os.getenv("CHUNK_OVERLAP_MESSAGES", "2"))
CHUNK_CACHE_SIZE = int(os.getenv("CHUNK_CACHE_SIZE", "100"))
CHUNK_CACHE_TTL = int(os.getenv("CHUNK_CACHE_TTL", "3600"))
ENABLE_CHUNK_PERSISTENCE = os.getenv("ENABLE_CHUNK_PERSISTENCE", "true").lower() in ("true", "1", "yes")
CHUNK_CONDENSATION_STRATEGY = os.getenv("CHUNK_CONDENSATION_STRATEGY", "auto")
SKIP_CONDENSED_CHUNKS = os.getenv("SKIP_CONDENSED_CHUNKS", "true").lower() in ("true", "1", "yes")
CHUNK_AGE_THRESHOLD = int(os.getenv("CHUNK_AGE_THRESHOLD", "1800"))
CACHE_DIR = os.getenv("CACHE_DIR", "./cache")

class ChunkState(Enum):
    """Represents the condensation state of a message chunk"""
    UNPROCESSED = "unprocessed"
    CONDENSING = "condensing"
    CONDENSED = "condensed"
    MODIFIED = "modified"
    EXPIRED = "expired"

@dataclass
class MessageChunk:
    """Represents a chunk of messages with metadata"""
    chunk_id: str
    messages: List[Dict[str, Any]]
    start_index: int
    end_index: int
    token_count: int
    content_hash: str
    created_at: float
    last_modified: float
    state: ChunkState
    condensation_strategy: Optional[str] = None
    condensed_content: Optional[str] = None
    condensation_timestamp: Optional[float] = None
    tokens_saved: int = 0
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class ChunkAnalysisResult:
    """Result of chunk analysis"""
    chunks: List[MessageChunk]
    total_chunks: int
    uncondensed_chunks: List[MessageChunk]
    condensed_chunks: List[MessageChunk]
    modified_chunks: List[MessageChunk]
    total_tokens: int
    estimated_condensation_savings: int

class MessageChunkManager:
    """Manages message chunks with intelligent condensation tracking"""
    
    def __init__(self):
        self.chunks_cache: Dict[str, MessageChunk] = {}
        self.chunk_state_cache: Dict[str, Tuple[ChunkState, float]] = {}
        self.persistence_dir = Path(CACHE_DIR) / "chunks"
        self.debug_logger = self._create_debug_logger()
        
        # Initialize persistence directory
        if ENABLE_CHUNK_PERSISTENCE:
            try:
                self.persistence_dir.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                # Fallback to a temporary directory if we can't create the cache directory
                import tempfile
                self.persistence_dir = Path(tempfile.gettempdir()) / "anthropic_proxy_chunks"
                self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        # Note: Chunk state loading is deferred to avoid async issues in constructor
        # State will be loaded on-demand when accessed
    
    def _create_debug_logger(self):
        """Create a simple debug logger"""
        class DebugLogger:
            def debug(self, msg): print(f"[CHUNK_MANAGER] {msg}")
            def info(self, msg): print(f"[CHUNK_MANAGER] {msg}")
            def warning(self, msg): print(f"[CHUNK_MANAGER] {msg}")
            def error(self, msg): print(f"[CHUNK_MANAGER] {msg}")
        return DebugLogger()
    
    def identify_message_chunks(self, 
                              messages: List[Dict[str, Any]], 
                              is_vision: bool = False,
                              force_rechunk: bool = False) -> List[MessageChunk]:
        """
        Identify and group messages into chunks based on content and configuration
        
        Args:
            messages: List of message dictionaries
            is_vision: Whether this is a vision request
            force_rechunk: Force re-chunking even if chunks exist in cache
            
        Returns:
            List of MessageChunk objects
        """
        if not ENABLE_CHUNK_BASED_CONDENSATION:
            return self._create_fallback_chunks(messages)
        
        start_time = time.time()
        
        try:
            # Check if we can reuse existing chunks
            content_hash = self._generate_content_hash(messages)
            cache_key = f"chunks_{content_hash}_{is_vision}"
            
            if not force_rechunk and cache_key in self.chunks_cache:
                cached_chunks = self.chunks_cache[cache_key]
                self.debug_logger.info(f"Using cached chunks: {len(cached_chunks)} chunks")
                return cached_chunks
            
            # Create new chunks
            chunks = self._create_message_chunks(messages, is_vision)
            
            # Cache the chunks
            self.chunks_cache[cache_key] = chunks
            
            # Limit cache size
            if len(self.chunks_cache) > CHUNK_CACHE_SIZE:
                oldest_key = min(self.chunks_cache.keys(), 
                               key=lambda k: self.chunks_cache[k][0].created_at if self.chunks_cache[k] else 0)
                del self.chunks_cache[oldest_key]
            
            self.debug_logger.info(f"Created {len(chunks)} chunks in {time.time() - start_time:.3f}s")
            return chunks
            
        except Exception as e:
            self.debug_logger.error(f"Chunk identification failed: {e}")
            log_error_fire_and_forget(f"MessageChunkManager.identify_message_chunks failed: {e}")
            return self._create_fallback_chunks(messages)
    
    def _create_message_chunks(self, 
                              messages: List[Dict[str, Any]], 
                              is_vision: bool) -> List[MessageChunk]:
        """Create message chunks based on configuration"""
        chunks = []
        current_chunk_messages = []
        current_chunk_tokens = 0
        start_index = 0
        
        for i, message in enumerate(messages):
            # Calculate message token count
            message_tokens = count_tokens_accurate([message], 
                                                 endpoint_type="openai" if is_vision else "anthropic")
            
            # Check if adding this message would exceed chunk limits
            would_exceed = (
                len(current_chunk_messages) >= CHUNK_SIZE_MESSAGES or
                current_chunk_tokens + message_tokens > CHUNK_MAX_TOKENS
            )
            
            if would_exceed and current_chunk_messages:
                # Create chunk from current messages
                chunk = self._create_chunk_from_messages(
                    current_chunk_messages, start_index, i - 1, is_vision
                )
                chunks.append(chunk)
                
                # Start new chunk with overlap if configured
                overlap_start = max(0, len(current_chunk_messages) - CHUNK_OVERLAP_MESSAGES)
                current_chunk_messages = current_chunk_messages[overlap_start:]
                current_chunk_tokens = sum(
                    count_tokens_accurate([msg], 
                                        endpoint_type="openai" if is_vision else "anthropic")
                    for msg in current_chunk_messages
                )
                start_index = i - len(current_chunk_messages)
            
            # Add current message to chunk
            current_chunk_messages.append(message)
            current_chunk_tokens += message_tokens
        
        # Create final chunk if there are remaining messages
        if current_chunk_messages:
            chunk = self._create_chunk_from_messages(
                current_chunk_messages, start_index, len(messages) - 1, is_vision
            )
            chunks.append(chunk)
        
        return chunks
    
    def _create_chunk_from_messages(self, 
                                   messages: List[Dict[str, Any]], 
                                   start_index: int,
                                   end_index: int,
                                   is_vision: bool) -> MessageChunk:
        """Create a MessageChunk from a list of messages"""
        content_hash = self._generate_content_hash(messages)
        token_count = count_tokens_accurate(messages, 
                                          endpoint_type="openai" if is_vision else "anthropic")
        current_time = time.time()
        
        # Check if this chunk was previously condensed
        chunk_id = f"chunk_{content_hash}_{is_vision}"
        state, timestamp = self._get_chunk_state(chunk_id)
        
        # Check if chunk state is still valid
        if state == ChunkState.CONDENSED and timestamp:
            age = current_time - timestamp
            if age > CHUNK_AGE_THRESHOLD:
                state = ChunkState.EXPIRED
        
        return MessageChunk(
            chunk_id=chunk_id,
            messages=messages,
            start_index=start_index,
            end_index=end_index,
            token_count=token_count,
            content_hash=content_hash,
            created_at=current_time,
            last_modified=current_time,
            state=state,
            metadata={
                "is_vision": is_vision,
                "message_count": len(messages),
                "creation_strategy": "auto"
            }
        )
    
    def _create_fallback_chunks(self, messages: List[Dict[str, Any]]) -> List[MessageChunk]:
        """Create fallback chunks when chunk-based condensation is disabled"""
        if not messages:
            return []
        
        # Create a single chunk containing all messages
        content_hash = self._generate_content_hash(messages)
        current_time = time.time()
        
        return [MessageChunk(
            chunk_id=f"fallback_{content_hash}",
            messages=messages,
            start_index=0,
            end_index=len(messages) - 1,
            token_count=count_tokens_accurate(messages),
            content_hash=content_hash,
            created_at=current_time,
            last_modified=current_time,
            state=ChunkState.UNPROCESSED,
            metadata={"fallback": True}
        )]
    
    def _generate_content_hash(self, messages: List[Dict[str, Any]]) -> str:
        """Generate a content hash for messages"""
        hash_input = []
        for msg in messages:
            # Include relevant fields for hash calculation
            msg_content = {
                "role": msg.get("role", ""),
                "content": str(msg.get("content", "")),
                "type": msg.get("type", "")
            }
            # Handle different content formats
            if isinstance(msg.get("content"), list):
                msg_content["content"] = json.dumps(msg.get("content", []), sort_keys=True)
            
            hash_input.append(json.dumps(msg_content, sort_keys=True))
        
        return hashlib.sha256("".join(hash_input).encode()).hexdigest()[:16]
    
    def get_chunk_id(self, messages: List[Dict[str, Any]], is_vision: bool = False) -> str:
        """Generate a unique chunk ID for a set of messages"""
        content_hash = self._generate_content_hash(messages)
        return f"chunk_{content_hash}_{is_vision}"
    
    def is_chunk_condensed(self, chunk: MessageChunk) -> bool:
        """Check if a chunk is already condensed"""
        if not SKIP_CONDENSED_CHUNKS:
            return False
        
        # Check current state
        if chunk.state == ChunkState.CONDENSED:
            # Check if condensation is still valid
            if chunk.condensation_timestamp:
                age = time.time() - chunk.condensation_timestamp
                if age <= CHUNK_AGE_THRESHOLD:
                    return True
                else:
                    # Mark as expired
                    chunk.state = ChunkState.EXPIRED
                    self._update_chunk_state(chunk.chunk_id, ChunkState.EXPIRED)
        
        return False
    
    def mark_chunk_condensed(self, 
                           chunk: MessageChunk, 
                           condensed_content: str,
                           strategy: str,
                           tokens_saved: int) -> None:
        """Mark a chunk as condensed with metadata"""
        chunk.state = ChunkState.CONDENSED
        chunk.condensed_content = condensed_content
        chunk.condensation_strategy = strategy
        chunk.condensation_timestamp = time.time()
        chunk.tokens_saved = tokens_saved
        chunk.last_modified = time.time()
        
        # Update state cache
        self._update_chunk_state(chunk.chunk_id, ChunkState.CONDENSED)
        
        # Persist if enabled
        if ENABLE_CHUNK_PERSISTENCE:
            asyncio.create_task(self._persist_chunk_state(chunk))
        
        self.debug_logger.info(f"Marked chunk {chunk.chunk_id} as condensed, saved {tokens_saved} tokens")
    
    def get_condensed_chunk(self, chunk: MessageChunk) -> Optional[Dict[str, Any]]:
        """Get the condensed version of a chunk"""
        if self.is_chunk_condensed(chunk) and chunk.condensed_content:
            return {
                "role": "assistant",
                "content": chunk.condensed_content,
                "type": "condensed_chunk",
                "chunk_id": chunk.chunk_id,
                "original_tokens": chunk.token_count,
                "tokens_saved": chunk.tokens_saved,
                "strategy": chunk.condensation_strategy,
                "condensed_at": chunk.condensation_timestamp
            }
        return None
    
    def update_chunk(self, chunk: MessageChunk, messages: List[Dict[str, Any]]) -> MessageChunk:
        """Update a chunk with new messages"""
        new_hash = self._generate_content_hash(messages)
        
        # Check if content actually changed
        if new_hash == chunk.content_hash:
            return chunk
        
        # Create updated chunk
        updated_chunk = MessageChunk(
            chunk_id=chunk.chunk_id,
            messages=messages,
            start_index=chunk.start_index,
            end_index=chunk.end_index,
            token_count=count_tokens_accurate(messages),
            content_hash=new_hash,
            created_at=chunk.created_at,
            last_modified=time.time(),
            state=ChunkState.MODIFIED,
            condensation_strategy=chunk.condensation_strategy,
            condensed_content=chunk.condensed_content,
            condensation_timestamp=chunk.condensation_timestamp,
            tokens_saved=chunk.tokens_saved,
            metadata=chunk.metadata
        )
        
        # Update state cache
        self._update_chunk_state(chunk.chunk_id, ChunkState.MODIFIED)
        
        return updated_chunk
    
    def analyze_chunks(self, chunks: List[MessageChunk]) -> ChunkAnalysisResult:
        """Analyze chunks to determine condensation needs"""
        uncondensed_chunks = []
        condensed_chunks = []
        modified_chunks = []
        total_tokens = 0
        estimated_savings = 0
        
        for chunk in chunks:
            total_tokens += chunk.token_count
            
            if self.is_chunk_condensed(chunk):
                condensed_chunks.append(chunk)
                estimated_savings += chunk.tokens_saved
            elif chunk.state == ChunkState.MODIFIED:
                modified_chunks.append(chunk)
                uncondensed_chunks.append(chunk)
            else:
                uncondensed_chunks.append(chunk)
                # Estimate potential savings (rough estimate: 30% reduction)
                estimated_savings += int(chunk.token_count * 0.3)
        
        return ChunkAnalysisResult(
            chunks=chunks,
            total_chunks=len(chunks),
            uncondensed_chunks=uncondensed_chunks,
            condensed_chunks=condensed_chunks,
            modified_chunks=modified_chunks,
            total_tokens=total_tokens,
            estimated_condensation_savings=estimated_savings
        )
    
    def _get_chunk_state(self, chunk_id: str) -> Tuple[ChunkState, Optional[float]]:
        """Get the current state of a chunk"""
        if chunk_id in self.chunk_state_cache:
            state, timestamp = self.chunk_state_cache[chunk_id]
            # Check if state is still valid
            if timestamp and time.time() - timestamp < CHUNK_CACHE_TTL:
                return state, timestamp
            else:
                # Remove expired entry
                del self.chunk_state_cache[chunk_id]
        
        # Try to load from persistence (synchronous fallback)
        if ENABLE_CHUNK_PERSISTENCE:
            try:
                state_file = self.persistence_dir / f"{chunk_id}_state.json"
                if state_file.exists():
                    with open(state_file, 'r') as f:
                        data = json.loads(f.read())
                        state = ChunkState(data.get("state", "unprocessed"))
                        timestamp = data.get("timestamp", time.time())
                        
                        # Cache the loaded state
                        self.chunk_state_cache[chunk_id] = (state, timestamp)
                        return state, timestamp
            except Exception as e:
                self.debug_logger.warning(f"Failed to load chunk state for {chunk_id}: {e}")
        
        return ChunkState.UNPROCESSED, None
    
    def _update_chunk_state(self, chunk_id: str, state: ChunkState) -> None:
        """Update the state of a chunk"""
        self.chunk_state_cache[chunk_id] = (state, time.time())
    
    async def _persist_chunk_state(self, chunk: MessageChunk) -> None:
        """Persist chunk state to storage"""
        if not ENABLE_CHUNK_PERSISTENCE:
            return
        
        try:
            state_file = self.persistence_dir / f"{chunk.chunk_id}_state.json"
            state_data = {
                "chunk_id": chunk.chunk_id,
                "state": chunk.state.value,
                "timestamp": chunk.condensation_timestamp or time.time(),
                "strategy": chunk.condensation_strategy,
                "tokens_saved": chunk.tokens_saved,
                "content_hash": chunk.content_hash
            }
            
            async with aiofiles.open(state_file, 'w') as f:
                await f.write(json.dumps(state_data, indent=2))
            
            # Also persist condensed content if available
            if chunk.condensed_content:
                content_file = self.persistence_dir / f"{chunk.chunk_id}_content.json"
                content_data = {
                    "chunk_id": chunk.chunk_id,
                    "condensed_content": chunk.condensed_content,
                    "condensed_at": chunk.condensation_timestamp,
                    "original_messages": chunk.messages
                }
                
                async with aiofiles.open(content_file, 'w') as f:
                    await f.write(json.dumps(content_data, indent=2))
                    
        except Exception as e:
            self.debug_logger.error(f"Failed to persist chunk state for {chunk.chunk_id}: {e}")
            log_error_fire_and_forget(f"MessageChunkManager._persist_chunk_state failed: {e}")
    
    async def _load_chunk_state(self) -> None:
        """Load chunk state from persistent storage"""
        if not ENABLE_CHUNK_PERSISTENCE or not self.persistence_dir.exists():
            return
        
        try:
            state_files = list(self.persistence_dir.glob("*_state.json"))
            loaded_count = 0
            
            for state_file in state_files:
                try:
                    async with aiofiles.open(state_file, 'r') as f:
                        data = json.loads(await f.read())
                        chunk_id = data.get("chunk_id")
                        state = ChunkState(data.get("state", "unprocessed"))
                        timestamp = data.get("timestamp", time.time())
                        
                        if chunk_id:
                            self.chunk_state_cache[chunk_id] = (state, timestamp)
                            loaded_count += 1
                            
                except Exception as e:
                    self.debug_logger.warning(f"Failed to load state file {state_file}: {e}")
            
            self.debug_logger.info(f"Loaded {loaded_count} chunk states from persistence")
            
        except Exception as e:
            self.debug_logger.error(f"Failed to load chunk state: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        total_chunks = len(self.chunks_cache)
        state_cache_size = len(self.chunk_state_cache)
        
        # Count chunks by state
        state_counts = {}
        for chunk_list in self.chunks_cache.values():
            for chunk in chunk_list:
                state = chunk.state.value
                state_counts[state] = state_counts.get(state, 0) + 1
        
        return {
            "chunks_cache_size": total_chunks,
            "state_cache_size": state_cache_size,
            "chunk_states": state_counts,
            "persistence_enabled": ENABLE_CHUNK_PERSISTENCE,
            "persistence_dir": str(self.persistence_dir),
            "chunk_size_messages": CHUNK_SIZE_MESSAGES,
            "chunk_max_tokens": CHUNK_MAX_TOKENS,
            "chunk_cache_ttl": CHUNK_CACHE_TTL
        }
    
    def clear_caches(self) -> None:
        """Clear all caches"""
        self.chunks_cache.clear()
        self.chunk_state_cache.clear()
        self.debug_logger.info("Cleared all chunk caches")
    
    async def cleanup_expired_chunks(self) -> int:
        """Clean up expired chunks and return count of cleaned items"""
        if not ENABLE_CHUNK_PERSISTENCE:
            return 0
        
        cleaned_count = 0
        current_time = time.time()
        
        try:
            # Clean up state cache
            expired_keys = []
            for chunk_id, (_, timestamp) in self.chunk_state_cache.items():
                if timestamp and current_time - timestamp > CHUNK_CACHE_TTL:
                    expired_keys.append(chunk_id)
            
            for key in expired_keys:
                del self.chunk_state_cache[key]
                cleaned_count += 1
            
            # Clean up persistence files
            if self.persistence_dir.exists():
                state_files = list(self.persistence_dir.glob("*_state.json"))
                content_files = list(self.persistence_dir.glob("*_content.json"))
                
                for file_path in state_files + content_files:
                    try:
                        file_time = file_path.stat().st_mtime
                        if current_time - file_time > CHUNK_CACHE_TTL:
                            file_path.unlink()
                            cleaned_count += 1
                    except Exception as e:
                        self.debug_logger.warning(f"Failed to delete expired file {file_path}: {e}")
            
            self.debug_logger.info(f"Cleaned up {cleaned_count} expired chunk items")
            
        except Exception as e:
            self.debug_logger.error(f"Chunk cleanup failed: {e}")
            log_error_fire_and_forget(f"MessageChunkManager.cleanup_expired_chunks failed: {e}")
        
        return cleaned_count

# Global chunk manager instance
_chunk_manager = None

def get_chunk_manager() -> MessageChunkManager:
    """Get the global chunk manager instance"""
    global _chunk_manager
    if _chunk_manager is None:
        _chunk_manager = MessageChunkManager()
    return _chunk_manager

async def cleanup_expired_chunks_periodically():
    """Periodically clean up expired chunks"""
    chunk_manager = get_chunk_manager()
    while True:
        try:
            await asyncio.sleep(CHUNK_CACHE_TTL // 2)  # Clean up half-way through TTL
            cleaned = await chunk_manager.cleanup_expired_chunks()
            if cleaned > 0:
                chunk_manager.debug_logger.info(f"Periodic cleanup: removed {cleaned} expired items")
        except Exception as e:
            chunk_manager.debug_logger.error(f"Periodic cleanup failed: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retrying