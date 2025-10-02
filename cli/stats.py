"""
Statistics collection and analysis for the Anthropic Proxy CLI

Provides comprehensive usage analytics and performance metrics.
"""

import asyncio
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import aiofiles
import aiofiles.os

from cli.config import Config
from cli.utils import format_duration, format_bytes

@dataclass
class RequestRecord:
    """Individual request record"""
    timestamp: float
    method: str
    endpoint: str
    status_code: int
    response_time: float
    tokens_used: int
    model: str
    success: bool
    error_message: Optional[str] = None

@dataclass
class AggregatedStats:
    """Aggregated statistics for a time period"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    requests_per_minute: float
    success_rate: float
    uptime: float
    active_connections: int

class StatsCollector:
    """Statistics collection and analysis system"""
    
    def __init__(self, config: Config):
        self.config = config
        self.stats_file = "stats.json"
        self.current_stats_file = "current_stats.json"
        
        # In-memory storage for recent requests
        self.recent_requests = deque(maxlen=1000)
        self.start_time = time.time()
        
        # Performance metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._total_tokens = 0
        self._active_connections = 0
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the stats collector"""
        try:
            # Load existing stats if available
            await self._load_stats()
        except Exception as e:
            print(f"Warning: Could not load existing stats: {e}")
    
    async def record_request(self, 
                           method: str,
                           endpoint: str,
                           status_code: int,
                           response_time: float,
                           tokens_used: int = 0,
                           model: str = "",
                           success: bool = True,
                           error_message: Optional[str] = None):
        """Record a request in the statistics"""
        
        async with self._lock:
            # Create request record
            record = RequestRecord(
                timestamp=time.time(),
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                response_time=response_time,
                tokens_used=tokens_used,
                model=model,
                success=success,
                error_message=error_message
            )
            
            # Add to recent requests
            self.recent_requests.append(record)
            
            # Update counters
            self._total_requests += 1
            self._total_tokens += tokens_used
            
            if success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1
            
            # Save stats periodically
            if self._total_requests % 10 == 0:
                await self._save_stats()
    
    async def get_current_stats(self) -> Dict[str, Any]:
        """Get current real-time statistics"""
        
        async with self._lock:
            now = time.time()
            uptime = now - self.start_time
            
            # Calculate requests per minute
            requests_last_minute = sum(
                1 for req in self.recent_requests 
                if now - req.timestamp <= 60
            )
            
            # Calculate response time statistics
            response_times = [
                req.response_time for req in self.recent_requests
                if req.response_time > 0
            ]
            
            if response_times:
                avg_response_time = statistics.mean(response_times)
                min_response_time = min(response_times)
                max_response_time = max(response_times)
                p95_response_time = self._calculate_percentile(response_times, 95)
            else:
                avg_response_time = 0.0
                min_response_time = 0.0
                max_response_time = 0.0
                p95_response_time = 0.0
            
            # Calculate success rate
            success_rate = (
                (self._successful_requests / self._total_requests * 100)
                if self._total_requests > 0 else 0.0
            )
            
            return {
                'total_requests': self._total_requests,
                'successful_requests': self._successful_requests,
                'failed_requests': self._failed_requests,
                'total_tokens': self._total_tokens,
                'avg_response_time': avg_response_time,
                'min_response_time': min_response_time,
                'max_response_time': max_response_time,
                'p95_response_time': p95_response_time,
                'requests_per_minute': requests_last_minute,
                'success_rate': success_rate,
                'uptime': uptime,
                'active_connections': self._active_connections,
                'timestamp': now
            }
    
    async def get_detailed_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get detailed statistics for the specified time period"""
        
        cutoff_time = time.time() - (hours * 3600)
        
        # Filter requests within the time period
        period_requests = [
            req for req in self.recent_requests
            if req.timestamp >= cutoff_time
        ]
        
        if not period_requests:
            return self._get_empty_stats()
        
        # Calculate statistics
        total_requests = len(period_requests)
        successful_requests = sum(1 for req in period_requests if req.success)
        failed_requests = total_requests - successful_requests
        total_tokens = sum(req.tokens_used for req in period_requests)
        
        response_times = [req.response_time for req in period_requests if req.response_time > 0]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = self._calculate_percentile(response_times, 95)
        else:
            avg_response_time = 0.0
            min_response_time = 0.0
            max_response_time = 0.0
            p95_response_time = 0.0
        
        # Calculate requests per minute
        if period_requests:
            time_span = period_requests[-1].timestamp - period_requests[0].timestamp
            requests_per_minute = (total_requests / time_span * 60) if time_span > 0 else 0.0
        else:
            requests_per_minute = 0.0
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0.0
        
        # Calculate uptime (simplified - assumes proxy was running the entire period)
        uptime = hours * 3600
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'total_tokens': total_tokens,
            'avg_response_time': avg_response_time,
            'min_response_time': min_response_time,
            'max_response_time': max_response_time,
            'p95_response_time': p95_response_time,
            'requests_per_minute': requests_per_minute,
            'success_rate': success_rate,
            'uptime': uptime,
            'active_connections': self._active_connections,
            'period_hours': hours
        }
    
    async def get_hourly_stats(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly statistics breakdown"""
        
        now = time.time()
        hourly_stats = []
        
        for hour_offset in range(hours):
            hour_start = now - ((hour_offset + 1) * 3600)
            hour_end = now - (hour_offset * 3600)
            
            # Filter requests for this hour
            hour_requests = [
                req for req in self.recent_requests
                if hour_start <= req.timestamp < hour_end
            ]
            
            if hour_requests:
                total_requests = len(hour_requests)
                successful_requests = sum(1 for req in hour_requests if req.success)
                total_tokens = sum(req.tokens_used for req in hour_requests)
                
                response_times = [req.response_time for req in hour_requests if req.response_time > 0]
                avg_response_time = statistics.mean(response_times) if response_times else 0.0
                
                success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0.0
                
                hourly_stats.append({
                    'hour': datetime.fromtimestamp(hour_start).strftime('%Y-%m-%d %H:00'),
                    'total_requests': total_requests,
                    'successful_requests': successful_requests,
                    'total_tokens': total_tokens,
                    'avg_response_time': avg_response_time,
                    'success_rate': success_rate
                })
            else:
                hourly_stats.append({
                    'hour': datetime.fromtimestamp(hour_start).strftime('%Y-%m-%d %H:00'),
                    'total_requests': 0,
                    'successful_requests': 0,
                    'total_tokens': 0,
                    'avg_response_time': 0.0,
                    'success_rate': 0.0
                })
        
        return list(reversed(hourly_stats))  # Most recent first
    
    async def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics broken down by model"""
        
        model_stats = defaultdict(lambda: {
            'total_requests': 0,
            'successful_requests': 0,
            'total_tokens': 0,
            'response_times': [],
            'avg_response_time': 0.0
        })
        
        for req in self.recent_requests:
            model = req.model or 'unknown'
            stats = model_stats[model]
            
            stats['total_requests'] += 1
            if req.success:
                stats['successful_requests'] += 1
            stats['total_tokens'] += req.tokens_used
            
            if req.response_time > 0:
                stats['response_times'].append(req.response_time)
        
        # Calculate averages and success rates
        result = {}
        for model, stats in model_stats.items():
            response_times = stats['response_times']
            avg_response_time = statistics.mean(response_times) if response_times else 0.0
            success_rate = (
                (stats['successful_requests'] / stats['total_requests'] * 100)
                if stats['total_requests'] > 0 else 0.0
            )
            
            result[model] = {
                'total_requests': stats['total_requests'],
                'successful_requests': stats['successful_requests'],
                'total_tokens': stats['total_tokens'],
                'avg_response_time': avg_response_time,
                'success_rate': success_rate
            }
        
        return result
    
    async def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics and breakdown"""
        
        error_counts = defaultdict(int)
        recent_errors = []
        
        for req in self.recent_requests:
            if not req.success:
                error_type = req.error_message or 'Unknown error'
                error_counts[error_type] += 1
                
                # Keep recent errors for display
                if len(recent_errors) < 10:
                    recent_errors.append({
                        'timestamp': req.timestamp,
                        'endpoint': req.endpoint,
                        'status_code': req.status_code,
                        'error': error_type
                    })
        
        # Sort errors by frequency
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_errors': sum(error_counts.values()),
            'error_breakdown': dict(sorted_errors[:10]),  # Top 10 errors
            'recent_errors': recent_errors
        }
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value from a list of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def _get_empty_stats(self) -> Dict[str, Any]:
        """Get empty statistics structure"""
        return {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'avg_response_time': 0.0,
            'min_response_time': 0.0,
            'max_response_time': 0.0,
            'p95_response_time': 0.0,
            'requests_per_minute': 0.0,
            'success_rate': 0.0,
            'uptime': 0.0,
            'active_connections': 0
        }
    
    async def _load_stats(self):
        """Load existing statistics from file"""
        try:
            async with aiofiles.open(self.stats_file, 'r') as f:
                data = await f.read()
                stats_data = json.loads(data)
                
                # Load counters
                self._total_requests = stats_data.get('total_requests', 0)
                self._successful_requests = stats_data.get('successful_requests', 0)
                self._failed_requests = stats_data.get('failed_requests', 0)
                self._total_tokens = stats_data.get('total_tokens', 0)
                
                # Load start time
                self.start_time = stats_data.get('start_time', time.time())
                
        except FileNotFoundError:
            # No existing stats file, start fresh
            self.start_time = time.time()
        except Exception as e:
            print(f"Warning: Error loading stats file: {e}")
            self.start_time = time.time()
    
    async def _save_stats(self):
        """Save current statistics to file"""
        try:
            stats_data = {
                'total_requests': self._total_requests,
                'successful_requests': self._successful_requests,
                'failed_requests': self._failed_requests,
                'total_tokens': self._total_tokens,
                'start_time': self.start_time,
                'last_updated': time.time()
            }
            
            async with aiofiles.open(self.stats_file, 'w') as f:
                await f.write(json.dumps(stats_data, indent=2))
                
        except Exception as e:
            print(f"Warning: Error saving stats file: {e}")
    
    async def reset_stats(self):
        """Reset all statistics"""
        async with self._lock:
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._total_tokens = 0
            self.start_time = time.time()
            self.recent_requests.clear()
            
            # Delete stats file
            try:
                await aiofiles.os.remove(self.stats_file)
            except FileNotFoundError:
                pass
    
    async def export_stats(self, filename: str, format: str = 'json'):
        """Export statistics to file"""
        
        stats = await self.get_detailed_stats(24 * 7)  # Last week
        hourly_stats = await self.get_hourly_stats(24 * 7)
        model_stats = await self.get_model_stats()
        error_stats = await self.get_error_stats()
        
        export_data = {
            'summary': stats,
            'hourly_breakdown': hourly_stats,
            'model_breakdown': model_stats,
            'error_analysis': error_stats,
            'export_timestamp': datetime.now().isoformat(),
            'export_format': format
        }
        
        if format.lower() == 'json':
            async with aiofiles.open(filename, 'w') as f:
                await f.write(json.dumps(export_data, indent=2))
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def increment_active_connections(self):
        """Increment active connections counter"""
        self._active_connections += 1
    
    def decrement_active_connections(self):
        """Decrement active connections counter"""
        if self._active_connections > 0:
            self._active_connections -= 1