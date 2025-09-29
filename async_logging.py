#!/usr/bin/env python3
"""
High-performance async logging system for anthropic-proxy.
Reduces logging overhead by using background tasks and optimized serialization.
"""

import asyncio
import json
import time
import os
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
from collections import deque
import logging
import logging.handlers

# Import performance configuration
from logging_performance_config import logging_config

# Performance settings from config
MAX_QUEUE_SIZE = logging_config.max_queue_size
BATCH_SIZE = logging_config.batch_size  
BATCH_TIMEOUT = logging_config.batch_timeout

class LogLevel:
    """Log level constants for performance optimization"""
    CRITICAL = 0  # Always log (errors, critical metrics)
    IMPORTANT = 1  # Log in non-production or when explicitly enabled
    DEBUG = 2     # Only in debug mode

class PerformantLogEntry:
    """Memory-efficient log entry with minimal overhead"""
    __slots__ = ['timestamp', 'level', 'type', 'req_id', 'data']
    
    def __init__(self, log_type: str, req_id: str, data: Dict[str, Any], level: int = LogLevel.IMPORTANT):
        self.timestamp = time.time()  # Use timestamp for performance
        self.level = level
        self.type = log_type
        self.req_id = req_id
        self.data = data

class AsyncLogBatcher:
    """Batches log entries and writes them asynchronously"""
    
    def __init__(self, log_file: str, batch_size: int = BATCH_SIZE, batch_timeout: float = BATCH_TIMEOUT):
        self.log_file = Path(log_file)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch: List[PerformantLogEntry] = []
        self.last_flush = time.time()
        self.lock = asyncio.Lock()
        self._flush_task = None
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Start background flush timer
        self._start_background_flush_timer()
    
    def _start_background_flush_timer(self):
        """Start a background task that periodically flushes the batch"""
        async def flush_timer():
            while True:
                try:
                    await asyncio.sleep(self.batch_timeout)
                    async with self.lock:
                        if self.batch and (time.time() - self.last_flush) >= self.batch_timeout:
                            await self._flush_batch()
                except Exception as e:
                    print(f"[ASYNC_LOG_ERROR] Background flush timer error: {e}")
                    
        # Only start timer if not already running
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(flush_timer())

    async def add_entry(self, entry: PerformantLogEntry):
        """Add entry to batch (non-blocking)"""
        # Use performance level from config to filter entries
        if entry.level > logging_config.performance_level:
            return  # Skip if below threshold
        
        async with self.lock:
            self.batch.append(entry)
            
            # Flush if batch is full (reduced size for better responsiveness)
            if len(self.batch) >= max(5, self.batch_size // 10):  # Much smaller batch for frequent flushing
                await self._flush_batch()
    
    def _handle_write_task_result(self, task):
        """Handle the result of write batch task to catch exceptions"""
        try:
            # This will raise any exception that occurred in the task
            task.result()
        except Exception as e:
            print(f"[ASYNC_LOG_TASK_ERROR] Write task failed: {e}")
            import traceback
            print(f"[ASYNC_LOG_TASK_ERROR] Traceback: {traceback.format_exc()}")
    
    async def _flush_batch(self):
        """Flush current batch to file"""
        if not self.batch:
            print(f"[ASYNC_LOG_DEBUG] Flush called but batch is empty")
            return
            
        print(f"[ASYNC_LOG_DEBUG] Flushing batch of {len(self.batch)} entries")
            
        # Move current batch to local variable for processing
        current_batch = self.batch.copy()
        self.batch.clear()
        self.last_flush = time.time()
        
        # Process batch in background to avoid blocking
        task = asyncio.create_task(self._write_batch_async(current_batch))
        # Add task exception handler to catch silent failures
        task.add_done_callback(self._handle_write_task_result)
    
    async def _write_batch_async(self, batch: List[PerformantLogEntry]):
        """Write batch to file asynchronously"""
        try:
            # Pre-serialize all entries (most expensive operation)
            serialized_entries = []
            for entry in batch:
                serialized = self._serialize_entry(entry)
                if serialized:
                    serialized_entries.append(serialized)
            
            # Write all entries at once using asyncio.to_thread
            if serialized_entries:
                def write_to_file():
                    with open(self.log_file, 'a', encoding='utf-8') as f:
                        for serialized in serialized_entries:
                            f.write(serialized + '\n')
                
                await asyncio.to_thread(write_to_file)
                        
        except Exception as e:
            # Fallback to console if file write fails
            print(f"[ASYNC_LOG_ERROR] Failed to write batch: {e}")
            import traceback
            print(f"[ASYNC_LOG_ERROR] Traceback: {traceback.format_exc()}")
    
    def _serialize_entry(self, entry: PerformantLogEntry) -> Optional[str]:
        """Serialize log entry"""
        try:
            log_data = {
                "timestamp": datetime.fromtimestamp(entry.timestamp, timezone.utc).isoformat(),
                "level": entry.level,
                "type": entry.type,
                "req_id": entry.req_id,
                "data": self._optimize_data(entry.data)
            }
            return json.dumps(log_data, separators=(',', ':'), ensure_ascii=False)
        except Exception:
            return None
    
    def _optimize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data for serialization - no truncation, just return as-is for full upstream logs"""
        if not isinstance(data, dict):
            return data
            
        # For upstream logs, we want full data without any truncation
        # The fire-and-forget async nature means this won't affect performance
        return data
    
    async def force_flush(self):
        """Force flush all pending entries"""
        async with self.lock:
            await self._flush_batch()

class AsyncUpstreamLogger:
    """High-performance upstream response logger"""
    
    def __init__(self):
        self.batcher = AsyncLogBatcher("logs/upstream_responses.json")
        self.request_batcher = AsyncLogBatcher("logs/upstream_requests.json")  # Add request logging
        self.metrics_batcher = AsyncLogBatcher("logs/performance_metrics.json")
        self.error_batcher = AsyncLogBatcher("logs/error_logs.json")
        
        # Performance counters
        self.request_count = 0
        self.total_response_time = 0.0
    
    async def log_upstream_request_async(
        self, 
        req_id: str,
        endpoint_type: str,
        model: str,
        url: str,
        payload: Any,
        headers: Dict[str, str]
    ):
        """Log upstream request asynchronously with full payload - no truncation"""
        
        # Extract essential request info
        has_thinking = isinstance(payload, dict) and "thinking" in payload
        message_count = len(payload.get("messages", [])) if isinstance(payload, dict) else 0
        max_tokens = payload.get("max_tokens") if isinstance(payload, dict) else None
        
        # Get payload size for logging but don't truncate
        payload_str = str(payload) if payload else ""
        payload_size = len(payload_str)
        
        log_entry = PerformantLogEntry(
            "upstream_request",
            req_id,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "endpoint_type": endpoint_type,
                "model": model,
                "url": url,
                "message_count": message_count,
                "max_tokens": max_tokens,
                "has_thinking_parameter": has_thinking,
                "thinking_value": payload.get("thinking") if has_thinking else None,
                "headers": {k: v for k, v in headers.items() if k.lower() not in ["authorization", "x-api-key"]},  # Exclude auth headers
                "payload_size": payload_size,
                "payload": payload  # Store full payload without truncation
            },
            level=LogLevel.IMPORTANT
        )
        
        await self.request_batcher.add_entry(log_entry)

    async def log_upstream_response_async(
        self, 
        req_id: str,
        response: Any,
        endpoint_type: str,
        model: str,
        request_payload: Any,
        request_start_time: float
    ):
        """Log upstream response asynchronously with minimal overhead"""
        response_time = time.time() - request_start_time
        self.request_count += 1
        self.total_response_time += response_time
        
        # Quick performance check - only extract essential data
        status_code = getattr(response, 'status_code', 0)
        content_length = len(getattr(response, 'content', b'')) if hasattr(response, 'content') else 0
        
        # Use config to determine log level and detail
        log_level = logging_config.get_log_level_for_response(response_time, status_code)
        should_log_detailed = logging_config.should_log_detailed_upstream(response_time, status_code)
        
        # Create minimal log entry for performance
        log_data = {
            "endpoint_type": endpoint_type,
            "model": model,
            "status_code": status_code,
            "response_time_ms": round(response_time * 1000, 2),
            "content_length": content_length,
            "success": status_code < 400
        }
        
        # Add detailed data only if performance config allows it
        if should_log_detailed:
            try:
                if logging_config.log_request_payloads:
                    log_data["url"] = str(getattr(response, 'url', ''))
                    log_data["method"] = getattr(getattr(response, 'request', None), 'method', 'POST')
                
                # Add response body for errors or detailed logging
                if (status_code >= 400 or response_time > 1.0 or logging_config.performance_level <= 1) and logging_config.log_response_bodies:
                    # Skip JSON parsing for large responses if configured
                    if (content_length > logging_config.large_response_threshold and 
                        logging_config.skip_json_parsing_for_large_responses):
                        log_data["response_preview"] = "[LARGE_RESPONSE_SKIPPED]"
                    else:
                        try:
                            if hasattr(response, 'json'):
                                response_body = response.json()
                                # For balanced or max_detail levels, include more complete response
                                if logging_config.performance_level <= 1:  # balanced or max_detail
                                    log_data["response_body"] = response_body  # Full response
                                    log_data["response_preview"] = self._extract_key_info(response_body)
                                else:
                                    log_data["response_preview"] = self._extract_key_info(response_body)
                        except:
                            # Fallback to raw text preview if JSON parsing fails
                            try:
                                if hasattr(response, 'text'):
                                    text_preview = response.text[:logging_config.max_response_body_log]
                                    log_data["response_text_preview"] = text_preview
                            except:
                                pass
                            pass
                        
            except Exception:
                pass  # Skip detailed logging if it fails
        
        # Queue for async writing
        entry = PerformantLogEntry("upstream_response", req_id, log_data, log_level)
        await self.batcher.add_entry(entry)
        
        # Log performance metrics periodically
        if self.request_count % 100 == 0:  # Every 100 requests
            await self._log_performance_metrics()
    
    def _extract_key_info(self, response_body: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key information from response body, handling both OpenAI and Anthropic formats"""
        key_info = {}
        
        # Common error fields
        if 'error' in response_body:
            key_info['error'] = response_body['error']
        
        # Usage information (always important)
        if 'usage' in response_body:
            key_info['usage'] = response_body['usage']
        
        # OpenAI format - Message content (truncated)
        if 'choices' in response_body and response_body['choices']:
            message = response_body['choices'][0].get('message', {})
            content = message.get('content', '')
            reasoning_content = message.get('reasoning_content', '')
            
            # Set reasoning flags if reasoning_content exists
            if reasoning_content:
                key_info['has_reasoning'] = True
                key_info['reasoning_available'] = True
            
            # Determine content preview based on what's available
            if reasoning_content and not content:
                # If main content is empty but reasoning exists, use reasoning
                key_info['content_preview'] = reasoning_content[:200] + ('...' if len(reasoning_content) > 200 else '')
            elif content:
                key_info['content_preview'] = content[:200] + ('...' if len(content) > 200 else '')
            else:
                key_info['content_preview'] = ""
        
        # Anthropic format - Message content (truncated)
        if 'content' in response_body and isinstance(response_body['content'], list):
            text_content = []
            for block in response_body['content']:
                if isinstance(block, dict) and block.get('type') == 'text':
                    text_content.append(block.get('text', ''))
            
            if text_content:
                full_content = '\n'.join(text_content)
                key_info['content_preview'] = full_content[:200] + ('...' if len(full_content) > 200 else '')
        
        # Include model and other important fields
        for field in ['model', 'id', 'object', 'stop_reason', 'finish_reason']:
            if field in response_body:
                key_info[field] = response_body[field]
        
        return key_info
    
    async def _log_performance_metrics(self):
        """Log aggregated performance metrics"""
        avg_response_time = self.total_response_time / self.request_count if self.request_count > 0 else 0
        
        metrics_data = {
            "total_requests": self.request_count,
            "avg_response_time_ms": round(avg_response_time * 1000, 2),
            "requests_per_minute": round(self.request_count / (time.time() / 60), 2)
        }
        
        entry = PerformantLogEntry("performance_metrics", "system", metrics_data, LogLevel.IMPORTANT)
        await self.metrics_batcher.add_entry(entry)
    
    async def log_error_async(self, req_id: str, error_context: Dict[str, Any]):
        """Log errors asynchronously"""
        entry = PerformantLogEntry("error", req_id, error_context, LogLevel.CRITICAL)
        await self.error_batcher.add_entry(entry)
    
    async def shutdown(self):
        """Gracefully shutdown and flush all pending logs"""
        await self.batcher.force_flush()
        await self.metrics_batcher.force_flush() 
        await self.error_batcher.force_flush()

# Global async logger instance
_async_logger: Optional[AsyncUpstreamLogger] = None

def get_async_logger() -> AsyncUpstreamLogger:
    """Get global async logger instance"""
    global _async_logger
    if _async_logger is None:
        _async_logger = AsyncUpstreamLogger()
    return _async_logger

def log_upstream_request_fire_and_forget(
    req_id: str,
    endpoint_type: str,
    model: str,
    url: str,
    payload: Any,
    headers: Dict[str, str]
):
    """Fire-and-forget logging function for upstream requests"""
    logger = get_async_logger()
    
    # Create background task that won't block the main request
    asyncio.create_task(
        logger.log_upstream_request_async(
            req_id, endpoint_type, model, url, payload, headers
        )
    )

def log_upstream_streaming_response_fire_and_forget(
    req_id: str,
    status_code: int,
    response_data: Dict[str, Any],
    endpoint_type: str,
    model: str,
    request_payload: Any,
    request_start_time: float,
    error_info: Dict[str, Any] = None
):
    """Fire-and-forget logging function for streaming responses"""
    logger = get_async_logger()
    
    # Create a mock response object for compatibility with existing logging
    class MockStreamingResponse:
        def __init__(self, status_code: int, response_data: Dict[str, Any], error_info: Dict[str, Any] = None):
            self.status_code = status_code
            self.response_data = response_data
            self.error_info = error_info
            self._content = json.dumps(response_data).encode('utf-8') if response_data else b''
            
        @property
        def content(self):
            return self._content
            
        def json(self):
            return self.response_data
            
        @property
        def url(self):
            return f"https://streaming-{endpoint_type}"
    
    mock_response = MockStreamingResponse(status_code, response_data, error_info)
    
    # Create background task that won't block the main request
    asyncio.create_task(
        logger.log_upstream_response_async(
            req_id, mock_response, endpoint_type, model, request_payload, request_start_time
        )
    )

def log_upstream_response_fire_and_forget(
    req_id: str,
    response: Any,
    endpoint_type: str,
    model: str,
    request_payload: Any,
    request_start_time: float
):
    """Fire-and-forget logging function for minimal performance impact"""
    logger = get_async_logger()
    
    # Create background task that won't block the main request
    asyncio.create_task(
        logger.log_upstream_response_async(
            req_id, response, endpoint_type, model, request_payload, request_start_time
        )
    )

def log_error_fire_and_forget(req_id: str, error_context: Dict[str, Any]):
    """Fire-and-forget error logging"""
    logger = get_async_logger()
    asyncio.create_task(logger.log_error_async(req_id, error_context))

# Cleanup function for graceful shutdown
async def shutdown_async_logging():
    """Shutdown async logging gracefully"""
    global _async_logger
    if _async_logger:
        await _async_logger.shutdown()
        _async_logger = None