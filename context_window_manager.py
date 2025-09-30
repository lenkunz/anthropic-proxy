#!/usr/bin/env python3
"""
Context Window Management for Anthropic Proxy

This module handles context window overflow issues that occur when switching
between endpoints with different context limits during a conversation.

Problem:
- Text model: 200K tokens (Anthropic) → 150K conversation 
- Switch to vision: 65K tokens (OpenAI) → OVERFLOW!

Solution:
- MINIMAL intervention: Only truncate when absolutely necessary
- Let client manage context until hard API limits are exceeded
- Emergency-only truncation preserves maximum client control
"""

import json
import os
import math
import re
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
import tiktoken

# Load environment variables
load_dotenv()

# Import configuration values
ANTHROPIC_EXPECTED_TOKENS = int(os.getenv("ANTHROPIC_EXPECTED_TOKENS", "200000"))
OPENAI_EXPECTED_TOKENS = int(os.getenv("OPENAI_EXPECTED_TOKENS", "200000"))
REAL_TEXT_MODEL_TOKENS = int(os.getenv("REAL_TEXT_MODEL_TOKENS", "200000"))
REAL_VISION_MODEL_TOKENS = int(os.getenv("REAL_VISION_MODEL_TOKENS", "65536"))

# Simple debug logger (avoid circular imports)
class SimpleLogger:
    def debug(self, msg): print(f"[DEBUG] {msg}")
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")

debug_logger = SimpleLogger()

def simple_count_tokens_from_messages(messages: List[Dict[str, Any]]) -> int:
    """Accurate token counting using tiktoken"""
    try:
        # Use tiktoken for accurate token counting
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        total_tokens = 0
        
        for msg in messages:
            # Add role tokens (approximately)
            total_tokens += 3  # role + formatting tokens
            
            content = msg.get('content', '')
            if isinstance(content, str):
                total_tokens += len(encoding.encode(content))
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            total_tokens += len(encoding.encode(item.get('text', '')))
                        elif item.get('type') in ['image', 'image_url']:
                            total_tokens += 1000  # Estimate for image tokens
        
        return total_tokens
    except Exception as e:
        debug_logger.warning(f"tiktoken failed, using fallback: {e}")
        # Fallback to rough estimation
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
SAFETY_MARGIN_PERCENT = 0.90  # Use 85% of context window
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
        Validate if messages fit within context window - ONLY truncate when unavoidable
        
        This now uses the REAL hard limits, not safety margins.
        Only truncates when the upstream API would actually reject the request.
        
        Returns:
        - (is_valid, estimated_tokens, reason)
        """
        estimated_tokens = self.estimate_message_tokens(messages)
        
        # Use REAL hard limits, not safety margins - let client manage context
        real_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
        
        # Only reserve response tokens if user specified max_tokens
        # Otherwise, let the upstream API handle it naturally
        if max_tokens and max_tokens > 0:
            response_limit = max_tokens
        else:
            # Don't pre-reserve tokens - let the model use all available space
            response_limit = 0
        
        total_needed = estimated_tokens + response_limit
        endpoint_type = "openai" if is_vision else "anthropic"
        
        if total_needed <= real_limit:
            debug_logger.debug(f"Context window OK: {estimated_tokens} input + {response_limit} response = {total_needed} <= {real_limit} ({endpoint_type} endpoint)")
            return True, estimated_tokens, ""
        
        overflow = total_needed - real_limit
        reason = f"Hard context limit exceeded: {total_needed} tokens needed > {real_limit} limit ({endpoint_type} endpoint). Overflow: {overflow} tokens"
        debug_logger.warning(f"UNAVOIDABLE truncation required: {reason}")
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
        Handle context window overflow ONLY when absolutely necessary
        
        Now only truncates when the request would be rejected by upstream API.
        Lets client manage context until it's truly unavoidable.
        
        Returns:
        - (truncated_messages, metadata)
        """
        is_valid, current_tokens, reason = self.validate_context_window(messages, is_vision, max_tokens)
        
        if is_valid:
            return messages, {"truncated": False, "original_tokens": current_tokens}
        
        # Only truncate when we exceed HARD limits that would cause API rejection
        real_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
        
        # Calculate minimal target - leave small buffer only for API overhead (not response)
        api_overhead = 100  # Minimal buffer for API protocol overhead
        target_tokens = real_limit - api_overhead
        
        debug_logger.warning(f"UNAVOIDABLE truncation: {current_tokens} tokens exceeds hard limit {real_limit}")
        debug_logger.info(f"Client should manage context when possible - this is emergency truncation")
        
        # Perform smart truncation to just under hard limit
        truncated_msgs, final_tokens = self.truncate_messages_smart(messages, target_tokens)
        
        metadata = {
            "truncated": True,
            "original_tokens": current_tokens, 
            "final_tokens": final_tokens,
            "truncation_reason": f"Emergency truncation - exceeded hard limit: {reason}",
            "messages_removed": len(messages) - len(truncated_msgs),
            "note": "Client should manage context to avoid this truncation"
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
    # Show REAL hard limits, not safety margins
    hard_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
    endpoint_type = "vision" if is_vision else "text"
    
    return {
        "estimated_tokens": estimated_tokens,
        "hard_limit": hard_limit,
        "endpoint_type": endpoint_type,
        "utilization_percent": round((estimated_tokens / hard_limit) * 100, 1),
        "available_tokens": max(0, hard_limit - estimated_tokens),
        "note": "Proxy only truncates when hard limit exceeded - client should manage context"
    }