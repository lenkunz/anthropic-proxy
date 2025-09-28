"""
Logging configuration for anthropic-proxy.
Provides structured logging with proper levels, request tracking, and file organization.
"""

import os
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

class RequestIDFilter(logging.Filter):
    """Add request ID to log records if available in context."""
    
    def __init__(self):
        super().__init__()
        self._request_id = None
    
    def set_request_id(self, request_id: str):
        """Set the current request ID."""
        self._request_id = request_id
    
    def filter(self, record):
        """Add request_id to the log record."""
        record.request_id = self._request_id or "no-req-id"
        return True

# Global request ID filter instance
request_id_filter = RequestIDFilter()

def setup_logging(debug_mode: bool = False) -> Dict[str, logging.Logger]:
    """
    Set up structured logging with multiple loggers for different purposes.
    
    Args:
        debug_mode: If True, enable debug level logging
        
    Returns:
        Dictionary of configured loggers
    """
    # Base log level
    log_level = logging.DEBUG if debug_mode else logging.INFO
    
    # Formatter for structured logs
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)s | %(levelname)s | %(request_id)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Simple formatter for access logs
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(request_id)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # JSON formatter for structured data
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'logger': record.name,
                'level': record.levelname,
                'request_id': getattr(record, 'request_id', 'no-req-id'),
                'message': record.getMessage()
            }
            
            # Add extra fields if they exist
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 
                              'exc_text', 'stack_info', 'request_id']:
                    if not key.startswith('_'):
                        log_data[key] = value
            
            return json.dumps(log_data, indent=None, separators=(',', ':'))
    
    json_formatter = JSONFormatter()
    
    loggers = {}
    
    # 1. Main application logger
    main_logger = logging.getLogger('anthropic-proxy')
    main_logger.setLevel(log_level)
    main_logger.addFilter(request_id_filter)
    
    # Main log file with rotation
    main_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'application.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setFormatter(detailed_formatter)
    main_handler.setLevel(log_level)
    main_logger.addHandler(main_handler)
    
    # Console output for main logger
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(detailed_formatter)
    console_handler.setLevel(logging.INFO)  # Less verbose on console
    main_logger.addHandler(console_handler)
    
    loggers['main'] = main_logger
    
    # 2. Access logger for HTTP requests
    access_logger = logging.getLogger('access')
    access_logger.setLevel(logging.INFO)
    access_logger.addFilter(request_id_filter)
    
    access_handler = logging.handlers.TimedRotatingFileHandler(
        LOGS_DIR / 'access.log',
        when='midnight',
        interval=1,
        backupCount=30
    )
    access_handler.setFormatter(simple_formatter)
    access_logger.addHandler(access_handler)
    loggers['access'] = access_logger
    
    # 3. Error logger for exceptions and errors
    error_logger = logging.getLogger('errors')
    error_logger.setLevel(logging.ERROR)
    error_logger.addFilter(request_id_filter)
    
    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / 'errors.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10
    )
    error_handler.setFormatter(detailed_formatter)
    error_logger.addHandler(error_handler)
    loggers['error'] = error_logger
    
    # 4. Debug logger for detailed debugging (only when debug mode is on)
    debug_logger = logging.getLogger('debug')
    debug_logger.setLevel(logging.DEBUG if debug_mode else logging.CRITICAL)
    debug_logger.addFilter(request_id_filter)
    
    if debug_mode:
        debug_handler = logging.handlers.TimedRotatingFileHandler(
            LOGS_DIR / 'debug.log',
            when='midnight',
            interval=1,
            backupCount=7  # Keep only 1 week of debug logs
        )
        debug_handler.setFormatter(detailed_formatter)
        debug_logger.addHandler(debug_handler)
    loggers['debug'] = debug_logger
    
    # 5. Request/Response logger for API interactions
    api_logger = logging.getLogger('api')
    api_logger.setLevel(logging.INFO)
    api_logger.addFilter(request_id_filter)
    
    api_handler = logging.handlers.TimedRotatingFileHandler(
        LOGS_DIR / 'api_requests.json',
        when='midnight',
        interval=1,
        backupCount=14
    )
    api_handler.setFormatter(json_formatter)
    api_logger.addHandler(api_handler)
    loggers['api'] = api_logger
    
    # 6. Performance logger for timing metrics
    perf_logger = logging.getLogger('performance')
    perf_logger.setLevel(logging.INFO)
    perf_logger.addFilter(request_id_filter)
    
    perf_handler = logging.handlers.TimedRotatingFileHandler(
        LOGS_DIR / 'performance.json',
        when='midnight',
        interval=1,
        backupCount=30
    )
    perf_handler.setFormatter(json_formatter)
    perf_logger.addHandler(perf_handler)
    loggers['performance'] = perf_logger
    
    # Disable propagation to avoid duplicate logs
    for logger in loggers.values():
        logger.propagate = False
    
    return loggers

def log_request(logger: logging.Logger, method: str, url: str, 
                status_code: Optional[int] = None, duration_ms: Optional[float] = None,
                model: Optional[str] = None, has_images: Optional[bool] = None,
                message_count: Optional[int] = None, **extra_data):
    """Log an HTTP request with structured data."""
    data = {
        'method': method,
        'url': url,
        'status_code': status_code,
        'duration_ms': duration_ms,
        'model': model,
        'has_images': has_images,
        'message_count': message_count
    }
    
    # Add any extra fields
    data.update(extra_data)
    
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}
    
    # Add data as extra fields to the log record
    logger.info(f"{method} {url}", extra=data)

def log_error(logger: logging.Logger, error: Exception, context: Dict[str, Any] = None):
    """Log an error with context and stack trace."""
    import traceback
    
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc()
    }
    
    if context:
        error_data.update(context)
    
    logger.error(f"Error: {error}", extra=error_data)

def get_request_id() -> str:
    """Generate a unique request ID."""
    import uuid
    return str(uuid.uuid4())[:8]

def set_request_context(request_id: str):
    """Set the current request context for logging."""
    request_id_filter.set_request_id(request_id)

def clear_request_context():
    """Clear the current request context."""
    request_id_filter.set_request_id(None)