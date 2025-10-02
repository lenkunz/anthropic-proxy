#!/usr/bin/env python3
"""
Environment Details Deduplication System for Anthropic Proxy

This module provides intelligent environment details deduplication to reduce token usage
by removing redundant environment details that are often sent by clients like Kilo.

Features:
- Pattern matching for various environment details formats
- Content analysis and comparison algorithms
- Multiple deduplication strategies
- Integration with existing context management
- Performance optimization with caching
- Configurable deduplication behavior
"""

import os
import re
import json
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ENABLE_ENV_DEDUPLICATION = os.getenv("ENABLE_ENV_DEDUPLICATION", "true").lower() in ("true", "1", "yes")
ENV_DEDUPLICATION_STRATEGY = os.getenv("ENV_DEDUPLICATION_STRATEGY", "keep_latest")
ENV_DETAILS_MAX_AGE_MINUTES = int(os.getenv("ENV_DETAILS_MAX_AGE_MINUTES", "30"))
ENV_DEDUPLICATION_LOGGING = os.getenv("ENV_DEDUPLICATION_LOGGING", "false").lower() in ("true", "1", "yes")
ENV_DEDUPLICATION_STATS = os.getenv("ENV_DEDUPLICATION_STATS", "true").lower() in ("true", "1", "yes")

# Environment details patterns
DEFAULT_ENV_PATTERNS = [
    r'<environment_details>.*?</environment_details>',
]

# Only use the specific environment_details tag - no custom patterns
ALL_ENV_PATTERNS = DEFAULT_ENV_PATTERNS


class DeduplicationStrategy(Enum):
    """Strategies for environment details deduplication."""
    KEEP_LATEST = "keep_latest"
    KEEP_MOST_RELEVANT = "keep_most_relevant"
    REMOVE_ALL = "remove_all"
    MERGE_STRATEGY = "merge_strategy"
    SELECTIVE_REMOVAL = "selective_removal"


@dataclass
class EnvironmentDetailsBlock:
    """Represents a detected environment details block."""
    content: str
    start_index: int
    end_index: int
    pattern_used: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_index: int = 0
    relevance_score: float = 0.0
    unique_id: str = field(default="")
    
    def __post_init__(self):
        if not self.unique_id:
            self.unique_id = hashlib.md5(self.content.encode()).hexdigest()[:16]


@dataclass
class DeduplicationResult:
    """Result of environment details deduplication."""
    original_messages: List[Dict[str, Any]]
    deduplicated_messages: List[Dict[str, Any]]
    removed_blocks: List[EnvironmentDetailsBlock]
    kept_blocks: List[EnvironmentDetailsBlock]
    tokens_saved: int
    processing_time: float
    strategy_used: DeduplicationStrategy


class SimpleLogger:
    """Simple logger for environment details deduplication."""
    def debug(self, msg): 
        if ENV_DEDUPLICATION_LOGGING:
            print(f"[ENV_DEDUP] {msg}")
    def info(self, msg): 
        if ENV_DEDUPLICATION_LOGGING:
            print(f"[ENV_DEDUP] {msg}")
    def warning(self, msg): 
        if ENV_DEDUPLICATION_LOGGING:
            print(f"[ENV_DEDUP] {msg}")
    def error(self, msg): 
        if ENV_DEDUPLICATION_LOGGING:
            print(f"[ENV_DEDUP] {msg}")


class EnvironmentDetailsManager:
    """
    Main class for environment details detection and deduplication.
    
    This class provides comprehensive environment details deduplication functionality
    including pattern detection, content analysis, and multiple deduplication strategies.
    """
    
    def __init__(self):
        """Initialize the environment details manager."""
        self.logger = SimpleLogger()
        self.enabled = ENABLE_ENV_DEDUPLICATION
        self.strategy = DeduplicationStrategy(ENV_DEDUPLICATION_STRATEGY)
        self.max_age_minutes = ENV_DETAILS_MAX_AGE_MINUTES
        
        # Compile regex patterns for performance
        self.compiled_patterns = [re.compile(pattern, re.DOTALL | re.IGNORECASE) 
                                 for pattern in ALL_ENV_PATTERNS]
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'total_blocks_found': 0,
            'total_blocks_removed': 0,
            'total_tokens_saved': 0,
            'total_processing_time': 0.0,
            'strategy_usage': {strategy.value: 0 for strategy in DeduplicationStrategy}
        }
        
        self.logger.info(f"Initialized EnvironmentDetailsManager (enabled={self.enabled}, strategy={self.strategy.value})")
    
    def detect_environment_details(self, content: str, message_index: int = 0) -> List[EnvironmentDetailsBlock]:
        """
        Detect environment details blocks in content using pattern matching.
        
        Args:
            content: Text content to search for environment details
            message_index: Index of the message in the conversation
            
        Returns:
            List of detected environment details blocks
        """
        if not content or not self.enabled:
            return []
        
        blocks = []
        
        for i, pattern in enumerate(self.compiled_patterns):
            matches = pattern.finditer(content)
            for match in matches:
                block = EnvironmentDetailsBlock(
                    content=match.group(0).strip(),
                    start_index=match.start(),
                    end_index=match.end(),
                    pattern_used=ALL_ENV_PATTERNS[i],
                    message_index=message_index
                )
                blocks.append(block)
        
        # Remove overlapping blocks (keep the longest/most specific)
        blocks = self._remove_overlapping_blocks(blocks)
        
        self.logger.debug(f"Detected {len(blocks)} environment details blocks in message {message_index}")
        return blocks
    
    def _remove_overlapping_blocks(self, blocks: List[EnvironmentDetailsBlock]) -> List[EnvironmentDetailsBlock]:
        """Remove overlapping environment details blocks, keeping the most comprehensive ones."""
        if not blocks:
            return []
        
        # Sort by start position, then by length (longer first)
        blocks.sort(key=lambda b: (b.start_index, -len(b.content)))
        
        non_overlapping = []
        for block in blocks:
            # Check if this block overlaps with any already selected block
            overlaps = any(
                block.start_index < existing.end_index and block.end_index > existing.start_index
                for existing in non_overlapping
            )
            
            if not overlaps:
                non_overlapping.append(block)
        
        return non_overlapping
    
    def compare_environment_details(self, blocks: List[EnvironmentDetailsBlock]) -> Dict[str, Any]:
        """
        Compare environment details blocks to identify duplicates and relationships.
        
        Args:
            blocks: List of environment details blocks to compare
            
        Returns:
            Comparison analysis with duplicates and relationships
        """
        if len(blocks) < 2:
            return {'duplicates': [], 'similar': [], 'unique': blocks}
        
        duplicates = []
        similar = []
        unique = []
        processed = set()
        
        for i, block1 in enumerate(blocks):
            if i in processed:
                continue
                
            is_duplicate = False
            duplicate_group = [block1]
            
            for j, block2 in enumerate(blocks[i+1:], i+1):
                if j in processed:
                    continue
                
                similarity = self._calculate_content_similarity(block1.content, block2.content)
                
                if similarity >= 0.9:  # Near duplicate
                    duplicate_group.append(block2)
                    processed.add(j)
                    is_duplicate = True
                elif similarity >= 0.7:  # Similar content
                    similar.append((block1, block2, similarity))
            
            if is_duplicate and len(duplicate_group) > 1:
                duplicates.append(duplicate_group)
                processed.add(i)
            elif not is_duplicate:
                unique.append(block1)
        
        return {
            'duplicates': duplicates,
            'similar': similar,
            'unique': unique
        }
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """
        Calculate similarity between two content strings.
        
        Args:
            content1: First content string
            content2: Second content string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize content for comparison
        normalized1 = self._normalize_content(content1)
        normalized2 = self._normalize_content(content2)
        
        if not normalized1 or not normalized2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(normalized1.lower().split())
        words2 = set(normalized2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison by removing noise and standardizing format."""
        # Only remove code block markers, preserve ALL XML content completely
        # since environment_details are now handled as separate messages
        content = re.sub(r'```(environment|env)\n', '', content)
        content = re.sub(r'```$', '', content)
        
        # Only normalize line endings, preserve all XML structure and content
        content = content.strip()
        
        return content

    def is_environment_details_message(self, message: Dict[str, Any]) -> bool:
        """
        Check if a message contains environment details.
        
        Args:
            message: Message dictionary to check
            
        Returns:
            True if this message contains environment details
        """
        if not isinstance(message, dict):
            return False
            
        content = message.get("content", "")
        if isinstance(content, str):
            # Check if content contains <environment_details> anywhere
            return "<environment_details>" in content
        elif isinstance(content, list):
            # Handle multipart content
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text", "")
                    if "<environment_details>" in text:
                        return True
        return False
    
    def deduplicate_environment_details(self, messages: List[Dict[str, Any]]) -> DeduplicationResult:
        """
        Main entry point for environment details deduplication.
        
        Args:
            messages: List of messages to process
            
        Returns:
            DeduplicationResult with processed messages and statistics
        """
        start_time = time.time()
        
        if not self.enabled or not messages:
            return DeduplicationResult(
                original_messages=messages.copy(),
                deduplicated_messages=messages.copy(),
                removed_blocks=[],
                kept_blocks=[],
                tokens_saved=0,
                processing_time=time.time() - start_time,
                strategy_used=self.strategy
            )
        
        # Detect environment details messages using the new approach
        all_blocks = []
        for i, message in enumerate(messages):
            if self.is_environment_details_message(message):
                # Extract environment details content from the message
                content = self._extract_message_content(message)
                if content:
                    # Find all environment_details blocks in this message
                    env_blocks = self.detect_environment_details(content, i)
                    all_blocks.extend(env_blocks)
        
        if not all_blocks:
            return DeduplicationResult(
                original_messages=messages.copy(),
                deduplicated_messages=messages.copy(),
                removed_blocks=[],
                kept_blocks=[],
                tokens_saved=0,
                processing_time=time.time() - start_time,
                strategy_used=self.strategy
            )
        
        # Analyze and deduplicate based on strategy
        result = self._apply_deduplication_strategy(messages, all_blocks)
        result.processing_time = time.time() - start_time
        
        # Update statistics
        self._update_stats(result)
        
        self.logger.info(f"Deduplicated {len(result.removed_blocks)} blocks, saved {result.tokens_saved} tokens")
        
        return result
    
    def _extract_message_content(self, message: Dict[str, Any]) -> str:
        """Extract text content from a message object."""
        content_parts = []
        
        if 'content' in message:
            content = message['content']
            if isinstance(content, str):
                content_parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'text':
                        content_parts.append(part.get('text', ''))
        
        return ' '.join(content_parts)
    
    def _apply_deduplication_strategy(self, messages: List[Dict[str, Any]], 
                                    blocks: List[EnvironmentDetailsBlock]) -> DeduplicationResult:
        """Apply the configured deduplication strategy."""
        if self.strategy == DeduplicationStrategy.KEEP_LATEST:
            return self._keep_latest_strategy(messages, blocks)
        elif self.strategy == DeduplicationStrategy.KEEP_MOST_RELEVANT:
            return self._keep_most_relevant_strategy(messages, blocks)
        elif self.strategy == DeduplicationStrategy.MERGE_STRATEGY:
            return self._merge_strategy(messages, blocks)
        elif self.strategy == DeduplicationStrategy.SELECTIVE_REMOVAL:
            return self._selective_removal_strategy(messages, blocks)
        else:
            # Fallback to keep latest
            return self._keep_latest_strategy(messages, blocks)
    
    def _keep_latest_strategy(self, messages: List[Dict[str, Any]], 
                            blocks: List[EnvironmentDetailsBlock]) -> DeduplicationResult:
        """Keep only the latest environment details block."""
        if not blocks:
            return self._create_result(messages, blocks, [], 0)
        
        # Sort by message index and timestamp (newest first)
        blocks.sort(key=lambda b: (b.message_index, b.timestamp), reverse=True)
        
        # Keep the newest block, remove others
        kept_block = blocks[0]
        removed_blocks = blocks[1:]
        
        # Calculate tokens to be saved
        tokens_saved = sum(len(block.content.split()) for block in removed_blocks)
        
        # Remove old blocks from messages
        processed_messages = self._remove_blocks_from_messages(messages.copy(), removed_blocks)
        
        return DeduplicationResult(
            original_messages=messages,
            deduplicated_messages=processed_messages,
            removed_blocks=removed_blocks,
            kept_blocks=[kept_block],
            tokens_saved=tokens_saved,
            processing_time=0.0,
            strategy_used=self.strategy
        )
    
    def _keep_most_relevant_strategy(self, messages: List[Dict[str, Any]], 
                                   blocks: List[EnvironmentDetailsBlock]) -> DeduplicationResult:
        """Keep the most relevant environment details block based on content analysis."""
        if not blocks:
            return self._create_result(messages, blocks, [], 0)
        
        # Calculate relevance scores
        for block in blocks:
            block.relevance_score = self._calculate_relevance_score(block)
        
        # Sort by relevance score (highest first)
        blocks.sort(key=lambda b: b.relevance_score, reverse=True)
        
        # Keep the most relevant block
        kept_block = blocks[0]
        removed_blocks = blocks[1:]
        
        # Calculate tokens to be saved
        tokens_saved = sum(len(block.content.split()) for block in removed_blocks)
        
        # Remove old blocks from messages
        processed_messages = self._remove_blocks_from_messages(messages.copy(), removed_blocks)
        
        return DeduplicationResult(
            original_messages=messages,
            deduplicated_messages=processed_messages,
            removed_blocks=removed_blocks,
            kept_blocks=[kept_block],
            tokens_saved=tokens_saved,
            processing_time=0.0,
            strategy_used=self.strategy
        )
    
    def _calculate_relevance_score(self, block: EnvironmentDetailsBlock) -> float:
        """Calculate relevance score for an environment details block."""
        score = 0.0
        
        # Prefer more recent blocks
        age_minutes = (datetime.now(timezone.utc) - block.timestamp).total_seconds() / 60
        recency_score = max(0, 1 - (age_minutes / self.max_age_minutes))
        score += recency_score * 0.4
        
        # Prefer longer, more detailed blocks
        length_score = min(1, len(block.content) / 500)  # Normalize to 0-1
        score += length_score * 0.3
        
        # Prefer blocks with more structured information
        structure_score = self._calculate_structure_score(block.content)
        score += structure_score * 0.3
        
        return score
    
    def _calculate_structure_score(self, content: str) -> float:
        """Calculate how structured the content is."""
        score = 0.0
        
        # Check for key-value pairs
        if re.search(r'\w+\s*[:=]\s*\w+', content):
            score += 0.3
        
        # Check for multiple lines (indicates structure)
        lines = content.split('\n')
        if len(lines) > 2:
            score += 0.2
        
        # Check for file paths
        if re.search(r'[/\\][\w/\\.-]+', content):
            score += 0.2
        
        # Check for URLs
        if re.search(r'https?://[^\s]+', content):
            score += 0.1
        
        # Check for JSON-like structure
        if re.search(r'[\[\]{}]', content):
            score += 0.2
        
        return min(1.0, score)
    
    def _merge_strategy(self, messages: List[Dict[str, Any]], 
                       blocks: List[EnvironmentDetailsBlock]) -> DeduplicationResult:
        """Merge important parts from multiple environment details blocks."""
        if not blocks:
            return self._create_result(messages, blocks, [], 0)
        
        # Sort by recency (newest first)
        blocks.sort(key=lambda b: (b.message_index, b.timestamp), reverse=True)
        
        # Keep the newest block as base
        base_block = blocks[0]
        merged_content = base_block.content
        
        # Try to merge unique information from other blocks
        for block in blocks[1:]:
            unique_info = self._extract_unique_info(block.content, merged_content)
            if unique_info:
                merged_content += "\n" + unique_info
        
        # Create a new merged block
        merged_block = EnvironmentDetailsBlock(
            content=merged_content,
            start_index=base_block.start_index,
            end_index=base_block.end_index,
            pattern_used=base_block.pattern_used,
            timestamp=datetime.now(timezone.utc),
            message_index=base_block.message_index,
            relevance_score=1.0
        )
        
        # Remove all original blocks and add merged block
        all_removed_blocks = blocks
        processed_messages = self._remove_blocks_from_messages(messages.copy(), all_removed_blocks)
        processed_messages = self._add_block_to_messages(processed_messages, merged_block)
        
        # Calculate tokens saved
        original_tokens = sum(len(block.content.split()) for block in blocks)
        merged_tokens = len(merged_content.split())
        tokens_saved = max(0, original_tokens - merged_tokens)
        
        return DeduplicationResult(
            original_messages=messages,
            deduplicated_messages=processed_messages,
            removed_blocks=all_removed_blocks,
            kept_blocks=[merged_block],
            tokens_saved=tokens_saved,
            processing_time=0.0,
            strategy_used=self.strategy
        )
    
    def _extract_unique_info(self, content: str, existing_content: str) -> str:
        """Extract information that's unique to content compared to existing_content."""
        # This is a simplified implementation - could be made more sophisticated
        content_lines = set(line.strip() for line in content.split('\n') if line.strip())
        existing_lines = set(line.strip() for line in existing_content.split('\n') if line.strip())
        
        unique_lines = content_lines - existing_lines
        return '\n'.join(sorted(unique_lines))
    
    def _selective_removal_strategy(self, messages: List[Dict[str, Any]], 
                                   blocks: List[EnvironmentDetailsBlock]) -> DeduplicationResult:
        """Selectively remove specific redundant sections while preserving unique information."""
        if not blocks:
            return self._create_result(messages, blocks, [], 0)
        
        # Find truly redundant blocks
        comparison = self.compare_environment_details(blocks)
        
        removed_blocks = []
        kept_blocks = []
        
        # Remove duplicate groups, keep only the newest from each group
        for duplicate_group in comparison['duplicates']:
            # Sort by recency, keep the newest
            duplicate_group.sort(key=lambda b: (b.message_index, b.timestamp), reverse=True)
            kept_blocks.append(duplicate_group[0])
            removed_blocks.extend(duplicate_group[1:])
        
        # Keep unique blocks
        kept_blocks.extend(comparison['unique'])
        
        # Calculate tokens saved
        tokens_saved = sum(len(block.content.split()) for block in removed_blocks)
        
        # Remove redundant blocks from messages
        processed_messages = self._remove_blocks_from_messages(messages.copy(), removed_blocks)
        
        return DeduplicationResult(
            original_messages=messages,
            deduplicated_messages=processed_messages,
            removed_blocks=removed_blocks,
            kept_blocks=kept_blocks,
            tokens_saved=tokens_saved,
            processing_time=0.0,
            strategy_used=self.strategy
        )
    
    def _remove_blocks_from_messages(self, messages: List[Dict[str, Any]],
                                   blocks_to_remove: List[EnvironmentDetailsBlock]) -> List[Dict[str, Any]]:
        """Remove specified environment details blocks from messages."""
        if not blocks_to_remove:
            return messages
        
        # Sort blocks by message index and start position (reverse order for safe removal)
        blocks_to_remove.sort(key=lambda b: (b.message_index, b.start_index), reverse=True)
        
        for block in blocks_to_remove:
            if block.message_index < len(messages):
                message = messages[block.message_index]
                
                # Handle multipart content (list format)
                if isinstance(message.get('content'), list):
                    self._remove_block_from_multipart_message(message, block)
                else:
                    # Handle simple string content
                    content = message.get('content', '')
                    if content and block.start_index < len(content) and block.end_index <= len(content):
                        new_content = content[:block.start_index] + content[block.end_index:]
                        message['content'] = new_content
        
        return messages
    
    def _remove_block_from_multipart_message(self, message: Dict[str, Any], block: EnvironmentDetailsBlock):
        """Remove a block from a multipart message (list content format)."""
        content_list = message.get('content', [])
        if not isinstance(content_list, list):
            return
        
        # Find which text part contains this block
        current_pos = 0
        target_part_index = None
        part_start_offset = None
        
        for i, part in enumerate(content_list):
            if isinstance(part, dict) and part.get('type') == 'text':
                text = part.get('text', '')
                if current_pos <= block.start_index < current_pos + len(text):
                    target_part_index = i
                    part_start_offset = block.start_index - current_pos
                    break
                current_pos += len(text)
        
        if target_part_index is not None and part_start_offset is not None:
            part = content_list[target_part_index]
            text = part.get('text', '')
            
            # Calculate removal positions within this part
            remove_start = part_start_offset
            remove_end = min(block.end_index - current_pos, len(text))
            
            if remove_start >= 0 and remove_end <= len(text) and remove_start < remove_end:
                # Remove the block from this text part
                new_text = text[:remove_start] + text[remove_end:]
                part['text'] = new_text
                
                # If the part is now empty, remove it
                if not new_text.strip():
                    content_list.pop(target_part_index)
    
    def _add_block_to_messages(self, messages: List[Dict[str, Any]], 
                             block: EnvironmentDetailsBlock) -> List[Dict[str, Any]]:
        """Add an environment details block to the appropriate message."""
        if block.message_index < len(messages):
            message = messages[block.message_index]
            content = self._extract_message_content(message)
            
            if content:
                # Insert the block at the original position
                new_content = content[:block.start_index] + block.content + content[block.start_index:]
                self._update_message_content(messages[block.message_index], new_content)
        
        return messages
    
    def _update_message_content(self, message: Dict[str, Any], new_content: str):
        """Update the content of a message with new text."""
        if 'content' in message:
            content = message['content']
            if isinstance(content, str):
                message['content'] = new_content
            elif isinstance(content, list):
                # Update the first text part or add a new one
                for part in content:
                    if isinstance(part, dict) and part.get('type') == 'text':
                        part['text'] = new_content
                        break
                else:
                    # No text part found, add one
                    content.insert(0, {'type': 'text', 'text': new_content})
    
    def _create_result(self, messages: List[Dict[str, Any]], 
                      all_blocks: List[EnvironmentDetailsBlock],
                      removed_blocks: List[EnvironmentDetailsBlock], 
                      tokens_saved: int) -> DeduplicationResult:
        """Create a basic deduplication result."""
        kept_blocks = [b for b in all_blocks if b not in removed_blocks]
        
        return DeduplicationResult(
            original_messages=messages,
            deduplicated_messages=messages.copy(),
            removed_blocks=removed_blocks,
            kept_blocks=kept_blocks,
            tokens_saved=tokens_saved,
            processing_time=0.0,
            strategy_used=self.strategy
        )
    
    def _update_stats(self, result: DeduplicationResult):
        """Update internal statistics."""
        self.stats['total_processed'] += len(result.original_messages)
        self.stats['total_blocks_found'] += len(result.removed_blocks) + len(result.kept_blocks)
        self.stats['total_blocks_removed'] += len(result.removed_blocks)
        self.stats['total_tokens_saved'] += result.tokens_saved
        self.stats['total_processing_time'] += result.processing_time
        self.stats['strategy_usage'][result.strategy_used.value] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics."""
        stats = self.stats.copy()
        if stats['total_processing_time'] > 0:
            stats['average_processing_time'] = stats['total_processing_time'] / max(1, stats['total_processed'])
        else:
            stats['average_processing_time'] = 0.0
        
        if stats['total_blocks_found'] > 0:
            stats['removal_rate'] = stats['total_blocks_removed'] / stats['total_blocks_found']
        else:
            stats['removal_rate'] = 0.0
        
        return stats
    
    def clear_stats(self):
        """Clear all statistics."""
        self.stats = {
            'total_processed': 0,
            'total_blocks_found': 0,
            'total_blocks_removed': 0,
            'total_tokens_saved': 0,
            'total_processing_time': 0.0,
            'strategy_usage': {strategy.value: 0 for strategy in DeduplicationStrategy}
        }
    
    def should_keep_details(self, block: EnvironmentDetailsBlock) -> bool:
        """
        Determine if an environment details block should be kept based on various criteria.
        
        Args:
            block: Environment details block to evaluate
            
        Returns:
            True if the block should be kept, False otherwise
        """
        # Check age
        age_minutes = (datetime.now(timezone.utc) - block.timestamp).total_seconds() / 60
        if age_minutes > self.max_age_minutes:
            return False
        
        # Check content relevance
        relevance_score = self._calculate_relevance_score(block)
        if relevance_score < 0.3:  # Low relevance threshold
            return False
        
        # Check for important keywords
        important_keywords = ['error', 'warning', 'exception', 'stack trace', 'debug']
        content_lower = block.content.lower()
        if any(keyword in content_lower for keyword in important_keywords):
            return True  # Keep important diagnostic information
        
        return True


# Global instance and convenience functions
_env_manager = None

def get_environment_details_manager() -> EnvironmentDetailsManager:
    """Get the global environment details manager instance."""
    global _env_manager
    if _env_manager is None:
        _env_manager = EnvironmentDetailsManager()
    return _env_manager


def deduplicate_environment_details(messages: List[Dict[str, Any]]) -> DeduplicationResult:
    """
    Convenience function for environment details deduplication.
    
    Args:
        messages: List of messages to process
        
    Returns:
        DeduplicationResult with processed messages and statistics
    """
    manager = get_environment_details_manager()
    return manager.deduplicate_environment_details(messages)


def detect_environment_details(content: str, message_index: int = 0) -> List[EnvironmentDetailsBlock]:
    """
    Convenience function for detecting environment details.
    
    Args:
        content: Text content to search
        message_index: Index of the message
        
    Returns:
        List of detected environment details blocks
    """
    manager = get_environment_details_manager()
    return manager.detect_environment_details(content, message_index)


def get_deduplication_stats() -> Dict[str, Any]:
    """Get environment details deduplication statistics."""
    manager = get_environment_details_manager()
    return manager.get_stats()