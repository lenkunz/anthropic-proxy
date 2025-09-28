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
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(exist_ok=True)
    
    async def add_entry(self, entry: PerformantLogEntry):
        """Add entry to batch (non-blocking)"""
        # Use performance level from config to filter entries
        if entry.level > logging_config.performance_level:
            return  # Skip if below threshold
            
        async with self.lock:
            self.batch.append(entry)
            
            # Flush if batch is full or timeout reached
            now = time.time()
            if len(self.batch) >= self.batch_size or (now - self.last_flush) >= self.batch_timeout:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush current batch to file"""
        if not self.batch:
            return
            
        # Move current batch to local variable for processing
        current_batch = self.batch.copy()
        self.batch.clear()
        self.last_flush = time.time()
        
        # Process batch in background to avoid blocking
        asyncio.create_task(self._write_batch_async(current_batch))
    
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
        """Optimize data for serialization (remove/truncate large values)"""
        if not isinstance(data, dict):
            return data
            
        optimized = {}
        for key, value in data.items():
            # Skip expensive operations based on performance config
            if key in ['response_headers', 'response_body_preview'] and not logging_config.log_response_headers:
                optimized[key] = "[TRUNCATED]"
            elif key == 'request_payload_preview' and not logging_config.log_request_payloads:
                optimized[key] = "[TRUNCATED]"
            elif isinstance(value, str) and len(value) > 500:
                # Truncate long strings for performance
                optimized[key] = value[:500] + f"... [TRUNCATED {len(value)-500} chars]"
            else:
                optimized[key] = value
        
        return optimized
    
    async def force_flush(self):
        """Force flush all pending entries"""
        async with self.lock:
            await self._flush_batch()

class AsyncUpstreamLogger:
    """High-performance upstream response logger"""
    
    def __init__(self):
        self.batcher = AsyncLogBatcher("logs/upstream_responses.json")
        self.metrics_batcher = AsyncLogBatcher("logs/performance_metrics.json")
        self.error_batcher = AsyncLogBatcher("logs/error_logs.json")
        
        # Performance counters
        self.request_count = 0
        self.total_response_time = 0.0
    
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
                
                # Add response body for errors or slow requests
                if (status_code >= 400 or response_time > 1.0) and logging_config.log_response_bodies:
                    # Skip JSON parsing for large responses if configured
                    if (content_length > logging_config.large_response_threshold and 
                        logging_config.skip_json_parsing_for_large_responses):
                        log_data["response_preview"] = "[LARGE_RESPONSE_SKIPPED]"
                    else:
                        try:
                            if hasattr(response, 'json'):
                                response_body = response.json()
                                log_data["response_preview"] = self._extract_key_info(response_body)
                        except:
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
        """Extract only key information from response body"""
        key_info = {}
        
        # Common error fields
        if 'error' in response_body:
            key_info['error'] = response_body['error']
        
        # Usage information (always important)
        if 'usage' in response_body:
            key_info['usage'] = response_body['usage']
        
        # Message content (truncated)
        if 'choices' in response_body and response_body['choices']:
            content = response_body['choices'][0].get('message', {}).get('content', '')
            if content:
                key_info['content_preview'] = content[:200] + ('...' if len(content) > 200 else '')
        
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