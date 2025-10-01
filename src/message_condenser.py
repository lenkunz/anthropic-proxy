#!/usr/bin/env python3
"""
AI-Powered Message Condensation System for Anthropic Proxy

This module provides intelligent conversation context management through
AI-powered message summarization and condensation strategies.

Features:
- Multiple condensation strategies (summary, key points, progressive)
- Intelligent message selection and prioritization
- Integration with existing token counting and caching systems
- Graceful fallback to simple truncation
- Performance optimization with caching and async operations
"""

import os
import json
import asyncio
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import existing components
try:
    from .context_window_manager import simple_count_tokens_from_messages, debug_logger
except ImportError:
    # Fallback logger if context_window_manager not available
    class SimpleLogger:
        def debug(self, msg): print(f"[DEBUG] {msg}")
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    
    debug_logger = SimpleLogger()

# Import chunk management system
try:
    from .message_chunk_manager import get_chunk_manager
    from .message_chunk_manager import MessageChunk, ChunkState, ChunkAnalysisResult
    CHUNK_MANAGEMENT_AVAILABLE = True
except ImportError:
    CHUNK_MANAGEMENT_AVAILABLE = False
    MessageChunk = None
    ChunkState = None
    ChunkAnalysisResult = None
    debug_logger.warning("Chunk management system not available, falling back to traditional condensation")
    
    def simple_count_tokens_from_messages(messages: List[Dict[str, Any]],
                                         image_descriptions: Optional[Dict[str, str]] = None) -> int:
        """Fallback token counting with image description support"""
        total_chars = sum(len(str(msg.get('content', ''))) for msg in messages)
        
        # Add image description characters if available
        if image_descriptions:
            for desc in image_descriptions.values():
                total_chars += len(desc)
        
        return int(total_chars / 3.5) + 100

# Helper function for enhanced token counting with image descriptions
def count_tokens_with_images(messages: List[Dict[str, Any]],
                           image_descriptions: Optional[Dict[str, str]] = None) -> int:
    """Enhanced token counting that supports image descriptions"""
    try:
        return simple_count_tokens_from_messages(messages, image_descriptions)
    except TypeError:
        # Fallback for older versions that don't support image_descriptions parameter
        return simple_count_tokens_from_messages(messages)

# Configuration
ENABLE_AI_CONDENSATION = os.getenv("ENABLE_AI_CONDENSATION", "true").lower() == "true"
CONDENSATION_DEFAULT_STRATEGY = os.getenv("CONDENSATION_DEFAULT_STRATEGY", "conversation_summary")
CONDENSATION_CAUTION_THRESHOLD = float(os.getenv("CONDENSATION_CAUTION_THRESHOLD", "0.70"))
CONDENSATION_WARNING_THRESHOLD = float(os.getenv("CONDENSATION_WARNING_THRESHOLD", "0.80"))
CONDENSATION_CRITICAL_THRESHOLD = float(os.getenv("CONDENSATION_CRITICAL_THRESHOLD", "0.90"))
CONDENSATION_MAX_MESSAGES = int(os.getenv("CONDENSATION_MAX_MESSAGES", "10"))
CONDENSATION_MIN_MESSAGES = int(os.getenv("CONDENSATION_MIN_MESSAGES", "3"))
CONDENSATION_CACHE_TTL = int(os.getenv("CONDENSATION_CACHE_TTL", "3600"))
CONDENSATION_TIMEOUT = int(os.getenv("CONDENSATION_TIMEOUT", "30"))

# Upstream configuration for condensation API calls
UPSTREAM_BASE = os.getenv("UPSTREAM_BASE", "https://api.z.ai/api/anthropic")
OPENAI_UPSTREAM_BASE = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")
SERVER_API_KEY = os.getenv("SERVER_API_KEY")

class CondensationStrategy(Enum):
    """Available condensation strategies"""
    CONVERSATION_SUMMARY = "conversation_summary"
    KEY_POINT_EXTRACTION = "key_point_extraction"
    PROGRESSIVE_SUMMARIZATION = "progressive_summarization"
    SMART_TRUNCATION = "smart_truncation"

@dataclass
class CondensationResult:
    """Result of a condensation operation"""
    success: bool
    condensed_messages: List[Dict[str, Any]]
    original_tokens: int
    condensed_tokens: int
    tokens_saved: int
    strategy_used: str
    processing_time: float
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class MessageImportance:
    """Message importance scoring"""
    index: int
    score: float
    reasons: List[str]
    should_preserve: bool

class CondensationStrategyBase(ABC):
    """Base class for condensation strategies"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.debug_logger = debug_logger
    
    @abstractmethod
    async def condense(self, 
                      messages: List[Dict[str, Any]], 
                      target_tokens: int,
                      upstream_client: httpx.AsyncClient) -> CondensationResult:
        """Execute condensation strategy"""
        pass
    
    def _calculate_message_importance(self, messages: List[Dict[str, Any]]) -> List[MessageImportance]:
        """Calculate importance scores for messages"""
        importance_scores = []
        
        for i, msg in enumerate(messages):
            score = 0.0
            reasons = []
            
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            # System messages are critical
            if role == 'system':
                score += 100
                reasons.append("system_message")
            
            # Recent messages are more important
            recency_score = (i + 1) / len(messages) * 50
            score += recency_score
            reasons.append(f"recency_{recency_score:.1f}")
            
            # User messages are important for context
            if role == 'user':
                score += 30
                reasons.append("user_message")
            
            # Assistant messages with tool calls are important
            if role == 'assistant':
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'tool_use':
                            score += 40
                            reasons.append("tool_call")
                            break
            
            # Length-based scoring (longer messages might contain more info)
            if isinstance(content, str):
                length_score = min(len(content) / 1000, 20)
                score += length_score
                if length_score > 5:
                    reasons.append("substantial_content")
            
            # Check for questions (important for conversation flow)
            if isinstance(content, str) and '?' in content:
                score += 15
                reasons.append("contains_question")
            
            # Check for code blocks
            if isinstance(content, str) and '```' in content:
                score += 20
                reasons.append("contains_code")
            
            should_preserve = score >= 50 or role == 'system'
            importance_scores.append(MessageImportance(i, score, reasons, should_preserve))
        
        return importance_scores

class ConversationSummaryStrategy(CondensationStrategyBase):
    """Strategy that summarizes conversation segments"""
    
    async def condense(self, 
                      messages: List[Dict[str, Any]], 
                      target_tokens: int,
                      upstream_client: httpx.AsyncClient) -> CondensationResult:
        """Condense by summarizing conversation segments"""
        start_time = time.time()
        
        try:
            # Calculate importance and select messages to condense
            importance_scores = self._calculate_message_importance(messages)
            
            # Separate messages to preserve vs condense
            preserve_indices = {imp.index for imp in importance_scores if imp.should_preserve}
            messages_to_preserve = [msg for i, msg in enumerate(messages) if i in preserve_indices]
            messages_to_condense = [msg for i, msg in enumerate(messages) if i not in preserve_indices]
            
            if not messages_to_condense:
                return CondensationResult(
                    success=False,
                    condensed_messages=messages,
                    original_tokens=simple_count_tokens_from_messages(messages),
                    condensed_tokens=simple_count_tokens_from_messages(messages),
                    tokens_saved=0,
                    strategy_used="conversation_summary",
                    processing_time=time.time() - start_time,
                    error_message="No messages available for condensation"
                )
            
            # Create segments for summarization
            segments = self._create_conversation_segments(messages_to_condense)
            
            # Summarize each segment
            condensed_segments = []
            for segment in segments:
                summary = await self._summarize_segment(segment, upstream_client)
                condensed_segments.append(summary)
            
            # Reconstruct conversation
            final_messages = self._reconstruct_conversation(
                messages_to_preserve, condensed_segments, messages
            )
            
            original_tokens = simple_count_tokens_from_messages(messages)
            condensed_tokens = simple_count_tokens_from_messages(final_messages)
            processing_time = time.time() - start_time
            
            return CondensationResult(
                success=True,
                condensed_messages=final_messages,
                original_tokens=original_tokens,
                condensed_tokens=condensed_tokens,
                tokens_saved=original_tokens - condensed_tokens,
                strategy_used="conversation_summary",
                processing_time=processing_time,
                metadata={
                    "segments_summarized": len(segments),
                    "messages_preserved": len(messages_to_preserve),
                    "messages_condensed": len(messages_to_condense)
                }
            )
            
        except Exception as e:
            debug_logger.error(f"Conversation summary condensation failed: {e}")
            return CondensationResult(
                success=False,
                condensed_messages=messages,
                original_tokens=simple_count_tokens_from_messages(messages),
                condensed_tokens=simple_count_tokens_from_messages(messages),
                tokens_saved=0,
                strategy_used="conversation_summary",
                processing_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _create_conversation_segments(self, messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Create conversation segments for summarization"""
        segments = []
        current_segment = []
        current_tokens = 0
        segment_target_tokens = 4000  # Target tokens per segment
        
        for msg in messages:
            msg_tokens = simple_count_tokens_from_messages([msg])
            
            if current_tokens + msg_tokens > segment_target_tokens and current_segment:
                segments.append(current_segment)
                current_segment = [msg]
                current_tokens = msg_tokens
            else:
                current_segment.append(msg)
                current_tokens += msg_tokens
        
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    async def _summarize_segment(self, segment: List[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Summarize a conversation segment using AI"""
        # Format segment for summarization
        segment_text = self._format_segment_for_summary(segment)
        
        # Create summarization prompt
        prompt = f"""Please summarize the following conversation segment while preserving:
1. Key decisions and conclusions
2. Important questions and answers
3. Technical details and code snippets
4. Context needed for continuing the conversation

Conversation segment:
{segment_text}

Provide a concise summary that captures the essential information:"""
        
        # Make API call for summarization
        try:
            response = await client.post(
                f"{UPSTREAM_BASE}/v1/messages",
                headers={
                    "x-api-key": SERVER_API_KEY,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "glm-4.6",
                    "max_tokens": 1000,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=CONDENSATION_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                summary_content = result.get("content", [{}])[0].get("text", "")
                
                return {
                    "role": "assistant",
                    "content": f"[Summary of {len(segment)} messages]: {summary_content}",
                    "metadata": {
                        "type": "summary",
                        "original_message_count": len(segment),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            else:
                # Fallback to simple concatenation
                return self._create_fallback_summary(segment)
                
        except Exception as e:
            debug_logger.warning(f"AI summarization failed, using fallback: {e}")
            return self._create_fallback_summary(segment)
    
    def _create_fallback_summary(self, segment: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create fallback summary when AI summarization fails"""
        key_points = []
        
        for msg in segment:
            content = msg.get('content', '')
            if isinstance(content, str):
                # Extract key information
                if '?' in content:
                    key_points.append(f"Question: {content[:100]}...")
                elif '```' in content:
                    key_points.append(f"Code snippet: {content[:100]}...")
                elif len(content) > 200:
                    key_points.append(f"Discussion: {content[:150]}...")
        
        summary_text = "; ".join(key_points[:3])  # Limit to 3 key points
        if not summary_text:
            summary_text = f"Condensed {len(segment)} messages to save context space"
        
        return {
            "role": "assistant",
            "content": f"[Condensed summary]: {summary_text}",
            "metadata": {
                "type": "fallback_summary",
                "original_message_count": len(segment),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    
    def _format_segment_for_summary(self, segment: List[Dict[str, Any]]) -> str:
        """Format conversation segment for summarization"""
        formatted_lines = []
        
        for msg in segment:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            if isinstance(content, str):
                formatted_lines.append(f"{role.upper()}: {content}")
            elif isinstance(content, list):
                # Handle complex content (images, etc.)
                text_content = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            text_content.append(item.get('text', ''))
                        elif item.get('type') == 'image':
                            text_content.append("[IMAGE]")
                
                formatted_lines.append(f"{role.upper()}: {' '.join(text_content)}")
        
        return "\n".join(formatted_lines)
    
    def _reconstruct_conversation(self, 
                                preserve_messages: List[Dict[str, Any]], 
                                condensed_segments: List[Dict[str, Any]],
                                original_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reconstruct conversation with preserved messages and condensed segments"""
        result = []
        
        # Add system messages first
        system_msgs = [msg for msg in preserve_messages if msg.get('role') == 'system']
        result.extend(system_msgs)
        
        # Add condensed segments
        result.extend(condensed_segments)
        
        # Add other preserved messages (non-system)
        other_preserved = [msg for msg in preserve_messages if msg.get('role') != 'system']
        result.extend(other_preserved)
        
        return result

class KeyPointExtractionStrategy(CondensationStrategyBase):
    """Strategy that extracts key points from messages"""
    
    async def condense(self, 
                      messages: List[Dict[str, Any]], 
                      target_tokens: int,
                      upstream_client: httpx.AsyncClient) -> CondensationResult:
        """Condense by extracting key points"""
        start_time = time.time()
        
        try:
            importance_scores = self._calculate_message_importance(messages)
            
            # Select messages with key information
            key_messages = []
            for imp in importance_scores:
                if imp.should_preserve or "substantial_content" in imp.reasons:
                    key_messages.append(messages[imp.index])
            
            # Extract key points from remaining messages
            remaining_messages = [msg for i, msg in enumerate(messages) 
                                if i not in {imp.index for imp in importance_scores if imp.should_preserve}]
            
            if remaining_messages:
                key_points = await self._extract_key_points(remaining_messages, upstream_client)
                
                # Create condensed message with key points
                condensed_msg = {
                    "role": "assistant",
                    "content": f"[Key points from conversation]: {key_points}",
                    "metadata": {
                        "type": "key_points",
                        "original_message_count": len(remaining_messages),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                
                final_messages = key_messages + [condensed_msg]
            else:
                final_messages = key_messages
            
            original_tokens = simple_count_tokens_from_messages(messages)
            condensed_tokens = simple_count_tokens_from_messages(final_messages)
            processing_time = time.time() - start_time
            
            return CondensationResult(
                success=True,
                condensed_messages=final_messages,
                original_tokens=original_tokens,
                condensed_tokens=condensed_tokens,
                tokens_saved=original_tokens - condensed_tokens,
                strategy_used="key_point_extraction",
                processing_time=processing_time,
                metadata={
                    "key_messages_preserved": len(key_messages),
                    "key_points_extracted": len(remaining_messages)
                }
            )
            
        except Exception as e:
            debug_logger.error(f"Key point extraction failed: {e}")
            return CondensationResult(
                success=False,
                condensed_messages=messages,
                original_tokens=simple_count_tokens_from_messages(messages),
                condensed_tokens=simple_count_tokens_from_messages(messages),
                tokens_saved=0,
                strategy_used="key_point_extraction",
                processing_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def _extract_key_points(self, messages: List[Dict[str, Any]], client: httpx.AsyncClient) -> str:
        """Extract key points from messages using AI"""
        # Format messages for key point extraction
        messages_text = self._format_messages_for_extraction(messages)
        
        prompt = f"""Extract the most important key points from these messages:
1. Decisions made
2. Questions asked and answered
3. Technical solutions provided
4. Action items or next steps
5. Critical context information

Messages:
{messages_text}

Provide a bulleted list of the most important key points:"""
        
        try:
            response = await client.post(
                f"{UPSTREAM_BASE}/v1/messages",
                headers={
                    "x-api-key": SERVER_API_KEY,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "glm-4.6",
                    "max_tokens": 800,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=CONDENSATION_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("content", [{}])[0].get("text", "No key points extracted")
            else:
                return self._create_fallback_key_points(messages)
                
        except Exception as e:
            debug_logger.warning(f"AI key point extraction failed, using fallback: {e}")
            return self._create_fallback_key_points(messages)
    
    def _create_fallback_key_points(self, messages: List[Dict[str, Any]]) -> str:
        """Create fallback key points when AI extraction fails"""
        key_points = []
        
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                # Simple heuristic extraction
                if 'decision' in content.lower() or 'decided' in content.lower():
                    key_points.append(f"• Decision: {content[:100]}...")
                elif 'solution' in content.lower() or 'fix' in content.lower():
                    key_points.append(f"• Solution: {content[:100]}...")
                elif '?' in content:
                    key_points.append(f"• Question: {content[:100]}...")
                elif '```' in content:
                    key_points.append(f"• Code provided")
        
        return '\n'.join(key_points[:5]) if key_points else "• Conversation condensed to save context space"
    
    def _format_messages_for_extraction(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for key point extraction"""
        formatted_lines = []
        
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            
            if isinstance(content, str):
                formatted_lines.append(f"{role}: {content}")
            else:
                formatted_lines.append(f"{role}: [Complex content]")
        
        return "\n".join(formatted_lines)

class ProgressiveSummarizationStrategy(CondensationStrategyBase):
    """Strategy that progressively summarizes large conversations"""
    
    async def condense(self, 
                      messages: List[Dict[str, Any]], 
                      target_tokens: int,
                      upstream_client: httpx.AsyncClient) -> CondensationResult:
        """Progressively summarize in layers"""
        start_time = time.time()
        
        try:
            if len(messages) < CONDENSATION_MIN_MESSAGES:
                return CondensationResult(
                    success=False,
                    condensed_messages=messages,
                    original_tokens=simple_count_tokens_from_messages(messages),
                    condensed_tokens=simple_count_tokens_from_messages(messages),
                    tokens_saved=0,
                    strategy_used="progressive_summarization",
                    processing_time=time.time() - start_time,
                    error_message="Too few messages for progressive summarization"
                )
            
            # Create hierarchical summary layers
            layers = self._create_summary_layers(messages)
            
            # Summarize each layer progressively
            summarized_layers = []
            for layer in layers:
                if len(layer) == 1:
                    summarized_layers.append(layer[0])
                else:
                    summary = await self._summarize_layer(layer, upstream_client)
                    summarized_layers.append(summary)
            
            # Combine with important recent messages
            importance_scores = self._calculate_message_importance(messages)
            recent_important = [messages[imp.index] for imp in importance_scores[-3:] 
                              if imp.should_preserve]
            
            final_messages = summarized_layers + recent_important
            
            original_tokens = simple_count_tokens_from_messages(messages)
            condensed_tokens = simple_count_tokens_from_messages(final_messages)
            processing_time = time.time() - start_time
            
            return CondensationResult(
                success=True,
                condensed_messages=final_messages,
                original_tokens=original_tokens,
                condensed_tokens=condensed_tokens,
                tokens_saved=original_tokens - condensed_tokens,
                strategy_used="progressive_summarization",
                processing_time=processing_time,
                metadata={
                    "layers_created": len(layers),
                    "messages_per_layer": [len(layer) for layer in layers],
                    "recent_messages_preserved": len(recent_important)
                }
            )
            
        except Exception as e:
            debug_logger.error(f"Progressive summarization failed: {e}")
            return CondensationResult(
                success=False,
                condensed_messages=messages,
                original_tokens=simple_count_tokens_from_messages(messages),
                condensed_tokens=simple_count_tokens_from_messages(messages),
                tokens_saved=0,
                strategy_used="progressive_summarization",
                processing_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _create_summary_layers(self, messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Create hierarchical layers for progressive summarization"""
        layers = []
        remaining_messages = messages.copy()
        
        # Create layers with decreasing size
        layer_sizes = [len(messages) // 4, len(messages) // 2, len(messages) // 4]
        
        for size in layer_sizes:
            if len(remaining_messages) > size:
                layer = remaining_messages[:size]
                layers.append(layer)
                remaining_messages = remaining_messages[size:]
        
        if remaining_messages:
            layers.append(remaining_messages)
        
        return layers
    
    async def _summarize_layer(self, layer: List[Dict[str, Any]], client: httpx.AsyncClient) -> Dict[str, Any]:
        """Summarize a layer of messages"""
        layer_text = self._format_layer_for_summary(layer)
        
        prompt = f"""Create a high-level summary of this conversation segment:
{layer_text}

Focus on the main themes and outcomes. Keep it concise but comprehensive."""
        
        try:
            response = await client.post(
                f"{UPSTREAM_BASE}/v1/messages",
                headers={
                    "x-api-key": SERVER_API_KEY,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "glm-4.6",
                    "max_tokens": 600,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=CONDENSATION_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                summary_content = result.get("content", [{}])[0].get("text", "")
                
                return {
                    "role": "assistant",
                    "content": f"[Progressive summary]: {summary_content}",
                    "metadata": {
                        "type": "progressive_summary",
                        "layer_size": len(layer),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            else:
                return self._create_fallback_layer_summary(layer)
                
        except Exception as e:
            debug_logger.warning(f"Progressive layer summarization failed: {e}")
            return self._create_fallback_layer_summary(layer)
    
    def _create_fallback_layer_summary(self, layer: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create fallback layer summary"""
        return {
            "role": "assistant",
            "content": f"[Layer summary]: Condensed {len(layer)} messages from early conversation",
            "metadata": {
                "type": "fallback_layer_summary",
                "layer_size": len(layer),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
    
    def _format_layer_for_summary(self, layer: List[Dict[str, Any]]) -> str:
        """Format layer for summarization"""
        return "\n".join([f"{msg.get('role', 'unknown')}: {str(msg.get('content', ''))[:200]}..." 
                         for msg in layer])

class SmartTruncationStrategy(CondensationStrategyBase):
    """Fallback strategy that intelligently truncates messages"""
    
    async def condense(self, 
                      messages: List[Dict[str, Any]], 
                      target_tokens: int,
                      upstream_client: httpx.AsyncClient) -> CondensationResult:
        """Intelligently truncate messages without AI"""
        start_time = time.time()
        
        try:
            # This is a synchronous operation, but we need to match the interface
            final_messages = await asyncio.get_event_loop().run_in_executor(
                None, self._truncate_messages_sync, messages, target_tokens
            )
            
            original_tokens = simple_count_tokens_from_messages(messages)
            condensed_tokens = simple_count_tokens_from_messages(final_messages)
            processing_time = time.time() - start_time
            
            return CondensationResult(
                success=True,
                condensed_messages=final_messages,
                original_tokens=original_tokens,
                condensed_tokens=condensed_tokens,
                tokens_saved=original_tokens - condensed_tokens,
                strategy_used="smart_truncation",
                processing_time=processing_time,
                metadata={
                    "fallback_reason": "AI condensation unavailable or failed"
                }
            )
            
        except Exception as e:
            debug_logger.error(f"Smart truncation failed: {e}")
            return CondensationResult(
                success=False,
                condensed_messages=messages,
                original_tokens=simple_count_tokens_from_messages(messages),
                condensed_tokens=simple_count_tokens_from_messages(messages),
                tokens_saved=0,
                strategy_used="smart_truncation",
                processing_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def _truncate_messages_sync(self, messages: List[Dict[str, Any]], target_tokens: int) -> List[Dict[str, Any]]:
        """Synchronous message truncation"""
        if not messages:
            return messages
        
        # Always preserve system messages
        system_msgs = [msg for msg in messages if msg.get('role') == 'system']
        other_msgs = [msg for msg in messages if msg.get('role') != 'system']
        
        # Start with system messages
        result = system_msgs.copy()
        current_tokens = simple_count_tokens_from_messages(result)
        
        # Add messages from the end (most recent) until we hit the limit
        for msg in reversed(other_msgs):
            msg_tokens = simple_count_tokens_from_messages([msg])
            
            if current_tokens + msg_tokens <= target_tokens:
                result.insert(len(system_msgs), msg)  # Insert after system messages
                current_tokens += msg_tokens
            else:
                # Try to truncate this message if it's too large
                truncated_msg = self._truncate_single_message(msg, target_tokens - current_tokens)
                if truncated_msg:
                    result.insert(len(system_msgs), truncated_msg)
                break
        
        return result
    
    def _truncate_single_message(self, message: Dict[str, Any], max_tokens: int) -> Optional[Dict[str, Any]]:
        """Truncate a single message to fit within token limit"""
        if max_tokens <= 0:
            return None
        
        msg = message.copy()
        content = msg.get('content', '')
        
        if isinstance(content, str):
            # Estimate characters to keep (rough approximation)
            target_chars = max_tokens * 3
            if len(content) > target_chars:
                truncated_content = content[:target_chars] + "... [truncated]"
                msg['content'] = truncated_content
            return msg
        elif isinstance(content, list):
            # Keep only the first few elements
            preserved = []
            current_tokens = 0
            
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text = item.get('text', '')
                        item_tokens = len(text) // 3  # Rough estimate
                        
                        if current_tokens + item_tokens <= max_tokens:
                            preserved.append(item)
                            current_tokens += item_tokens
                        else:
                            break
                    else:
                        # Preserve non-text items if possible
                        if current_tokens < max_tokens:
                            preserved.append(item)
                            current_tokens += 100  # Estimate for non-text items
            
            if preserved:
                msg['content'] = preserved
                return msg
        
        return None

class AICondensationEngine:
    """Main engine for AI-powered message condensation"""
    
    def __init__(self):
        self.strategies = {
            CondensationStrategy.CONVERSATION_SUMMARY: ConversationSummaryStrategy({}),
            CondensationStrategy.KEY_POINT_EXTRACTION: KeyPointExtractionStrategy({}),
            CondensationStrategy.PROGRESSIVE_SUMMARIZATION: ProgressiveSummarizationStrategy({}),
            CondensationStrategy.SMART_TRUNCATION: SmartTruncationStrategy({})
        }
        
        self.cache = {}
        self.cache_timestamps = {}
        self.debug_logger = debug_logger
        
        # Initialize chunk manager if available
        if CHUNK_MANAGEMENT_AVAILABLE:
            self.chunk_manager = get_chunk_manager()
        else:
            self.chunk_manager = None
        
    def should_condense(self, 
                       messages: List[Dict[str, Any]], 
                       current_tokens: int, 
                       max_tokens: int,
                       is_vision: bool = False) -> Tuple[bool, str]:
        """Determine if condensation should be applied"""
        
        if not ENABLE_AI_CONDENSATION:
            return False, "AI condensation disabled"
        
        if len(messages) < CONDENSATION_MIN_MESSAGES:
            return False, f"Too few messages ({len(messages)} < {CONDENSATION_MIN_MESSAGES})"
        
        # Calculate utilization ratio
        utilization = current_tokens / max_tokens
        
        if utilization >= CONDENSATION_CRITICAL_THRESHOLD:
            return True, f"Critical threshold reached ({utilization:.2f} >= {CONDENSATION_CRITICAL_THRESHOLD})"
        elif utilization >= CONDENSATION_WARNING_THRESHOLD:
            return True, f"Warning threshold reached ({utilization:.2f} >= {CONDENSATION_WARNING_THRESHOLD})"
        elif utilization >= CONDENSATION_CAUTION_THRESHOLD:
            return True, f"Caution threshold reached ({utilization:.2f} >= {CONDENSATION_CAUTION_THRESHOLD})"
        
        return False, f"Threshold not reached ({utilization:.2f} < {CONDENSATION_CAUTION_THRESHOLD})"
    
    def select_strategy(self, 
                       messages: List[Dict[str, Any]], 
                       current_tokens: int,
                       max_tokens: int,
                       preferred_strategy: Optional[str] = None) -> CondensationStrategy:
        """Select appropriate condensation strategy"""
        
        if preferred_strategy:
            try:
                return CondensationStrategy(preferred_strategy)
            except ValueError:
                debug_logger.warning(f"Unknown strategy: {preferred_strategy}, using default")
        
        # Auto-select strategy based on characteristics
        message_count = len(messages)
        
        if message_count > 20:
            return CondensationStrategy.PROGRESSIVE_SUMMARIZATION
        elif message_count > 10:
            return CondensationStrategy.CONVERSATION_SUMMARY
        elif current_tokens > max_tokens * 0.9:
            return CondensationStrategy.SMART_TRUNCATION
        else:
            return CondensationStrategy.KEY_POINT_EXTRACTION
    
    async def condense_messages(self,
                               messages: List[Dict[str, Any]],
                               current_tokens: int,
                               max_tokens: int,
                               preferred_strategy: Optional[str] = None,
                               is_vision: bool = False,
                               image_descriptions: Optional[Dict[str, str]] = None) -> CondensationResult:
        """Main entry point for message condensation"""
        
        start_time = time.time()
        
        # Apply environment details deduplication first to reduce token usage
        deduplicated_messages = messages
        env_tokens_saved = 0
        try:
            from .environment_details_manager import get_environment_details_manager
            env_manager = get_environment_details_manager()
            if env_manager and env_manager.enabled:
                dedup_result = env_manager.deduplicate_environment_details(messages)
                deduplicated_messages = dedup_result.deduplicated_messages
                env_tokens_saved = dedup_result.tokens_saved
                debug_logger.info(f"Environment details deduplication: removed {len(dedup_result.removed_blocks)} blocks, saved {env_tokens_saved} tokens")
        except ImportError:
            debug_logger.debug("Environment details manager not available")
        except Exception as e:
            debug_logger.warning(f"Environment details deduplication failed: {e}")
        
        # Check if we should condense (use deduplicated messages for analysis)
        should_condense, reason = self.should_condense(deduplicated_messages, current_tokens, max_tokens, is_vision)
        
        if not should_condense:
            return CondensationResult(
                success=False,
                condensed_messages=deduplicated_messages,
                original_tokens=current_tokens,
                condensed_tokens=current_tokens,
                tokens_saved=env_tokens_saved,  # Include environment deduplication savings
                strategy_used="environment_deduplication_only",
                processing_time=0,
                error_message=reason
            )
        
        debug_logger.info(f"Starting message condensation: {reason}")
        
        # Select strategy (use deduplicated messages)
        strategy = self.select_strategy(deduplicated_messages, current_tokens, max_tokens, preferred_strategy)
        
        # Check cache first (use deduplicated messages for cache key)
        cache_key = self._generate_cache_key(deduplicated_messages, strategy, max_tokens)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            debug_logger.debug(f"Using cached condensation result")
            return cached_result
        
        # Execute condensation
        strategy_instance = self.strategies[strategy]
        
        try:
            async with httpx.AsyncClient(timeout=CONDENSATION_TIMEOUT) as client:
                result = await strategy_instance.condense(deduplicated_messages, max_tokens, client)
            
            # Add environment deduplication savings to the result
            result.tokens_saved += env_tokens_saved
            
            # Cache successful results
            if result.success:
                self._cache_result(cache_key, result)
            
            debug_logger.info(f"Condensation completed: {result.strategy_used}, "
                            f"saved {result.tokens_saved} tokens (including {env_tokens_saved} from env deduplication) in {result.processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            debug_logger.error(f"Condensation failed: {e}")
            
            # Fallback to smart truncation
            debug_logger.info("Falling back to smart truncation")
            fallback_strategy = self.strategies[CondensationStrategy.SMART_TRUNCATION]
            
            try:
                async with httpx.AsyncClient(timeout=CONDENSATION_TIMEOUT) as client:
                    result = await fallback_strategy.condense(deduplicated_messages, max_tokens, client)
                
                # Add environment deduplication savings to the fallback result
                result.tokens_saved += env_tokens_saved
                
                return result
                
                if result.success:
                    self._cache_result(cache_key, result)
                
                return result
                
            except Exception as fallback_error:
                debug_logger.error(f"Even fallback condensation failed: {fallback_error}")
                
                return CondensationResult(
                    success=False,
                    condensed_messages=messages,
                    original_tokens=current_tokens,
                    condensed_tokens=current_tokens,
                    tokens_saved=0,
                    strategy_used="none",
                    processing_time=time.time() - start_time,
                    error_message=f"All condensation strategies failed: {str(e)}, {str(fallback_error)}"
                )
    
    def _generate_cache_key(self, 
                           messages: List[Dict[str, Any]], 
                           strategy: CondensationStrategy, 
                           max_tokens: int) -> str:
        """Generate cache key for condensation results"""
        # Create a hash of message content and strategy
        content_hash = hashlib.md5()
        
        for msg in messages:
            content_hash.update(json.dumps(msg, sort_keys=True).encode())
        
        content_hash.update(strategy.value.encode())
        content_hash.update(str(max_tokens).encode())
        
        return content_hash.hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[CondensationResult]:
        """Get cached condensation result"""
        if cache_key in self.cache:
            timestamp = self.cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < CONDENSATION_CACHE_TTL:
                return self.cache[cache_key]
            else:
                # Remove expired cache entry
                del self.cache[cache_key]
                del self.cache_timestamps[cache_key]
        
        return None
    
    def _cache_result(self, cache_key: str, result: CondensationResult):
        """Cache condensation result"""
        # Limit cache size
        if len(self.cache) >= 100:
            # Remove oldest entry
            oldest_key = min(self.cache_timestamps.keys(), 
                           key=lambda k: self.cache_timestamps[k])
            del self.cache[oldest_key]
            del self.cache_timestamps[oldest_key]
        
        self.cache[cache_key] = result
        self.cache_timestamps[cache_key] = time.time()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_ttl": CONDENSATION_CACHE_TTL,
            "cached_entries": list(self.cache.keys())
        }
    
    async def condense_messages_chunked(self,
                                       messages: List[Dict[str, Any]],
                                       current_tokens: int,
                                       max_tokens: int,
                                       preferred_strategy: Optional[str] = None,
                                       is_vision: bool = False,
                                       image_descriptions: Optional[Dict[str, str]] = None) -> CondensationResult:
        """
        Chunk-based message condensation with intelligent tracking
        
        This method uses the chunk management system to avoid re-condensing
        already processed chunks, especially for image endpoints.
        """
        if not CHUNK_MANAGEMENT_AVAILABLE or not self.chunk_manager:
            # Fallback to traditional condensation
            return await self.condense_messages(
                messages, current_tokens, max_tokens, preferred_strategy, is_vision, image_descriptions
            )
        
        start_time = time.time()
        
        try:
            # Identify message chunks
            chunks = self.chunk_manager.identify_message_chunks(messages, is_vision)
            
            if not chunks:
                return CondensationResult(
                    success=False,
                    condensed_messages=messages,
                    original_tokens=current_tokens,
                    condensed_tokens=current_tokens,
                    tokens_saved=0,
                    strategy_used="none",
                    processing_time=0,
                    error_message="No chunks identified"
                )
            
            # Analyze chunks to understand condensation needs
            analysis = self.chunk_manager.analyze_chunks(chunks)
            
            self.debug_logger.info(f"Chunk analysis: {analysis.total_chunks} chunks, "
                                 f"{len(analysis.uncondensed_chunks)} uncondensed, "
                                 f"{len(analysis.condensed_chunks)} already condensed")
            
            # If all chunks are already condensed and valid, reconstruct condensed messages
            if not analysis.uncondensed_chunks and analysis.condensed_chunks:
                condensed_messages = self._reconstruct_condensed_messages(chunks, messages)
                final_tokens = count_tokens_with_images(condensed_messages, image_descriptions)
                
                return CondensationResult(
                    success=True,
                    condensed_messages=condensed_messages,
                    original_tokens=current_tokens,
                    condensed_tokens=final_tokens,
                    tokens_saved=current_tokens - final_tokens,
                    strategy_used="chunk_cached",
                    processing_time=time.time() - start_time,
                    metadata={
                        "chunks_used": len(chunks),
                        "condensed_chunks": len(analysis.condensed_chunks),
                        "from_cache": True
                    }
                )
            
            # Process uncondensed chunks
            processed_chunks = []
            total_tokens_saved = 0
            
            for chunk in chunks:
                if self.chunk_manager.is_chunk_condensed(chunk):
                    # Use already condensed chunk
                    processed_chunks.append(chunk)
                    total_tokens_saved += chunk.tokens_saved
                    continue
                
                # Condense the chunk
                chunk_result = await self._condense_single_chunk(
                    chunk, max_tokens, preferred_strategy, is_vision, image_descriptions
                )
                
                if chunk_result.success:
                    # Mark chunk as condensed
                    self.chunk_manager.mark_chunk_condensed(
                        chunk,
                        chunk_result.condensed_messages[0].get('content', ''),
                        chunk_result.strategy_used,
                        chunk_result.tokens_saved
                    )
                    processed_chunks.append(chunk)
                    total_tokens_saved += chunk_result.tokens_saved
                else:
                    # Keep original chunk if condensation failed
                    processed_chunks.append(chunk)
            
            # Reconstruct final condensed messages
            final_messages = self._reconstruct_condensed_messages(processed_chunks, messages)
            final_tokens = count_tokens_with_images(final_messages, image_descriptions)
            
            return CondensationResult(
                success=True,
                condensed_messages=final_messages,
                original_tokens=current_tokens,
                condensed_tokens=final_tokens,
                tokens_saved=total_tokens_saved,
                strategy_used="chunk_based",
                processing_time=time.time() - start_time,
                metadata={
                    "total_chunks": len(chunks),
                    "processed_chunks": len(processed_chunks),
                    "condensed_chunks": len([c for c in processed_chunks if c.state == ChunkState.CONDENSED]),
                    "chunks_from_cache": len(analysis.condensed_chunks)
                }
            )
            
        except Exception as e:
            self.debug_logger.error(f"Chunk-based condensation failed: {e}")
            # Fallback to traditional condensation
            return await self.condense_messages(
                messages, current_tokens, max_tokens, preferred_strategy, is_vision, image_descriptions
            )
    
    async def _condense_single_chunk(self,
                                    chunk: MessageChunk,
                                    max_tokens: int,
                                    preferred_strategy: Optional[str],
                                    is_vision: bool,
                                    image_descriptions: Optional[Dict[str, str]]) -> CondensationResult:
        """Condense a single chunk of messages"""
        chunk_tokens = chunk.token_count
        target_tokens = max(max_tokens // len([chunk]) if chunk else max_tokens, chunk_tokens // 2)
        
        # Use existing condensation logic for the chunk
        return await self.condense_messages(
            chunk.messages,
            chunk_tokens,
            target_tokens,
            preferred_strategy,
            is_vision,
            image_descriptions
        )
    
    def _reconstruct_condensed_messages(self,
                                      chunks: List[MessageChunk],
                                      original_messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reconstruct the final message list from processed chunks"""
        reconstructed = []
        
        for chunk in chunks:
            if chunk.state == ChunkState.CONDENSED and chunk.condensed_content:
                # Use condensed version
                condensed_msg = {
                    "role": "assistant",
                    "content": chunk.condensed_content,
                    "type": "condensed_chunk",
                    "chunk_id": chunk.chunk_id,
                    "original_range": [chunk.start_index, chunk.end_index],
                    "tokens_saved": chunk.tokens_saved
                }
                reconstructed.append(condensed_msg)
            else:
                # Use original messages
                reconstructed.extend(chunk.messages)
        
        return reconstructed
    
    def get_chunk_stats(self) -> Dict[str, Any]:
        """Get chunk management statistics"""
        if not CHUNK_MANAGEMENT_AVAILABLE or not self.chunk_manager:
            return {"chunk_management_available": False}
        
        return {
            "chunk_management_available": True,
            **self.chunk_manager.get_cache_stats()
        }

# Global instance
condensation_engine = AICondensationEngine()

# Convenience functions
async def condense_messages_if_needed(messages: List[Dict[str, Any]],
                                     current_tokens: int,
                                     max_tokens: int,
                                     preferred_strategy: Optional[str] = None,
                                     is_vision: bool = False,
                                     image_descriptions: Optional[Dict[str, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to condense messages if needed
    
    Returns:
    - (condensed_messages, metadata)
    """
    result = await condensation_engine.condense_messages(
        messages, current_tokens, max_tokens, preferred_strategy, is_vision, image_descriptions
    )
    
    metadata = {
        "condensed": result.success,
        "original_tokens": result.original_tokens,
        "final_tokens": result.condensed_tokens,
        "tokens_saved": result.tokens_saved,
        "strategy_used": result.strategy_used,
        "processing_time": result.processing_time,
        "error_message": result.error_message,
        "metadata": result.metadata
    }
    
    return result.condensed_messages, metadata