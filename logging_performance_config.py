#!/usr/bin/env python3
"""
Performance logging configuration for anthropic-proxy.
Allows fine-tuning of logging performance vs. detail trade-offs.
"""

import os
from typing import Dict, Any

class LoggingConfig:
    """Centralized logging configuration for performance tuning"""
    
    # Performance levels (higher = more performance, less detail)
    PERFORMANCE_LEVELS = {
        "max_detail": 0,     # Log everything with full detail
        "balanced": 1,       # Good balance of performance and detail  
        "performance": 2,    # Prioritize performance over detail
        "minimal": 3         # Only critical logs, maximum performance
    }
    
    def __init__(self):
        # Get performance level from environment
        perf_level_name = os.getenv("LOGGING_PERFORMANCE_LEVEL", "balanced").lower()
        self.performance_level = self.PERFORMANCE_LEVELS.get(perf_level_name, 1)
        
        # Core settings based on performance level
        self.batch_size = self._get_batch_size()
        self.batch_timeout = self._get_batch_timeout()
        self.max_queue_size = self._get_max_queue_size()
        
        # Feature toggles based on performance level
        self.log_request_headers = self.performance_level <= 1
        self.log_response_headers = self.performance_level <= 0
        self.log_response_bodies = self.performance_level <= 2
        self.log_request_payloads = self.performance_level <= 1
        self.log_retry_attempts = self.performance_level <= 2
        
        # String truncation limits (bytes)
        self.max_response_body_log = self._get_response_body_limit()
        self.max_request_payload_log = self._get_request_payload_limit()
        
        # Performance optimizations
        self.use_async_file_io = True
        self.compress_old_logs = self.performance_level >= 2
        self.skip_json_parsing_for_large_responses = self.performance_level >= 2
        self.large_response_threshold = 10000  # bytes
        
    def _get_batch_size(self) -> int:
        """Get batch size based on performance level"""
        batch_sizes = {0: 10, 1: 50, 2: 100, 3: 200}
        return batch_sizes.get(self.performance_level, 50)
    
    def _get_batch_timeout(self) -> float:
        """Get batch timeout based on performance level"""
        timeouts = {0: 1.0, 1: 5.0, 2: 10.0, 3: 30.0}
        return timeouts.get(self.performance_level, 5.0)
    
    def _get_max_queue_size(self) -> int:
        """Get max queue size based on performance level"""
        queue_sizes = {0: 500, 1: 1000, 2: 2000, 3: 5000}
        return queue_sizes.get(self.performance_level, 1000)
    
    def _get_response_body_limit(self) -> int:
        """Get response body logging limit"""
        limits = {0: 5000, 1: 2000, 2: 1000, 3: 500}
        return limits.get(self.performance_level, 2000)
    
    def _get_request_payload_limit(self) -> int:
        """Get request payload logging limit"""
        limits = {0: 2000, 1: 1000, 2: 500, 3: 200}
        return limits.get(self.performance_level, 1000)
    
    def should_log_detailed_upstream(self, response_time: float, status_code: int) -> bool:
        """Determine if we should log detailed upstream info based on performance level and response characteristics"""
        # Always log errors regardless of performance level
        if status_code >= 400:
            return True
            
        # Always log slow responses
        if response_time > 2.0:
            return True
            
        # For normal responses, check performance level
        if self.performance_level <= 1:  # balanced or max_detail
            return True
        elif self.performance_level == 2:  # performance
            return response_time > 1.0  # Only log if slower than 1s
        else:  # minimal
            return False
    
    def get_log_level_for_response(self, response_time: float, status_code: int) -> int:
        """Get appropriate log level for a response"""
        from async_logging import LogLevel
        
        if status_code >= 400:
            return LogLevel.CRITICAL
        elif response_time > 5.0:
            return LogLevel.CRITICAL  # Very slow responses are critical
        elif response_time > 2.0:
            return LogLevel.IMPORTANT
        elif self.performance_level <= 1:
            return LogLevel.IMPORTANT
        else:
            return LogLevel.DEBUG

# Global configuration instance
logging_config = LoggingConfig()

# Environment variables for easy configuration
"""
Set these environment variables to control logging performance:

LOGGING_PERFORMANCE_LEVEL:
  - max_detail: Log everything with full detail (development)
  - balanced: Good balance of performance and detail (default)
  - performance: Prioritize performance over detail (production)
  - minimal: Only critical logs, maximum performance (high-load production)

Example usage:
export LOGGING_PERFORMANCE_LEVEL=performance
docker compose up -d
"""