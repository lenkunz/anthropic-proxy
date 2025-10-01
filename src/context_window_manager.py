#!/usr/bin/env python3
"""
Intelligent Context Window Management for Anthropic Proxy

This module provides advanced context window management with AI-powered condensation,
accurate token counting, and multi-level context validation strategies.

Problem:
- Text model: 200K tokens (Anthropic) → 150K conversation
- Switch to vision: 65K tokens (OpenAI) → OVERFLOW!

Solution:
- Intelligent context management with proactive condensation
- Multi-level validation (safe, caution, warning, critical)
- AI-powered message condensation before emergency truncation
- Seamless integration with accurate token counting and image handling
"""

import json
import os
import math
import re
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from dotenv import load_dotenv
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False

# Load environment variables
load_dotenv()

# Import configuration values
ANTHROPIC_EXPECTED_TOKENS = int(os.getenv("ANTHROPIC_EXPECTED_TOKENS", "200000"))
OPENAI_EXPECTED_TOKENS = int(os.getenv("OPENAI_EXPECTED_TOKENS", "200000"))
REAL_TEXT_MODEL_TOKENS = int(os.getenv("REAL_TEXT_MODEL_TOKENS", "200000"))
REAL_VISION_MODEL_TOKENS = int(os.getenv("REAL_VISION_MODEL_TOKENS", "65536"))

# Intelligent Context Management Configuration
ENABLE_AI_CONDENSATION = os.getenv("ENABLE_AI_CONDENSATION", "true").lower() in ("true", "1", "yes")
CONDENSATION_DEFAULT_STRATEGY = os.getenv("CONDENSATION_DEFAULT_STRATEGY", "conversation_summary")
CONDENSATION_CAUTION_THRESHOLD = float(os.getenv("CONDENSATION_CAUTION_THRESHOLD", "0.70"))
CONDENSATION_WARNING_THRESHOLD = float(os.getenv("CONDENSATION_WARNING_THRESHOLD", "0.80"))
CONDENSATION_CRITICAL_THRESHOLD = float(os.getenv("CONDENSATION_CRITICAL_THRESHOLD", "0.90"))
CONDENSATION_MIN_MESSAGES = int(os.getenv("CONDENSATION_MIN_MESSAGES", "3"))
CONDENSATION_MAX_MESSAGES = int(os.getenv("CONDENSATION_MAX_MESSAGES", "10"))
CONDENSATION_TIMEOUT = int(os.getenv("CONDENSATION_TIMEOUT", "30"))

# Performance and caching configuration
ENABLE_CONTEXT_PERFORMANCE_LOGGING = os.getenv("ENABLE_CONTEXT_PERFORMANCE_LOGGING", "false").lower() in ("true", "1", "yes")
CONTEXT_CACHE_SIZE = int(os.getenv("CONTEXT_CACHE_SIZE", "100"))
CONTEXT_ANALYSIS_CACHE_TTL = int(os.getenv("CONTEXT_ANALYSIS_CACHE_TTL", "300"))

# Context management enums and data classes
class ContextRiskLevel(Enum):
    """Risk levels for context utilization"""
    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    CRITICAL = "critical"
    OVERFLOW = "overflow"

class ContextManagementStrategy(Enum):
    """Strategies for context management"""
    MONITOR_ONLY = "monitor_only"
    CONDENSATION_LIGHT = "condensation_light"
    CONDENSATION_AGGRESSIVE = "condensation_aggressive"
    EMERGENCY_TRUNCATION = "emergency_truncation"

@dataclass
class ContextAnalysisResult:
    """Result of context analysis"""
    risk_level: ContextRiskLevel
    utilization_percent: float
    current_tokens: int
    limit_tokens: int
    available_tokens: int
    recommended_strategy: ContextManagementStrategy
    should_condense: bool
    messages_count: int
    analysis_time: float
    metadata: Dict[str, Any]

@dataclass
class ContextManagementResult:
    """Result of context management operations"""
    original_messages: List[Dict[str, Any]]
    processed_messages: List[Dict[str, Any]]
    original_tokens: int
    final_tokens: int
    tokens_saved: int
    strategy_used: ContextManagementStrategy
    risk_level: ContextRiskLevel
    processing_time: float
    metadata: Dict[str, Any]

# Enhanced debug logger (avoid circular imports)
class SimpleLogger:
    def debug(self, msg):
        if ENABLE_CONTEXT_PERFORMANCE_LOGGING:
            print(f"[CONTEXT_DEBUG] {msg}")
    def info(self, msg):
        if ENABLE_CONTEXT_PERFORMANCE_LOGGING:
            print(f"[CONTEXT_INFO] {msg}")
    def warning(self, msg): print(f"[CONTEXT_WARNING] {msg}")
    def error(self, msg): print(f"[CONTEXT_ERROR] {msg}")

debug_logger = SimpleLogger()

def simple_count_tokens_from_messages(messages: List[Dict[str, Any]],
                                     image_descriptions: Optional[Dict[str, str]] = None) -> int:
    """Accurate token counting using tiktoken with dynamic image token calculation"""
    try:
        # Load configuration for dynamic image token calculation
        from dotenv import load_dotenv
        load_dotenv()
        
        BASE_IMAGE_TOKENS = int(os.getenv("BASE_IMAGE_TOKENS", "85"))
        IMAGE_TOKENS_PER_CHAR = float(os.getenv("IMAGE_TOKENS_PER_CHAR", "0.25"))
        ENABLE_DYNAMIC_IMAGE_TOKENS = os.getenv("ENABLE_DYNAMIC_IMAGE_TOKENS", "true").lower() in ("true", "1", "yes")
        
        # Use tiktoken for accurate token counting if available
        if TIKTOKEN_AVAILABLE:
            encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        else:
            # Fallback when tiktoken is not available
            encoding = None
        total_tokens = 0
        
        for i, msg in enumerate(messages):
            # Add role tokens (approximately)
            total_tokens += 3  # role + formatting tokens
            
            content = msg.get('content', '')
            if isinstance(content, str):
                if encoding:
                    total_tokens += len(encoding.encode(content))
                else:
                    # Fallback estimation: ~4 characters per token
                    total_tokens += len(content) // 4
            elif isinstance(content, list):
                for j, item in enumerate(content):
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            if encoding:
                                total_tokens += len(encoding.encode(item.get('text', '')))
                            else:
                                # Fallback estimation: ~4 characters per token
                                total_tokens += len(item.get('text', '')) // 4
                        elif item.get('type') in ['image', 'image_url']:
                            # Use dynamic image token calculation if enabled
                            if ENABLE_DYNAMIC_IMAGE_TOKENS:
                                # Use image description if available
                                if image_descriptions and f"{i}_{j}" in image_descriptions:
                                    description = image_descriptions[f"{i}_{j}"]
                                    # Calculate tokens based on description length
                                    if encoding:
                                        description_tokens = len(encoding.encode(description))
                                    else:
                                        description_tokens = len(description) // 4
                                    total_tokens += BASE_IMAGE_TOKENS + int(description_tokens * IMAGE_TOKENS_PER_CHAR)
                                else:
                                    # Use base image tokens if no description
                                    total_tokens += BASE_IMAGE_TOKENS
                            else:
                                # Fallback to fixed 1000 tokens for backward compatibility
                                total_tokens += 1000
        
        return total_tokens
    except Exception as e:
        debug_logger.warning(f"tiktoken failed, using fallback: {e}")
        # Fallback to rough estimation with dynamic image tokens
        load_dotenv()
        
        BASE_IMAGE_TOKENS = int(os.getenv("BASE_IMAGE_TOKENS", "85"))
        IMAGE_TOKENS_PER_CHAR = float(os.getenv("IMAGE_TOKENS_PER_CHAR", "0.25"))
        ENABLE_DYNAMIC_IMAGE_TOKENS = os.getenv("ENABLE_DYNAMIC_IMAGE_TOKENS", "true").lower() in ("true", "1", "yes")
        
        total_chars = 0
        for i, msg in enumerate(messages):
            content = msg.get('content', '')
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for j, item in enumerate(content):
                    if isinstance(item, dict):
                        if item.get('type') == 'text':
                            total_chars += len(item.get('text', ''))
                        elif item.get('type') in ['image', 'image_url']:
                            # Use dynamic image token calculation in fallback
                            if ENABLE_DYNAMIC_IMAGE_TOKENS:
                                if image_descriptions and f"{i}_{j}" in image_descriptions:
                                    description = image_descriptions[f"{i}_{j}"]
                                    # Estimate tokens from description length
                                    description_chars = len(description)
                                    estimated_tokens = BASE_IMAGE_TOKENS + int(description_chars * IMAGE_TOKENS_PER_CHAR)
                                    total_chars += estimated_tokens * 3.5  # Convert back to chars for consistency
                                else:
                                    total_chars += BASE_IMAGE_TOKENS * 3.5  # Convert to chars
                            else:
                                total_chars += 1000  # Fixed estimate
        
        # Rough estimate: ~3.5 characters per token
        return int(total_chars / 3.5) + 100  # Add overhead for formatting

# Context window safety margins (leave room for response)
SAFETY_MARGIN_PERCENT = 0.90  # Use 85% of context window
MIN_RESPONSE_TOKENS = 4096    # Reserve for response

# Import condensation system
try:
    from .message_condenser import condense_messages_if_needed, condensation_engine
    CONDENSATION_AVAILABLE = True
    debug_logger.info("AI condensation system loaded successfully")
except ImportError as e:
    CONDENSATION_AVAILABLE = False
    debug_logger.warning(f"AI condensation system not available: {e}")

# Import chunk management system
try:
    from .message_chunk_manager import get_chunk_manager, ENABLE_CHUNK_BASED_CONDENSATION
    CHUNK_MANAGEMENT_AVAILABLE = True
    debug_logger.info("Chunk management system loaded successfully")
except ImportError as e:
    CHUNK_MANAGEMENT_AVAILABLE = False
    ENABLE_CHUNK_BASED_CONDENSATION = False
    debug_logger.warning(f"Chunk management system not available: {e}")

class ContextWindowManager:
    """Intelligent context window manager with AI-powered condensation and multi-level validation"""
    
    def __init__(self):
        # Initialize limits with safety margins for traditional operations
        self.text_limit = int(REAL_TEXT_MODEL_TOKENS * SAFETY_MARGIN_PERCENT)
        self.vision_limit = int(REAL_VISION_MODEL_TOKENS * SAFETY_MARGIN_PERCENT)
        
        # Initialize AI condensation engine
        self.condensation_engine = None
        if CONDENSATION_AVAILABLE:
            try:
                from .message_condenser import AICondensationEngine
                self.condensation_engine = AICondensationEngine()
                debug_logger.info("AI condensation engine initialized successfully")
            except Exception as e:
                debug_logger.error(f"Failed to initialize AI condensation engine: {e}")
        
        # Initialize accurate token counter
        self.token_counter = None
        try:
            from .accurate_token_counter import get_token_counter
            self.token_counter = get_token_counter()
            debug_logger.info("Accurate token counter initialized successfully")
        except Exception as e:
            debug_logger.warning(f"Failed to initialize accurate token counter: {e}")
        
        # Initialize chunk manager
        self.chunk_manager = None
        if CHUNK_MANAGEMENT_AVAILABLE and ENABLE_CHUNK_BASED_CONDENSATION:
            try:
                self.chunk_manager = get_chunk_manager()
                debug_logger.info("Chunk manager initialized successfully")
            except Exception as e:
                debug_logger.error(f"Failed to initialize chunk manager: {e}")
        
        # Initialize environment details manager
        self.env_details_manager = None
        try:
            from .environment_details_manager import get_environment_details_manager
            self.env_details_manager = get_environment_details_manager()
            debug_logger.info("Environment details manager initialized successfully")
        except Exception as e:
            debug_logger.warning(f"Failed to initialize environment details manager: {e}")
        
        # Performance caching
        self._analysis_cache = {}
        self._cache_timestamps = {}
        
    def get_context_limit(self, is_vision: bool) -> int:
        """Get real context limit for endpoint type"""
        return REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
    
    def get_effective_limit(self, is_vision: bool, include_response_reserve: bool = True) -> int:
        """Get effective limit with optional response token reservation"""
        real_limit = self.get_context_limit(is_vision)
        if include_response_reserve:
            return int(real_limit * SAFETY_MARGIN_PERCENT)
        return real_limit
    
    def estimate_message_tokens(self, messages: List[Dict[str, Any]],
                              image_descriptions: Optional[Dict[int, str]] = None,
                              endpoint_type: str = "openai") -> int:
        """
        Estimate total tokens in message list using accurate counting when available
        
        Args:
            messages: List of message dictionaries
            image_descriptions: Optional dictionary mapping image indices to descriptions
            endpoint_type: Type of endpoint ("openai" or "anthropic")
        
        Returns:
            Estimated token count
        """
        try:
            # Use accurate token counter if available
            if self.token_counter:
                return self.token_counter.count_messages_tokens(
                    messages, endpoint_type, image_descriptions
                )
            
            # Try to use the global accurate token counting function
            try:
                from .accurate_token_counter import count_tokens_accurate, ENABLE_ACCURATE_TOKEN_COUNTING
                if ENABLE_ACCURATE_TOKEN_COUNTING:
                    return count_tokens_accurate(messages, endpoint_type, None, image_descriptions)
            except ImportError:
                pass
            
            # Try to import and use the updated token counter from main if available
            try:
                from main import count_tokens_from_messages
                return count_tokens_from_messages(messages, image_descriptions)
            except ImportError:
                # Fallback to simple estimation with image descriptions
                return simple_count_tokens_from_messages(messages, image_descriptions)
        except Exception as e:
            debug_logger.warning(f"Token estimation failed: {e}")
            # Fallback: rough estimate based on character count with image descriptions
            return simple_count_tokens_from_messages(messages, image_descriptions)
    
    def _generate_cache_key(self, messages: List[Dict[str, Any]], is_vision: bool) -> str:
        """Generate cache key for context analysis"""
        import hashlib
        
        # Create a simplified representation for caching
        message_summary = []
        for msg in messages:
            content = msg.get('content', '')
            if isinstance(content, str):
                content_preview = content[:100]  # First 100 chars
            elif isinstance(content, list):
                content_preview = f"list_{len(content)}_items"
            else:
                content_preview = str(type(content))
            
            message_summary.append(f"{msg.get('role', 'unknown')}:{content_preview}")
        
        cache_data = {
            'messages': message_summary,
            'is_vision': is_vision,
            'text_limit': REAL_TEXT_MODEL_TOKENS,
            'vision_limit': REAL_VISION_MODEL_TOKENS
        }
        
        return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
    
    def analyze_context_state(self,
                            messages: List[Dict[str, Any]],
                            is_vision: bool,
                            image_descriptions: Optional[Dict[int, str]] = None,
                            max_tokens: Optional[int] = None) -> ContextAnalysisResult:
        """
        Analyze current context state and determine risk level and recommended strategy
        
        Args:
            messages: List of message dictionaries
            is_vision: Whether this is a vision request
            image_descriptions: Optional dictionary mapping image indices to descriptions
            max_tokens: Optional maximum tokens for response
        
        Returns:
            ContextAnalysisResult with detailed analysis
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(messages, is_vision)
        current_time = time.time()
        
        if (cache_key in self._analysis_cache and
            cache_key in self._cache_timestamps and
            current_time - self._cache_timestamps[cache_key] < CONTEXT_ANALYSIS_CACHE_TTL):
            cached_result = self._analysis_cache[cache_key]
            cached_result.analysis_time = time.time() - start_time
            return cached_result
        
        # Get token count and limits
        endpoint_type = "openai" if is_vision else "anthropic"
        current_tokens = self.estimate_message_tokens(messages, image_descriptions, endpoint_type)
        limit_tokens = self.get_context_limit(is_vision)
        
        # Reserve tokens for response if specified
        if max_tokens and max_tokens > 0:
            available_tokens = limit_tokens - current_tokens - max_tokens
        else:
            available_tokens = limit_tokens - current_tokens
        
        utilization_percent = (current_tokens / limit_tokens) * 100 if limit_tokens > 0 else 100
        
        # Determine risk level
        if utilization_percent >= 100:
            risk_level = ContextRiskLevel.OVERFLOW
        elif utilization_percent >= CONDENSATION_CRITICAL_THRESHOLD * 100:
            risk_level = ContextRiskLevel.CRITICAL
        elif utilization_percent >= CONDENSATION_WARNING_THRESHOLD * 100:
            risk_level = ContextRiskLevel.WARNING
        elif utilization_percent >= CONDENSATION_CAUTION_THRESHOLD * 100:
            risk_level = ContextRiskLevel.CAUTION
        else:
            risk_level = ContextRiskLevel.SAFE
        
        # Determine recommended strategy
        should_condense = False
        if risk_level == ContextRiskLevel.OVERFLOW:
            recommended_strategy = ContextManagementStrategy.EMERGENCY_TRUNCATION
            should_condense = True
        elif risk_level == ContextRiskLevel.CRITICAL:
            recommended_strategy = ContextManagementStrategy.CONDENSATION_AGGRESSIVE
            should_condense = ENABLE_AI_CONDENSATION and len(messages) >= CONDENSATION_MIN_MESSAGES
        elif risk_level == ContextRiskLevel.WARNING:
            recommended_strategy = ContextManagementStrategy.CONDENSATION_LIGHT
            should_condense = ENABLE_AI_CONDENSATION and len(messages) >= CONDENSATION_MIN_MESSAGES
        elif risk_level == ContextRiskLevel.CAUTION:
            recommended_strategy = ContextManagementStrategy.MONITOR_ONLY
            should_condense = False
        else:
            recommended_strategy = ContextManagementStrategy.MONITOR_ONLY
            should_condense = False
        
        # Create result
        result = ContextAnalysisResult(
            risk_level=risk_level,
            utilization_percent=utilization_percent,
            current_tokens=current_tokens,
            limit_tokens=limit_tokens,
            available_tokens=max(0, available_tokens),
            recommended_strategy=recommended_strategy,
            should_condense=should_condense,
            messages_count=len(messages),
            analysis_time=time.time() - start_time,
            metadata={
                'endpoint_type': endpoint_type,
                'max_tokens': max_tokens,
                'condensation_available': CONDENSATION_AVAILABLE,
                'accurate_counting_available': self.token_counter is not None
            }
        )
        
        # Cache the result
        self._analysis_cache[cache_key] = result
        self._cache_timestamps[cache_key] = current_time
        
        # Clean old cache entries
        if len(self._analysis_cache) > CONTEXT_CACHE_SIZE:
            oldest_key = min(self._cache_timestamps.keys(), key=lambda k: self._cache_timestamps[k])
            del self._analysis_cache[oldest_key]
            del self._cache_timestamps[oldest_key]
        
        return result
    
    def should_condense_context(self,
                              messages: List[Dict[str, Any]],
                              is_vision: bool,
                              image_descriptions: Optional[Dict[int, str]] = None) -> bool:
        """
        Determine if context should be condensed based on analysis
        
        Args:
            messages: List of message dictionaries
            is_vision: Whether this is a vision request
            image_descriptions: Optional dictionary mapping image indices to descriptions
        
        Returns:
            True if condensation should be applied
        """
        analysis = self.analyze_context_state(messages, is_vision, image_descriptions)
        return analysis.should_condense
    
    def get_context_management_strategy(self,
                                      messages: List[Dict[str, Any]],
                                      is_vision: bool,
                                      image_descriptions: Optional[Dict[int, str]] = None) -> ContextManagementStrategy:
        """
        Get the recommended context management strategy
        
        Args:
            messages: List of message dictionaries
            is_vision: Whether this is a vision request
            image_descriptions: Optional dictionary mapping image indices to descriptions
        
        Returns:
            Recommended ContextManagementStrategy
        """
        analysis = self.analyze_context_state(messages, is_vision, image_descriptions)
        return analysis.recommended_strategy
    
    async def apply_intelligent_context_management(self,
                                                  messages: List[Dict[str, Any]],
                                                  is_vision: bool,
                                                  max_tokens: Optional[int] = None,
                                                  image_descriptions: Optional[Dict[int, str]] = None) -> ContextManagementResult:
        """
        Apply intelligent context management with AI condensation and multi-level strategies
        
        Args:
            messages: List of message dictionaries
            is_vision: Whether this is a vision request
            max_tokens: Optional maximum tokens for response
            image_descriptions: Optional dictionary mapping image indices to descriptions
        
        Returns:
            ContextManagementResult with detailed operation results
        """
        start_time = time.time()
        original_messages = messages.copy()
        
        # Apply environment details deduplication first to reduce token usage
        deduplicated_messages = messages
        env_tokens_saved = 0
        if self.env_details_manager:
            try:
                dedup_result = self.env_details_manager.deduplicate_environment_details(messages)
                deduplicated_messages = dedup_result.deduplicated_messages
                env_tokens_saved = dedup_result.tokens_saved
                debug_logger.info(f"Environment details deduplication: removed {len(dedup_result.removed_blocks)} blocks, saved {env_tokens_saved} tokens")
            except Exception as e:
                debug_logger.warning(f"Environment details deduplication failed: {e}")
                deduplicated_messages = messages
        
        original_tokens = self.estimate_message_tokens(deduplicated_messages, image_descriptions, "openai" if is_vision else "anthropic")
        
        # Analyze current context state
        analysis = self.analyze_context_state(deduplicated_messages, is_vision, image_descriptions, max_tokens)
        
        debug_logger.info(f"Context analysis: {analysis.risk_level.value} ({analysis.utilization_percent:.1f}% utilization), "
                         f"strategy: {analysis.recommended_strategy.value}")
        
        # Handle different risk levels
        if analysis.risk_level == ContextRiskLevel.SAFE:
            # No action needed
            return ContextManagementResult(
                original_messages=original_messages,
                processed_messages=deduplicated_messages,
                original_tokens=original_tokens,
                final_tokens=original_tokens,
                tokens_saved=env_tokens_saved,
                strategy_used=ContextManagementStrategy.MONITOR_ONLY,
                risk_level=analysis.risk_level,
                processing_time=time.time() - start_time,
                metadata={"analysis": analysis, "action": "none_required", "env_tokens_saved": env_tokens_saved}
            )
        
        elif analysis.risk_level == ContextRiskLevel.CAUTION:
            # Monitor only, no action needed but log warning
            debug_logger.info(f"Context approaching limit ({analysis.utilization_percent:.1f}%), monitoring only")
            return ContextManagementResult(
                original_messages=original_messages,
                processed_messages=deduplicated_messages,
                original_tokens=original_tokens,
                final_tokens=original_tokens,
                tokens_saved=env_tokens_saved,
                strategy_used=ContextManagementStrategy.MONITOR_ONLY,
                risk_level=analysis.risk_level,
                processing_time=time.time() - start_time,
                metadata={"analysis": analysis, "action": "monitoring", "env_tokens_saved": env_tokens_saved}
            )
        
        elif analysis.risk_level in [ContextRiskLevel.WARNING, ContextRiskLevel.CRITICAL]:
            # Apply AI condensation
            if ENABLE_AI_CONDENSATION and self.condensation_engine and analysis.should_condense:
                try:
                    debug_logger.info(f"Applying AI condensation with {analysis.recommended_strategy.value} strategy")
                    
                    # Determine target tokens based on strategy
                    real_limit = self.get_context_limit(is_vision)
                    if analysis.recommended_strategy == ContextManagementStrategy.CONDENSATION_AGGRESSIVE:
                        target_tokens = int(real_limit * CONDENSATION_CAUTION_THRESHOLD)
                    else:  # CONDENSATION_LIGHT
                        target_tokens = int(real_limit * CONDENSATION_WARNING_THRESHOLD)
                    
                    # Apply condensation (use chunk-based if available)
                    if (self.chunk_manager and ENABLE_CHUNK_BASED_CONDENSATION and
                        hasattr(self.condensation_engine, 'condense_messages_chunked')):
                        condensed_messages = await self.condensation_engine.condense_messages_chunked(
                            messages=deduplicated_messages,
                            current_tokens=original_tokens,
                            max_tokens=target_tokens,
                            preferred_strategy=CONDENSATION_DEFAULT_STRATEGY,
                            is_vision=is_vision,
                            image_descriptions=image_descriptions
                        )
                        debug_logger.info("Applied chunk-based condensation")
                    else:
                        # Fallback to traditional condensation
                        condensed_messages = await self.condensation_engine.condense_messages(
                            messages=deduplicated_messages,
                            current_tokens=original_tokens,
                            target_tokens=target_tokens,
                            preferred_strategy=CONDENSATION_DEFAULT_STRATEGY,
                            is_vision=is_vision,
                            image_descriptions=image_descriptions
                        )
                        debug_logger.info("Applied traditional condensation")
                    
                    final_tokens = self.estimate_message_tokens(
                        condensed_messages, image_descriptions, "openai" if is_vision else "anthropic"
                    )
                    
                    total_tokens_saved = env_tokens_saved + (original_tokens - final_tokens)
                    return ContextManagementResult(
                        original_messages=original_messages,
                        processed_messages=condensed_messages,
                        original_tokens=original_tokens,
                        final_tokens=final_tokens,
                        tokens_saved=total_tokens_saved,
                        strategy_used=analysis.recommended_strategy,
                        risk_level=analysis.risk_level,
                        processing_time=time.time() - start_time,
                        metadata={
                            "analysis": analysis,
                            "action": "ai_condensation",
                            "condensation_metadata": condensed_messages.metadata if hasattr(condensed_messages, 'metadata') else {},
                            "target_tokens": target_tokens,
                            "env_tokens_saved": env_tokens_saved
                        }
                    )
                    
                except Exception as e:
                    debug_logger.error(f"AI condensation failed: {e}")
                    # Fall through to emergency truncation
        
        # Emergency truncation for overflow or failed condensation
        debug_logger.warning("Applying emergency truncation")
        real_limit = self.get_context_limit(is_vision)
        
        # Calculate minimal target - leave small buffer only for API overhead
        api_overhead = 100
        target_tokens = real_limit - api_overhead
        
        truncated_messages, final_tokens = self.truncate_messages_smart(deduplicated_messages, target_tokens)
        
        total_tokens_saved = env_tokens_saved + (original_tokens - final_tokens)
        return ContextManagementResult(
            original_messages=original_messages,
            processed_messages=truncated_messages,
            original_tokens=original_tokens,
            final_tokens=final_tokens,
            tokens_saved=total_tokens_saved,
            strategy_used=ContextManagementStrategy.EMERGENCY_TRUNCATION,
            risk_level=ContextRiskLevel.OVERFLOW,
            processing_time=time.time() - start_time,
            metadata={
                "analysis": analysis,
                "action": "emergency_truncation",
                "target_tokens": target_tokens,
                "env_tokens_saved": env_tokens_saved,
                "note": "Client should manage context to avoid this truncation"
            }
        )
    
    def validate_context_window(self,
                              messages: List[Dict[str, Any]],
                              is_vision: bool,
                              max_tokens: Optional[int] = None,
                              image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[bool, int, str]:
        """
        Enhanced context validation with intelligent analysis
        
        This method now provides detailed analysis of context state and recommendations
        for context management strategies.
        
        Returns:
        - (is_valid, estimated_tokens, reason)
        """
        endpoint_type = "openai" if is_vision else "anthropic"
        estimated_tokens = self.estimate_message_tokens(messages, image_descriptions, endpoint_type)
        
        # Analyze context state
        analysis = self.analyze_context_state(messages, is_vision, image_descriptions, max_tokens)
        
        # Use REAL hard limits for validation
        real_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
        
        # Only reserve response tokens if user specified max_tokens
        if max_tokens and max_tokens > 0:
            response_limit = max_tokens
        else:
            response_limit = 0
        
        total_needed = estimated_tokens + response_limit
        
        if total_needed <= real_limit:
            if analysis.risk_level in [ContextRiskLevel.WARNING, ContextRiskLevel.CRITICAL]:
                reason = f"Context within limits but approaching threshold: {analysis.utilization_percent:.1f}% utilization. Consider context management."
                debug_logger.info(f"Context OK but caution advised: {reason}")
                return True, estimated_tokens, reason
            else:
                debug_logger.debug(f"Context window OK: {estimated_tokens} input + {response_limit} response = {total_needed} <= {real_limit} ({endpoint_type} endpoint)")
                return True, estimated_tokens, ""
        
        overflow = total_needed - real_limit
        reason = f"Hard context limit exceeded: {total_needed} tokens needed > {real_limit} limit ({endpoint_type} endpoint). Overflow: {overflow} tokens. Risk level: {analysis.risk_level.value}"
        debug_logger.warning(f"Context validation failed: {reason}")
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
    
    async def handle_context_overflow_async(self,
                                          messages: List[Dict[str, Any]],
                                          is_vision: bool,
                                          max_tokens: Optional[int] = None,
                                          image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Enhanced async context overflow handling with intelligent management
        
        This method now uses the full intelligent context management system with
        AI condensation, multi-level validation, and comprehensive analysis.
        
        Args:
            messages: List of message dictionaries
            is_vision: Whether this is a vision request
            max_tokens: Optional maximum tokens for response
            image_descriptions: Optional dictionary mapping image indices to descriptions
        
        Returns:
        - (processed_messages, metadata)
        """
        try:
            # Use the new intelligent context management
            result = await self.apply_intelligent_context_management(
                messages, is_vision, max_tokens, image_descriptions
            )
            
            # Convert to legacy format for backward compatibility
            if result.strategy_used == ContextManagementStrategy.MONITOR_ONLY:
                return result.processed_messages, {
                    "truncated": False,
                    "original_tokens": result.original_tokens,
                    "final_tokens": result.final_tokens,
                    "risk_level": result.risk_level.value,
                    "utilization_percent": result.metadata.get("analysis", {}).utilization_percent if result.metadata.get("analysis") else 0,
                    "method": "intelligent_monitoring"
                }
            else:
                return result.processed_messages, {
                    "truncated": True,
                    "original_tokens": result.original_tokens,
                    "final_tokens": result.final_tokens,
                    "tokens_saved": result.tokens_saved,
                    "truncation_reason": f"Intelligent context management: {result.strategy_used.value}",
                    "messages_removed": len(result.original_messages) - len(result.processed_messages),
                    "method": result.strategy_used.value,
                    "risk_level": result.risk_level.value,
                    "utilization_percent": result.metadata.get("analysis", {}).utilization_percent if result.metadata.get("analysis") else 0,
                    "processing_time": result.processing_time,
                    "metadata": result.metadata
                }
                
        except Exception as e:
            debug_logger.error(f"Intelligent context management failed: {e}")
            # Fallback to traditional method
            return await self._fallback_traditional_handling(messages, is_vision, max_tokens, image_descriptions)
    
    async def _fallback_traditional_handling(self,
                                           messages: List[Dict[str, Any]],
                                           is_vision: bool,
                                           max_tokens: Optional[int] = None,
                                           image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fallback to traditional context handling for backward compatibility
        """
        is_valid, current_tokens, reason = self.validate_context_window(messages, is_vision, max_tokens, image_descriptions)
        
        if is_valid:
            return messages, {"truncated": False, "original_tokens": current_tokens}
        
        # Get real limit for this endpoint type
        real_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
        
        debug_logger.warning(f"Context overflow detected: {current_tokens} tokens exceeds limit {real_limit}")
        
        # Try AI condensation first if available
        if CONDENSATION_AVAILABLE:
            try:
                debug_logger.info("Attempting AI-powered message condensation (fallback)")
                condensed_messages, condensation_metadata = await condense_messages_if_needed(
                    messages, current_tokens, real_limit, is_vision=is_vision
                )
                
                if condensation_metadata.get("condensed", False):
                    final_tokens = condensation_metadata.get("final_tokens", current_tokens)
                    
                    # Check if condensation was sufficient
                    condensation_valid, _, _ = self.validate_context_window(
                        condensed_messages, is_vision, max_tokens, image_descriptions
                    )
                    
                    if condensation_valid:
                        metadata = {
                            "truncated": True,
                            "original_tokens": current_tokens,
                            "final_tokens": final_tokens,
                            "truncation_reason": f"AI condensation successful: {condensation_metadata.get('strategy_used', 'unknown')}",
                            "messages_removed": len(messages) - len(condensed_messages),
                            "tokens_saved": condensation_metadata.get("tokens_saved", 0),
                            "condensation_metadata": condensation_metadata,
                            "method": "ai_condensation_fallback"
                        }
                        
                        debug_logger.info(f"AI condensation successful (fallback): saved {condensation_metadata.get('tokens_saved', 0)} tokens")
                        return condensed_messages, metadata
                    else:
                        debug_logger.warning("AI condensation insufficient, falling back to truncation")
                else:
                    debug_logger.info("AI condensation not applied, using traditional truncation")
                    
            except Exception as e:
                debug_logger.error(f"AI condensation failed (fallback): {e}")
                debug_logger.info("Falling back to traditional truncation")
        
        # Fallback to traditional truncation
        debug_logger.info("Using traditional message truncation (fallback)")
        
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
            "method": "traditional_truncation_fallback",
            "note": "Client should manage context to avoid this truncation"
        }
        
        return truncated_msgs, metadata

    def handle_context_overflow(self,
                              messages: List[Dict[str, Any]],
                              is_vision: bool,
                              max_tokens: Optional[int] = None,
                              image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Enhanced sync context overflow handling with intelligent analysis
        
        This method provides intelligent context analysis and recommendations
        even in sync mode, though AI condensation requires async operation.
        
        Args:
            messages: List of message dictionaries
            is_vision: Whether this is a vision request
            max_tokens: Optional maximum tokens for response
            image_descriptions: Optional dictionary mapping image indices to descriptions
        
        Returns:
        - (processed_messages, metadata)
        """
        try:
            # Analyze context state first
            analysis = self.analyze_context_state(messages, is_vision, image_descriptions, max_tokens)
            
            # Validate context window
            is_valid, current_tokens, reason = self.validate_context_window(messages, is_vision, max_tokens, image_descriptions)
            
            if is_valid:
                return messages, {
                    "truncated": False,
                    "original_tokens": current_tokens,
                    "final_tokens": current_tokens,
                    "risk_level": analysis.risk_level.value,
                    "utilization_percent": analysis.utilization_percent,
                    "recommended_strategy": analysis.recommended_strategy.value,
                    "should_condense": analysis.should_condense,
                    "method": "intelligent_analysis"
                }
            
            # For overflow cases in sync mode, we can only do traditional truncation
            # but we provide detailed analysis and recommendations
            real_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
            
            debug_logger.warning(f"Context overflow in sync mode: {current_tokens} tokens exceeds hard limit {real_limit}")
            debug_logger.info(f"Risk level: {analysis.risk_level.value}, Recommended strategy: {analysis.recommended_strategy.value}")
            
            # Only truncate when we exceed HARD limits that would cause API rejection
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
                "risk_level": analysis.risk_level.value,
                "utilization_percent": analysis.utilization_percent,
                "recommended_strategy": analysis.recommended_strategy.value,
                "should_condense": analysis.should_condense,
                "method": "traditional_truncation_with_analysis",
                "note": "Consider using async version for AI condensation capabilities"
            }
            
            return truncated_msgs, metadata
            
        except Exception as e:
            debug_logger.error(f"Enhanced context management failed: {e}")
            # Fallback to basic handling
            return self._basic_sync_handling(messages, is_vision, max_tokens, image_descriptions)
    
    def _basic_sync_handling(self,
                           messages: List[Dict[str, Any]],
                           is_vision: bool,
                           max_tokens: Optional[int] = None,
                           image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Basic sync handling for backward compatibility
        """
        is_valid, current_tokens, reason = self.validate_context_window(messages, is_vision, max_tokens, image_descriptions)
        
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
            "method": "basic_truncation",
            "note": "Client should manage context to avoid this truncation"
        }
        
        return truncated_msgs, metadata
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for the context manager
        """
        return {
            "cache_size": len(self._analysis_cache),
            "cache_limit": CONTEXT_CACHE_SIZE,
            "condensation_engine_available": self.condensation_engine is not None,
            "accurate_token_counter_available": self.token_counter is not None,
            "ai_condensation_enabled": ENABLE_AI_CONDENSATION,
            "configuration": {
                "caution_threshold": CONDENSATION_CAUTION_THRESHOLD,
                "warning_threshold": CONDENSATION_WARNING_THRESHOLD,
                "critical_threshold": CONDENSATION_CRITICAL_THRESHOLD,
                "min_messages": CONDENSATION_MIN_MESSAGES,
                "max_messages": CONDENSATION_MAX_MESSAGES
            }
        }
    
    def clear_caches(self) -> None:
        """Clear all internal caches"""
        self._analysis_cache.clear()
        self._cache_timestamps.clear()
        
        if self.token_counter:
            self.token_counter.clear_cache()
        
        if self.condensation_engine:
            self.condensation_engine.clear_cache()
        
        debug_logger.info("All context manager caches cleared")

# Global instance
context_manager = ContextWindowManager()

# ===== Enhanced Public API Functions =====

async def validate_and_truncate_context_async(messages: List[Dict[str, Any]],
                                            is_vision: bool,
                                            max_tokens: Optional[int] = None,
                                            image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Enhanced async entry point for intelligent context window management
    
    This function now provides full intelligent context management with AI condensation,
    multi-level validation, and comprehensive analysis.
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        max_tokens: Optional maximum tokens for response
        image_descriptions: Optional dictionary mapping image indices to descriptions
    
    Returns:
    - (processed_messages, metadata) with enhanced metadata including risk analysis
    """
    return await context_manager.handle_context_overflow_async(messages, is_vision, max_tokens, image_descriptions)

def validate_and_truncate_context(messages: List[Dict[str, Any]],
                                is_vision: bool,
                                max_tokens: Optional[int] = None,
                                image_descriptions: Optional[Dict[int, str]] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Enhanced sync entry point for context window management with intelligent analysis
    
    This function provides intelligent context analysis and recommendations even in sync mode.
    For full AI condensation capabilities, use the async version.
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        max_tokens: Optional maximum tokens for response
        image_descriptions: Optional dictionary mapping image indices to descriptions
    
    Returns:
    - (processed_messages, metadata) with enhanced metadata including risk analysis
    """
    return context_manager.handle_context_overflow(messages, is_vision, max_tokens, image_descriptions)

async def apply_intelligent_context_management(messages: List[Dict[str, Any]],
                                             is_vision: bool,
                                             max_tokens: Optional[int] = None,
                                             image_descriptions: Optional[Dict[int, str]] = None) -> ContextManagementResult:
    """
    Apply full intelligent context management with AI condensation
    
    This is the main entry point for the new intelligent context management system.
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        max_tokens: Optional maximum tokens for response
        image_descriptions: Optional dictionary mapping image indices to descriptions
    
    Returns:
    - ContextManagementResult with detailed operation results
    """
    return await context_manager.apply_intelligent_context_management(messages, is_vision, max_tokens, image_descriptions)

def analyze_context_state(messages: List[Dict[str, Any]],
                         is_vision: bool,
                         image_descriptions: Optional[Dict[int, str]] = None,
                         max_tokens: Optional[int] = None) -> ContextAnalysisResult:
    """
    Analyze current context state and get recommendations
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        image_descriptions: Optional dictionary mapping image indices to descriptions
        max_tokens: Optional maximum tokens for response
    
    Returns:
    - ContextAnalysisResult with detailed analysis and recommendations
    """
    return context_manager.analyze_context_state(messages, is_vision, image_descriptions, max_tokens)

def should_condense_context(messages: List[Dict[str, Any]],
                           is_vision: bool,
                           image_descriptions: Optional[Dict[int, str]] = None) -> bool:
    """
    Determine if context should be condensed based on intelligent analysis
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        image_descriptions: Optional dictionary mapping image indices to descriptions
    
    Returns:
    - True if condensation is recommended
    """
    return context_manager.should_condense_context(messages, is_vision, image_descriptions)

def get_context_management_strategy(messages: List[Dict[str, Any]],
                                   is_vision: bool,
                                   image_descriptions: Optional[Dict[int, str]] = None) -> ContextManagementStrategy:
    """
    Get the recommended context management strategy
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        image_descriptions: Optional dictionary mapping image indices to descriptions
    
    Returns:
    - Recommended ContextManagementStrategy
    """
    return context_manager.get_context_management_strategy(messages, is_vision, image_descriptions)

def get_context_info(messages: List[Dict[str, Any]], is_vision: bool,
                    image_descriptions: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """
    Get enhanced context window information with intelligent analysis
    
    This function now provides detailed context analysis including risk levels
    and management recommendations.
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        image_descriptions: Optional dictionary mapping image indices to descriptions
    
    Returns:
    - Enhanced context information with intelligent analysis
    """
    # Get basic context info
    estimated_tokens = context_manager.estimate_message_tokens(messages, image_descriptions, "openai" if is_vision else "anthropic")
    hard_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
    endpoint_type = "vision" if is_vision else "text"
    
    # Get intelligent analysis
    analysis = context_manager.analyze_context_state(messages, is_vision, image_descriptions)
    
    return {
        "estimated_tokens": estimated_tokens,
        "hard_limit": hard_limit,
        "endpoint_type": endpoint_type,
        "utilization_percent": analysis.utilization_percent,
        "available_tokens": analysis.available_tokens,
        "risk_level": analysis.risk_level.value,
        "recommended_strategy": analysis.recommended_strategy.value,
        "should_condense": analysis.should_condense,
        "messages_count": analysis.messages_count,
        "analysis_time": analysis.analysis_time,
        "intelligent_management_available": ENABLE_AI_CONDENSATION and CONDENSATION_AVAILABLE,
        "accurate_counting_available": context_manager.token_counter is not None,
        "note": "Enhanced context management with AI condensation available"
    }

def get_context_performance_stats() -> Dict[str, Any]:
    """
    Get performance statistics for the context management system
    
    Returns:
    - Performance statistics and configuration information
    """
    return context_manager.get_performance_stats()

def clear_context_caches() -> None:
    """Clear all context management caches"""
    context_manager.clear_caches()

# ===== Legacy API Functions (for backward compatibility) =====

def get_simple_context_info(messages: List[Dict[str, Any]], is_vision: bool,
                           image_descriptions: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """
    Legacy context info function for backward compatibility
    
    Args:
        messages: List of message dictionaries
        is_vision: Whether this is a vision request
        image_descriptions: Optional dictionary mapping image indices to descriptions
    
    Returns:
    - Basic context information (legacy format)
    """
    estimated_tokens = context_manager.estimate_message_tokens(messages, image_descriptions)
    hard_limit = REAL_VISION_MODEL_TOKENS if is_vision else REAL_TEXT_MODEL_TOKENS
    endpoint_type = "vision" if is_vision else "text"
    
    return {
        "estimated_tokens": estimated_tokens,
        "hard_limit": hard_limit,
        "endpoint_type": endpoint_type,
        "utilization_percent": round((estimated_tokens / hard_limit) * 100, 1),
        "available_tokens": max(0, hard_limit - estimated_tokens),
        "note": "Legacy function - consider using get_context_info for enhanced analysis"
    }