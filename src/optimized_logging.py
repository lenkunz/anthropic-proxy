#!/usr/bin/env python3
"""
Enhanced logging configuration with performance optimizations.
Reduces logging overhead while maintaining observability.
"""

import logging
import json
import time
import os
from typing import Dict, Any, Optional
from contextlib import contextmanager
from threading import local

# Performance-optimized logging levels
PERF_LEVEL = 25  # Custom level between INFO(20) and WARNING(30)
logging.addLevelName(PERF_LEVEL, "PERF")

# Thread-local storage for request context
_request_context = local()

class PerformanceOptimizedFormatter(logging.Formatter):
    """Formatter optimized for minimal overhead"""
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self._base_record = {
            "timestamp": None,
            "level": None,
            "message": None,
        }
    
    def format(self, record):
        # Fast path for performance-critical logs
        log_data = self._base_record.copy()
        log_data["timestamp"] = self.formatTime(record)
        log_data["level"] = record.levelname
        log_data["message"] = record.getMessage()
        
        # Add extra fields only if enabled and present
        if self.include_extra and hasattr(record, 'extra'):
            log_data["extra"] = record.extra
        
        # Request ID from context if available
        if hasattr(_request_context, 'request_id'):
            log_data["request_id"] = _request_context.request_id
        
        return json.dumps(log_data, separators=(',', ':'), ensure_ascii=False)

class ConditionalLogger:
    """Logger wrapper that conditionally logs based on performance settings"""
    
    def __init__(self, logger: logging.Logger, debug_mode: bool = False):
        self.logger = logger
        self.debug_mode = debug_mode
        self._log_payload_threshold = int(os.getenv("LOG_PAYLOAD_THRESHOLD", "1000"))
        self._enable_request_body_logging = os.getenv("ENABLE_REQUEST_BODY_LOGGING", "false").lower() == "true"
        self._enable_response_body_logging = os.getenv("ENABLE_RESPONSE_BODY_LOGGING", "false").lower() == "true"
    
    def debug_conditional(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug messages only if debug mode is enabled"""
        if self.debug_mode:
            self.logger.debug(message, extra=extra or {})
    
    def request(self, method: str, url: str, payload_size: int = 0, extra: Optional[Dict[str, Any]] = None):
        """Log request with conditional payload logging"""
        log_extra = {
            "method": method,
            "url": url,
            "payload_size": payload_size,
            **(extra or {})
        }
        
        # Only log large payloads in debug mode
        if payload_size > self._log_payload_threshold and not self.debug_mode:
            log_extra.pop("payload", None)
        
        self.logger.info(f"Request {method} {url}", extra=log_extra)
    
    def response(self, status_code: int, duration_ms: float, extra: Optional[Dict[str, Any]] = None):
        """Log response with performance metrics"""
        log_extra = {
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            **(extra or {})
        }
        
        # Choose log level based on response time and status
        if duration_ms > 5000:  # > 5 seconds
            self.logger.warning("Slow response", extra=log_extra)
        elif status_code >= 400:
            self.logger.error("Error response", extra=log_extra)
        else:
            self.logger.info("Response", extra=log_extra)
    
    def performance(self, operation: str, duration: float, extra: Optional[Dict[str, Any]] = None):
        """Log performance metrics"""
        log_extra = {
            "operation": operation,
            "duration": round(duration, 4),
            **(extra or {})
        }
        self.logger.log(PERF_LEVEL, f"Performance: {operation}", extra=log_extra)
    
    def error_minimal(self, message: str, error_type: str, extra: Optional[Dict[str, Any]] = None):
        """Log errors with minimal overhead"""
        log_extra = {
            "error_type": error_type,
            **(extra or {})
        }
        self.logger.error(message, extra=log_extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Standard error logging method for compatibility"""
        self.logger.error(message, extra=extra or {})
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Standard info logging method for compatibility"""
        self.logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Standard warning logging method for compatibility"""
        self.logger.warning(message, extra=extra or {})
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Standard debug logging method for compatibility"""
        if self.debug_mode:
            self.logger.debug(message, extra=extra or {})

class PerformanceTimer:
    """Context manager for measuring operation performance"""
    
    def __init__(self, logger: ConditionalLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
        self.extra_data = {}
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            if exc_type:
                self.extra_data["error"] = True
                self.extra_data["error_type"] = exc_type.__name__
            self.logger.performance(self.operation, duration, self.extra_data)
    
    def add_extra(self, key: str, value: Any):
        """Add extra data to be logged"""
        self.extra_data[key] = value

def setup_optimized_logging(debug_mode: bool = False) -> Dict[str, ConditionalLogger]:
    """Setup optimized logging system"""
    
    # Configure log levels based on debug mode
    if debug_mode:
        log_level = logging.DEBUG
        include_extra = True
    else:
        log_level = logging.INFO
        include_extra = False
    
    # Create formatters
    formatter = PerformanceOptimizedFormatter(include_extra=include_extra)
    
    # Create handlers with different configurations
    handlers = {}
    
    # Main application logger
    main_handler = logging.StreamHandler()
    main_handler.setFormatter(formatter)
    main_logger = logging.getLogger("anthropic_proxy.main")
    main_logger.setLevel(log_level)
    main_logger.addHandler(main_handler)
    
    # Performance logger (always enabled for key metrics)
    perf_handler = logging.FileHandler("logs/performance.json")
    perf_handler.setFormatter(formatter)
    perf_logger = logging.getLogger("anthropic_proxy.performance")
    perf_logger.setLevel(PERF_LEVEL)
    perf_logger.addHandler(perf_handler)
    
    # Request logger (conditional based on debug mode)
    if debug_mode:
        request_handler = logging.FileHandler("logs/requests.json")
        request_handler.setFormatter(formatter)
        request_logger = logging.getLogger("anthropic_proxy.requests")
        request_logger.setLevel(logging.DEBUG)
        request_logger.addHandler(request_handler)
    else:
        request_logger = logging.getLogger("anthropic_proxy.requests")
        request_logger.setLevel(logging.CRITICAL)  # Effectively disabled
    
    # Error logger (always enabled)
    error_handler = logging.FileHandler("logs/errors.json")
    error_handler.setFormatter(formatter)
    error_logger = logging.getLogger("anthropic_proxy.errors")
    error_logger.setLevel(logging.ERROR)
    error_logger.addHandler(error_handler)
    
    return {
        "main": ConditionalLogger(main_logger, debug_mode),
        "performance": ConditionalLogger(perf_logger, debug_mode),
        "requests": ConditionalLogger(request_logger, debug_mode),
        "errors": ConditionalLogger(error_logger, debug_mode)
    }

@contextmanager
def request_logging_context(request_id: str):
    """Context manager for request-scoped logging"""
    _request_context.request_id = request_id
    try:
        yield
    finally:
        if hasattr(_request_context, 'request_id'):
            delattr(_request_context, 'request_id')

def get_performance_timer(logger: ConditionalLogger, operation: str) -> PerformanceTimer:
    """Create a performance timer for an operation"""
    return PerformanceTimer(logger, operation)

# Optimized payload serialization
def serialize_payload_safe(payload: Any, max_size: int = 1000) -> str:
    """Safely serialize payload with size limits"""
    try:
        serialized = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        if len(serialized) > max_size:
            return f"<payload truncated, size={len(serialized)}>"
        return serialized
    except (TypeError, ValueError):
        return f"<non-serializable payload, type={type(payload).__name__}>"

# Fast string trimming for logs
def trim_for_logging(text: str, max_length: int = 200) -> str:
    """Fast string trimming for logging"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."