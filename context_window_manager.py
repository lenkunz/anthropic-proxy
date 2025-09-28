#!/usr/bin/env python3
"""
Context Window Management for Anthropic Proxy

This module handles context window overflow issues that occur when switching
between endpoints with different context limits during a conversation.

Problem:
- Text model: 200K tokens (Anthropic) → 150K conversation 
- Switch to vision: 65K tokens (OpenAI) → OVERFLOW!

Solution:
- Intelligent message truncation
- Context window validation before routing
- Graceful degradation with user notification
"""

import json
import os
import math
import re
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import configuration values
ANTHROPIC_EXPECTED_TOKENS = int(os.getenv("ANTHROPIC_EXPECTED_TOKENS", "200000"))
OPENAI_EXPECTED_TOKENS = int(os.getenv("OPENAI_EXPECTED_TOKENS", "128000"))
REAL_TEXT_MODEL_TOKENS = int(os.getenv("REAL_TEXT_MODEL_TOKENS", "128000"))
REAL_VISION_MODEL_TOKENS = int(os.getenv("REAL_VISION_MODEL_TOKENS", "65536"))

# Simple debug logger (avoid circular imports)
class SimpleLogger:
    def debug(self, msg): print(f"[DEBUG] {msg}")
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")

debug_logger = SimpleLogger()

def simple_count_tokens_from_messages(messages: List[Dict[str, Any]]) -> int:
    """Simple token estimation (fallback when main imports not available)"""
    total_chars = 0
    for msg in messages:
        content = msg.get('content', '')
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        total_chars += len(item.get('text', ''))
                    elif item.get('type') in ['image', 'image_url']:
                        total_chars += 1000  # Estimate for image tokens
    
    # Rough estimate: ~3.5 characters per token
    return int(total_chars / 3.5) + 100  # Add overhead for formatting

# Context window safety margins (leave room for response)
SAFETY_MARGIN_PERCENT = 0.85  # Use 85% of context window
MIN_RESPONSE_TOKENS = 4096    # Reserve for response

class ContextWindowManager:
    """Manages context window constraints across different endpoints"""
    
    def __init__(self):
        self.text_limit = int(REAL_TEXT_MODEL_TOKENS * SAFETY_MARGIN_PERCENT)
        self.vision_limit = int(REAL_VISION_MODEL_TOKENS * SAFETY_MARGIN_PERCENT)
        
    def get_context_limit(self, is_vision: bool) -> int:
        """Get effective context limit for endpoint type"""
        return self.vision_limit if is_vision else self.text_limit
    
    def estimate_message_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """Estimate total tokens in message list"""
        try:
            # Try to import and use the real token counter if available
            try:
                from main import count_tokens_from_messages
                return count_tokens_from_messages(messages)
            except ImportError:
                # Fallback to simple estimation
                return simple_count_tokens_from_messages(messages)
        except Exception as e:
            debug_logger.warning(f"Token estimation failed: {e}")
            # Fallback: rough estimate based on character count
            return simple_count_tokens_from_messages(messages)
    
    def validate_context_window(self, 
                              messages: List[Dict[str, Any]], 
                              is_vision: bool,
                              max_tokens: Optional[int] = None) -> Tuple[bool, int, str]:
        """
        Validate if messages fit within context window
        
        Returns:
        - (is_valid, estimated_tokens, reason)
        """
        estimated_tokens = self.estimate_message_tokens(messages)
        context_limit = self.get_context_limit(is_vision)
        response_limit = max_tokens or MIN_RESPONSE_TOKENS
        
        total_needed = estimated_tokens + response_limit
        endpoint_type = "vision" if is_vision else "text"
        
        if total_needed <= context_limit:
            debug_logger.debug(f"Context window OK: {estimated_tokens} + {response_limit} = {total_needed} <= {context_limit} ({endpoint_type})")
            return True, estimated_tokens, ""
        
        overflow = total_needed - context_limit
        reason = f"Context overflow: {total_needed} tokens needed > {context_limit} limit ({endpoint_type} endpoint). Overflow: {overflow} tokens"
        debug_logger.warning(reason)
        return False, estimated_tokens, reason
    
    def truncate_messages_smart(self, 
                              messages: List[Dict[str, Any]], 
                              target_tokens: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Intelligently truncate messages to fit within target token count
        
        Strategy:
        1. Always preserve system message (first)
        2. Always preserve last user message  
        3. Remove from the middle, keeping recent context
        4. If still too large, truncate individual messages
        """
        if not messages:
            return messages, 0
        
        # Always keep system message and last user message
        system_msgs = [msg for msg in messages if msg.get('role') == 'system']
        user_msgs = [msg for msg in messages if msg.get('role') == 'user']
        assistant_msgs = [msg for msg in messages if msg.get('role') == 'assistant']
        
        if not user_msgs:
            return messages, self.estimate_message_tokens(messages)
        
        # Start with required messages (system + last user)
        required_msgs = system_msgs[:1] + [user_msgs[-1]]  # First system + last user
        required_tokens = self.estimate_message_tokens(required_msgs)
        
        if required_tokens >= target_tokens:
            # Even required messages are too large, truncate last user message
            debug_logger.warning("Even required messages exceed limit, truncating user message")
            return self._truncate_single_message(required_msgs, target_tokens)
        
        # Add messages from recent history until we hit limit
        remaining_tokens = target_tokens - required_tokens
        additional_msgs = []
        
        # Add recent conversation pairs (user + assistant)
        recent_pairs = []
        for i in range(len(user_msgs) - 1, 0, -1):  # Start from second-to-last user msg
            user_msg = user_msgs[i-1]
            # Find corresponding assistant message
            assistant_msg = None
            for j, a_msg in enumerate(assistant_msgs):
                if j == i-1:  # Assuming alternating pattern
                    assistant_msg = a_msg
                    break
            
            if assistant_msg:
                recent_pairs.insert(0, (user_msg, assistant_msg))
            else:
                recent_pairs.insert(0, (user_msg,))
        
        # Add pairs until we exceed token limit
        for pair in reversed(recent_pairs):  # Add most recent first
            pair_tokens = self.estimate_message_tokens(list(pair))
            if pair_tokens <= remaining_tokens:
                additional_msgs.extend(pair)
                remaining_tokens -= pair_tokens
            else:
                break
        
        # Combine all messages
        final_msgs = system_msgs[:1] + additional_msgs + [user_msgs[-1]]
        final_tokens = self.estimate_message_tokens(final_msgs)
        
        debug_logger.info(f"Smart truncation: {len(messages)} → {len(final_msgs)} messages, ~{final_tokens} tokens")
        return final_msgs, final_tokens
    
    def _truncate_single_message(self, messages: List[Dict[str, Any]], target_tokens: int) -> Tuple[List[Dict[str, Any]], int]:
        """Truncate content within individual messages if they're too large"""
        if not messages:
            return messages, 0
        
        # Find the largest message to truncate
        largest_idx = 0
        largest_tokens = 0
        
        for i, msg in enumerate(messages):
            msg_tokens = self.estimate_message_tokens([msg])
            if msg_tokens > largest_tokens:
                largest_tokens = msg_tokens
                largest_idx = i
        
        # Truncate the largest message's content
        msg = messages[largest_idx].copy()
        content = msg.get('content', '')
        
        if isinstance(content, str):
            # Simple text truncation
            # Rough calculation: keep target_tokens * 3 characters
            target_chars = target_tokens * 3
            if len(content) > target_chars:
                truncated = content[:target_chars] + "... [truncated for context limit]"
                msg['content'] = truncated
        elif isinstance(content, list):
            # Complex content (images, etc.) - keep first few elements
            # Try to preserve at least one element
            preserved_content = content[:max(1, target_tokens // 1000)]  
            if len(preserved_content) < len(content):
                preserved_content.append({
                    "type": "text", 
                    "text": f"... [truncated {len(content) - len(preserved_content)} elements for context limit]"
                })
            msg['content'] = preserved_content
        
        messages[largest_idx] = msg
        return messages, self.estimate_message_tokens(messages)
    
    def handle_context_overflow(self, 
                              messages: List[Dict[str, Any]], 
                              is_vision: bool,
                              max_tokens: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Handle context window overflow by truncating messages
        
        Returns:
        - (truncated_messages, metadata)
        """
        is_valid, current_tokens, reason = self.validate_context_window(messages, is_vision, max_tokens)
        
        if is_valid:
            return messages, {"truncated": False, "original_tokens": current_tokens}
        
        # Calculate target tokens (leave room for response)
        context_limit = self.get_context_limit(is_vision)
        response_limit = max_tokens or MIN_RESPONSE_TOKENS
        target_tokens = context_limit - response_limit
        
        debug_logger.warning(f"Context overflow detected, truncating to {target_tokens} tokens")
        
        # Perform smart truncation
        truncated_msgs, final_tokens = self.truncate_messages_smart(messages, target_tokens)
        
        metadata = {
            "truncated": True,
            "original_tokens": current_tokens, 
            "final_tokens": final_tokens,
            "truncation_reason": reason,
            "messages_removed": len(messages) - len(truncated_msgs)
        }
        
        return truncated_msgs, metadata

# Global instance
context_manager = ContextWindowManager()

def validate_and_truncate_context(messages: List[Dict[str, Any]], 
                                is_vision: bool, 
                                max_tokens: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Main entry point for context window management
    
    Returns:
    - (processed_messages, metadata)
    """
    return context_manager.handle_context_overflow(messages, is_vision, max_tokens)

def get_context_info(messages: List[Dict[str, Any]], is_vision: bool) -> Dict[str, Any]:
    """Get context window information for debugging"""
    estimated_tokens = context_manager.estimate_message_tokens(messages)
    limit = context_manager.get_context_limit(is_vision)
    endpoint_type = "vision" if is_vision else "text"
    
    return {
        "estimated_tokens": estimated_tokens,
        "context_limit": limit,
        "endpoint_type": endpoint_type,
        "utilization_percent": round((estimated_tokens / limit) * 100, 1),
        "available_tokens": max(0, limit - estimated_tokens)
    }