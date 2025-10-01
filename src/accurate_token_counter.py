#!/usr/bin/env python3
"""
Accurate Token Counter for Anthropic Proxy

This module provides precise token counting using tiktoken, replacing the previous
scaling-based token estimation system. It supports both Anthropic and OpenAI 
token encodings, handles various message formats, and includes performance
optimizations through caching.

Key Features:
- Accurate tiktoken-based token counting
- Support for both Anthropic and OpenAI encodings
- Performance optimization with LRU caching
- Dynamic image token calculation based on description length
- Graceful fallbacks for error handling
- Support for various message formats (text, images, tool calls)
"""

import os
import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from functools import lru_cache
from dataclasses import dataclass
import tiktoken
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TIKTOKEN_CACHE_SIZE = int(os.getenv("TIKTOKEN_CACHE_SIZE", "1000"))
ENABLE_TOKEN_COUNTING_LOGGING = os.getenv("ENABLE_TOKEN_COUNTING_LOGGING", "false").lower() in ("true", "1", "yes")
IMAGE_TOKENS_PER_CHAR = float(os.getenv("IMAGE_TOKENS_PER_CHAR", "0.25"))  # Approximate tokens per character for image descriptions
BASE_IMAGE_TOKENS = int(os.getenv("BASE_IMAGE_TOKENS", "85"))  # Base tokens for image metadata
ENABLE_DYNAMIC_IMAGE_TOKENS = os.getenv("ENABLE_DYNAMIC_IMAGE_TOKENS", "true").lower() in ("true", "1", "yes")

# Performance optimization: Pre-calculate common values
IMAGE_TOKEN_MULTIPLIER = IMAGE_TOKENS_PER_CHAR
BASE_IMAGE_TOKENS_INT = BASE_IMAGE_TOKENS

# Simple debug logger to avoid circular imports
class SimpleLogger:
    def debug(self, msg): 
        if ENABLE_TOKEN_COUNTING_LOGGING:
            print(f"[TOKEN_COUNTER] {msg}")
    def info(self, msg): 
        if ENABLE_TOKEN_COUNTING_LOGGING:
            print(f"[TOKEN_COUNTER] {msg}")
    def warning(self, msg): 
        if ENABLE_TOKEN_COUNTING_LOGGING:
            print(f"[TOKEN_COUNTER] WARNING: {msg}")

logger = SimpleLogger()

@dataclass
class TokenCount:
    """Data class for token counting results"""
    total_tokens: int
    text_tokens: int
    image_tokens: int
    tool_tokens: int
    metadata_tokens: int
    
    def __add__(self, other: 'TokenCount') -> 'TokenCount':
        return TokenCount(
            total_tokens=self.total_tokens + other.total_tokens,
            text_tokens=self.text_tokens + other.text_tokens,
            image_tokens=self.image_tokens + other.image_tokens,
            tool_tokens=self.tool_tokens + other.tool_tokens,
            metadata_tokens=self.metadata_tokens + other.metadata_tokens
        )

class AccurateTokenCounter:
    """
    Accurate token counting using tiktoken with performance optimizations.
    
    This class provides precise token counting for various message formats,
    supporting both Anthropic and OpenAI token encodings with caching for
    performance optimization.
    """
    
    def __init__(self):
        """Initialize the token counter with encoding support."""
        self._anthropic_encoding = None
        self._openai_encoding = None
        self._initialize_encodings()
        logger.info("AccurateTokenCounter initialized")
    
    def _initialize_encodings(self) -> None:
        """Initialize tiktoken encodings with fallback support."""
        try:
            # Initialize OpenAI encoding (cl100k_base - GPT-4/GPT-3.5-Turbo)
            self._openai_encoding = tiktoken.get_encoding("cl100k_base")
            logger.debug("OpenAI cl100k_base encoding loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load OpenAI encoding: {e}")
            self._openai_encoding = None
        
        try:
            # Try to get model-specific encoding for Anthropic-compatible models
            # Note: tiktoken doesn't have native Anthropic encoding, but we can use cl100k_base
            # as it's compatible with most modern tokenizers
            self._anthropic_encoding = tiktoken.get_encoding("cl100k_base")
            logger.debug("Anthropic-compatible encoding loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load Anthropic encoding: {e}")
            self._anthropic_encoding = None
    
    def _get_encoding(self, endpoint_type: str = "openai") -> Optional[tiktoken.Encoding]:
        """Get appropriate encoding for endpoint type."""
        if endpoint_type.lower() == "anthropic":
            return self._anthropic_encoding or self._openai_encoding
        else:
            return self._openai_encoding or self._anthropic_encoding
    
    @lru_cache(maxsize=TIKTOKEN_CACHE_SIZE)
    def _count_text_tokens_cached(self, text: str, endpoint_type: str = "openai") -> int:
        """
        Count tokens in text with caching for performance optimization.
        
        Args:
            text: The text to count tokens for
            endpoint_type: The endpoint type ("openai" or "anthropic")
            
        Returns:
            Number of tokens in the text
        """
        if not text or not text.strip():
            return 0
        
        encoding = self._get_encoding(endpoint_type)
        if encoding is None:
            # Fallback to rough estimation (3.5 characters per token)
            return max(1, len(text) // 4)
        
        try:
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed for text: {e}")
            # Fallback to rough estimation
            return max(1, len(text) // 4)
    
    def _count_image_tokens(self, image_block: Dict[str, Any], description: Optional[str] = None) -> int:
        """
        Calculate tokens for image content based on description length with performance optimizations.
        
        Instead of using fixed 1000 tokens per image, we calculate dynamically
        based on the actual description length, which is more accurate.
        
        Args:
            image_block: The image block from the message
            description: Optional description text for the image
            
        Returns:
            Number of tokens for the image
        """
        try:
            # Use pre-calculated constants for performance
            if not ENABLE_DYNAMIC_IMAGE_TOKENS:
                # Fallback to fixed tokens for backward compatibility
                return 1000
            
            # If we have a description, count its tokens
            if description and description.strip():
                description_tokens = self._count_text_tokens_cached(description)
                # Use pre-calculated base tokens for performance
                total_tokens = BASE_IMAGE_TOKENS_INT + description_tokens
                if ENABLE_TOKEN_COUNTING_LOGGING:
                    logger.debug(f"Image tokens calculated from description: {description_tokens} + {BASE_IMAGE_TOKENS_INT} = {total_tokens}")
                return total_tokens
            
            # If no description, use a reasonable default based on image metadata
            # This is more accurate than the previous fixed 1000 tokens
            image_metadata_tokens = BASE_IMAGE_TOKENS_INT
            
            # Add tokens for image URL or media type if present (optimized checks)
            source = image_block.get("source")
            if isinstance(source, dict):
                if "media_type" in source:
                    image_metadata_tokens += 10  # Media type tokens
                if "type" in source:
                    image_metadata_tokens += 5   # Type tokens
            
            if ENABLE_TOKEN_COUNTING_LOGGING:
                logger.debug(f"Image tokens calculated from metadata: {image_metadata_tokens}")
            return image_metadata_tokens
            
        except Exception as e:
            if ENABLE_TOKEN_COUNTING_LOGGING:
                logger.warning(f"Image token calculation failed: {e}")
            # Fallback to conservative estimate using pre-calculated constant
            return BASE_IMAGE_TOKENS_INT * 2
    
    def _count_tool_call_tokens(self, tool_call: Dict[str, Any]) -> int:
        """
        Count tokens for tool call content.
        
        Args:
            tool_call: The tool call dictionary
            
        Returns:
            Number of tokens for the tool call
        """
        try:
            tokens = 0
            
            # Add tokens for function name
            if "function" in tool_call and isinstance(tool_call["function"], dict):
                function = tool_call["function"]
                
                if "name" in function:
                    tokens += self._count_text_tokens_cached(function["name"])
                
                # Add tokens for function arguments
                if "arguments" in function:
                    args_str = function["arguments"]
                    if isinstance(args_str, str):
                        tokens += self._count_text_tokens_cached(args_str)
                    elif isinstance(args_str, dict):
                        args_str = json.dumps(args_str, separators=(',', ':'))
                        tokens += self._count_text_tokens_cached(args_str)
            
            # Add base tokens for tool call structure
            tokens += 20  # Base tokens for tool call formatting
            
            return tokens
            
        except Exception as e:
            logger.warning(f"Tool call token counting failed: {e}")
            # Fallback estimate
            return 50
    
    def _count_message_metadata_tokens(self, message: Dict[str, Any]) -> int:
        """
        Count tokens for message metadata (role, formatting, etc.).
        
        Args:
            message: The message dictionary
            
        Returns:
            Number of tokens for message metadata
        """
        try:
            tokens = 0
            
            # Add tokens for role
            role = message.get("role", "")
            if role:
                tokens += self._count_text_tokens_cached(role)
            
            # Add base tokens for message formatting
            tokens += 4  # Role formatting, delimiters, etc.
            
            # Add tokens for other metadata fields
            for key in ["name", "id", "type"]:
                if key in message:
                    value = message[key]
                    if isinstance(value, str):
                        tokens += self._count_text_tokens_cached(value)
                    tokens += 2  # Key and formatting
            
            return tokens
            
        except Exception as e:
            logger.warning(f"Message metadata token counting failed: {e}")
            # Fallback estimate
            return 10
    
    def count_message_tokens(self, message: Dict[str, Any], endpoint_type: str = "openai", 
                           image_descriptions: Optional[Dict[int, str]] = None) -> TokenCount:
        """
        Count tokens for a single message with detailed breakdown.
        
        Args:
            message: The message dictionary to count tokens for
            endpoint_type: The endpoint type ("openai" or "anthropic")
            image_descriptions: Optional dictionary mapping image indices to descriptions
            
        Returns:
            TokenCount object with detailed breakdown
        """
        try:
            text_tokens = 0
            image_tokens = 0
            tool_tokens = 0
            metadata_tokens = 0
            
            # Count metadata tokens
            metadata_tokens = self._count_message_metadata_tokens(message)
            
            # Handle content
            content = message.get("content", "")
            
            if isinstance(content, str):
                # Simple text message
                text_tokens = self._count_text_tokens_cached(content, endpoint_type)
                
            elif isinstance(content, list):
                # Complex content (multiple parts)
                for i, part in enumerate(content):
                    if isinstance(part, dict):
                        part_type = part.get("type", "")
                        
                        if part_type == "text":
                            text = part.get("text", "")
                            text_tokens += self._count_text_tokens_cached(text, endpoint_type)
                            
                        elif part_type in ["image", "image_url"]:
                            # Check if we have a description for this image
                            description = None
                            if image_descriptions and i in image_descriptions:
                                description = image_descriptions[i]
                            
                            image_tokens += self._count_image_tokens(part, description)
                            
                        elif part_type == "tool_use":
                            # Tool use in Anthropic format
                            tool_tokens += self._count_tool_call_tokens(part)
                            
                        elif part_type == "tool_result":
                            # Tool result
                            result_text = part.get("content", "")
                            if isinstance(result_text, str):
                                text_tokens += self._count_text_tokens_cached(result_text, endpoint_type)
                            else:
                                text_tokens += self._count_text_tokens_cached(str(result_text), endpoint_type)
                        
                        else:
                            # Unknown part type, count as text
                            part_text = str(part)
                            text_tokens += self._count_text_tokens_cached(part_text, endpoint_type)
                    
                    elif isinstance(part, str):
                        # String part
                        text_tokens += self._count_text_tokens_cached(part, endpoint_type)
            
            # Handle tool calls in OpenAI format
            if "tool_calls" in message and isinstance(message["tool_calls"], list):
                for tool_call in message["tool_calls"]:
                    tool_tokens += self._count_tool_call_tokens(tool_call)
            
            # Calculate total tokens
            total_tokens = text_tokens + image_tokens + tool_tokens + metadata_tokens
            
            result = TokenCount(
                total_tokens=total_tokens,
                text_tokens=text_tokens,
                image_tokens=image_tokens,
                tool_tokens=tool_tokens,
                metadata_tokens=metadata_tokens
            )
            
            logger.debug(f"Message token count: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Message token counting failed: {e}")
            # Fallback to simple estimation
            fallback_tokens = self._fallback_token_count(message)
            return TokenCount(
                total_tokens=fallback_tokens,
                text_tokens=fallback_tokens,
                image_tokens=0,
                tool_tokens=0,
                metadata_tokens=0
            )
    
    def _fallback_token_count(self, message: Dict[str, Any]) -> int:
        """
        Fallback token counting method when tiktoken fails.
        
        Args:
            message: The message dictionary
            
        Returns:
            Estimated token count
        """
        try:
            content = message.get("content", "")
            if isinstance(content, str):
                # Rough estimate: 1 token per 3.5 characters
                return max(1, len(content) // 4)
            elif isinstance(content, list):
                total_chars = 0
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            total_chars += len(part.get("text", ""))
                        elif part.get("type") in ["image", "image_url"]:
                            total_chars += 1000  # Conservative estimate for images
                    elif isinstance(part, str):
                        total_chars += len(part)
                return max(1, total_chars // 4)
            else:
                return max(1, len(str(content)) // 4)
        except Exception:
            return 50  # Absolute fallback
    
    def count_messages_tokens(self, messages: List[Dict[str, Any]], endpoint_type: str = "openai",
                            system_message: Optional[str] = None,
                            image_descriptions: Optional[Dict[int, str]] = None) -> TokenCount:
        """
        Count tokens for a list of messages.
        
        Args:
            messages: List of message dictionaries
            endpoint_type: The endpoint type ("openai" or "anthropic")
            system_message: Optional system message
            image_descriptions: Optional dictionary mapping image indices to descriptions
            
        Returns:
            TokenCount object with total token breakdown
        """
        try:
            total_count = TokenCount(0, 0, 0, 0, 0)
            
            # Count system message tokens if provided
            if system_message:
                system_tokens = self._count_text_tokens_cached(system_message, endpoint_type)
                total_count += TokenCount(
                    total_tokens=system_tokens + 10,  # Add formatting tokens
                    text_tokens=system_tokens,
                    image_tokens=0,
                    tool_tokens=0,
                    metadata_tokens=10
                )
            
            # Count tokens for each message
            for i, message in enumerate(messages):
                message_count = self.count_message_tokens(message, endpoint_type, image_descriptions)
                total_count += message_count
                
                logger.debug(f"Message {i} tokens: {message_count.total_tokens}")
            
            logger.info(f"Total tokens for {len(messages)} messages: {total_count.total_tokens}")
            return total_count
            
        except Exception as e:
            logger.warning(f"Messages token counting failed: {e}")
            # Fallback estimation
            fallback_total = sum(self._fallback_token_count(msg) for msg in messages) + 100
            return TokenCount(
                total_tokens=fallback_total,
                text_tokens=fallback_total,
                image_tokens=0,
                tool_tokens=0,
                metadata_tokens=0
            )
    
    def validate_token_count(self, messages: List[Dict[str, Any]], max_tokens: int,
                           endpoint_type: str = "openai", system_message: Optional[str] = None,
                           image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[bool, TokenCount]:
        """
        Validate if messages fit within token limit.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum allowed tokens
            endpoint_type: The endpoint type ("openai" or "anthropic")
            system_message: Optional system message
            image_descriptions: Optional dictionary mapping image indices to descriptions
            
        Returns:
            Tuple of (is_valid, token_count)
        """
        token_count = self.count_messages_tokens(messages, endpoint_type, system_message, image_descriptions)
        is_valid = token_count.total_tokens <= max_tokens
        
        logger.info(f"Token validation: {token_count.total_tokens}/{max_tokens} tokens (valid={is_valid})")
        
        return is_valid, token_count
    
    def count_messages_tokens_with_env_deduplication(self, messages: List[Dict[str, Any]], endpoint_type: str = "openai",
                                                    system_message: Optional[str] = None,
                                                    image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[TokenCount, int]:
        """
        Count tokens for messages with environment details deduplication.
        
        Args:
            messages: List of message dictionaries
            endpoint_type: The endpoint type ("openai" or "anthropic")
            system_message: Optional system message
            image_descriptions: Optional dictionary mapping image indices to descriptions
            
        Returns:
            Tuple of (TokenCount object, environment_tokens_saved)
        """
        try:
            # Try to apply environment details deduplication
            env_tokens_saved = 0
            deduplicated_messages = messages
            
            try:
                from .environment_details_manager import get_environment_details_manager
                env_manager = get_environment_details_manager()
                if env_manager and env_manager.enabled:
                    dedup_result = env_manager.deduplicate_environment_details(messages)
                    deduplicated_messages = dedup_result.deduplicated_messages
                    env_tokens_saved = dedup_result.tokens_saved
                    logger.debug(f"Environment deduplication saved {env_tokens_saved} tokens")
            except ImportError:
                logger.debug("Environment details manager not available")
            except Exception as e:
                logger.warning(f"Environment deduplication failed: {e}")
            
            # Count tokens for deduplicated messages
            token_count = self.count_messages_tokens(deduplicated_messages, endpoint_type, system_message, image_descriptions)
            
            return token_count, env_tokens_saved
            
        except Exception as e:
            logger.warning(f"Messages token counting with env deduplication failed: {e}")
            # Fallback to regular counting
            token_count = self.count_messages_tokens(messages, endpoint_type, system_message, image_descriptions)
            return token_count, 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        try:
            text_cache_info = self._count_text_tokens_cached.cache_info()
            return {
                "text_cache_hits": text_cache_info.hits,
                "text_cache_misses": text_cache_info.misses,
                "text_cache_hit_ratio": text_cache_info.hits / max(1, text_cache_info.hits + text_cache_info.misses),
                "text_cache_size": text_cache_info.currsize,
                "text_cache_max_size": text_cache_info.maxsize
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {}
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        try:
            self._count_text_tokens_cached.cache_clear()
            logger.info("Token counter caches cleared")
        except Exception as e:
            logger.warning(f"Failed to clear caches: {e}")

# Global instance for reuse
_global_token_counter: Optional[AccurateTokenCounter] = None

def get_token_counter() -> AccurateTokenCounter:
    """Get or create the global token counter instance."""
    global _global_token_counter
    if _global_token_counter is None:
        _global_token_counter = AccurateTokenCounter()
    return _global_token_counter

def count_tokens_accurate(messages: List[Dict[str, Any]], endpoint_type: str = "openai",
                         system_message: Optional[str] = None,
                         image_descriptions: Optional[Dict[int, str]] = None) -> int:
    """
    Convenience function for accurate token counting.
    
    Args:
        messages: List of message dictionaries
        endpoint_type: The endpoint type ("openai" or "anthropic")
        system_message: Optional system message
        image_descriptions: Optional dictionary mapping image indices to descriptions
        
    Returns:
        Total token count
    """
    counter = get_token_counter()
    token_count = counter.count_messages_tokens(messages, endpoint_type, system_message, image_descriptions)
    return token_count.total_tokens