"""
Statistics Integration Module for Anthropic Proxy

Integrates the proxy server with the CLI statistics collection system
to provide real-time usage monitoring and analytics.
"""

import asyncio
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Import CLI stats collector
import sys
sys.path.append(str(Path(__file__).parent.parent))
from cli.stats import StatsCollector
from cli.config import Config

class ProxyStatsIntegration:
    """Integrates proxy server with CLI statistics system"""
    
    def __init__(self):
        self.config = Config()
        self.stats_collector = StatsCollector(self.config)
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the stats integration"""
        if self._initialized:
            return
            
        try:
            await self.stats_collector.initialize()
            self._initialized = True
            print("[STATS] Statistics integration initialized successfully")
        except Exception as e:
            print(f"[STATS] Failed to initialize statistics integration: {e}")
            # Continue without stats rather than breaking the proxy
    
    async def record_request(self, 
                           method: str,
                           endpoint: str,
                           status_code: int,
                           response_time: float,
                           tokens_used: int = 0,
                           model: str = "",
                           success: bool = True,
                           error_message: Optional[str] = None):
        """Record a request in the statistics system"""
        if not self._initialized:
            return
        
        try:
            await self.stats_collector.record_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                response_time=response_time,
                tokens_used=tokens_used,
                model=model,
                success=success,
                error_message=error_message
            )
        except Exception as e:
            # Don't let stats errors break the proxy
            print(f"[STATS] Failed to record request: {e}")
    
    async def get_current_stats(self) -> Dict[str, Any]:
        """Get current statistics for health checks"""
        if not self._initialized:
            return self._get_empty_stats()
        
        try:
            return await self.stats_collector.get_current_stats()
        except Exception as e:
            print(f"[STATS] Failed to get current stats: {e}")
            return self._get_empty_stats()
    
    def _get_empty_stats(self) -> Dict[str, Any]:
        """Get empty statistics structure"""
        return {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'avg_response_time': 0.0,
            'requests_per_minute': 0.0,
            'success_rate': 0.0,
            'uptime': 0.0,
            'active_connections': 0
        }

# Global stats integration instance
stats_integration = ProxyStatsIntegration()

async def initialize_stats():
    """Initialize the global stats integration"""
    await stats_integration.initialize()

async def record_proxy_request(method: str,
                             endpoint: str,
                             status_code: int,
                             response_time: float,
                             tokens_used: int = 0,
                             model: str = "",
                             success: bool = True,
                             error_message: Optional[str] = None):
    """Record a proxy request - global function for easy import"""
    await stats_integration.record_request(
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        response_time=response_time,
        tokens_used=tokens_used,
        model=model,
        success=success,
        error_message=error_message
    )

async def get_proxy_stats() -> Dict[str, Any]:
    """Get proxy statistics - global function for easy import"""
    return await stats_integration.get_current_stats()

# Stats middleware for FastAPI
class StatsMiddleware:
    """Middleware to automatically collect statistics for all requests"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        # Store original send function
        original_send = send
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Response is starting, record the request
                end_time = time.time()
                response_time = end_time - start_time
                status_code = message.get("status", 500)
                
                # Extract request info
                method = scope.get("method", "unknown")
                path = scope.get("path", "unknown")
                
                # Determine if request was successful
                success = 200 <= status_code < 400
                
                # Extract model from query or headers if available
                model = ""
                query_string = scope.get("query_string", b"").decode()
                if "model=" in query_string:
                    try:
                        model = query_string.split("model=")[1].split("&")[0]
                    except:
                        pass
                
                # Extract tokens from response headers if available
                tokens_used = 0
                headers = dict(message.get("headers", []))
                if "x-prompt-tokens" in headers:
                    try:
                        tokens_used += int(headers["x-prompt-tokens"])
                    except:
                        pass
                if "x-completion-tokens" in headers:
                    try:
                        tokens_used += int(headers["x-completion-tokens"])
                    except:
                        pass
                
                # Record the request asynchronously (fire and forget)
                asyncio.create_task(
                    record_proxy_request(
                        method=method,
                        endpoint=path,
                        status_code=status_code,
                        response_time=response_time,
                        tokens_used=tokens_used,
                        model=model,
                        success=success
                    )
                )
            
            await original_send(message)
        
        await self.app(scope, receive, send_wrapper)