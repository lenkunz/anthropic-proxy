#!/usr/bin/env python3
"""
Log rotation and compression system for anthropic-proxy.
Provides automatic log rotation based on size and time, with gzip compression.
"""

import os
import gzip
import shutil
import asyncio
import time
import glob
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import logging
import json

class LogRotationConfig:
    """Configuration for log rotation and compression"""
    
    def __init__(self):
        # Rotation settings
        self.max_file_size_mb = int(os.getenv("UPSTREAM_LOG_MAX_SIZE_MB", "50"))
        self.backup_count = int(os.getenv("UPSTREAM_LOG_BACKUP_COUNT", "10"))
        self.rotation_enabled = os.getenv("UPSTREAM_LOG_ROTATION", "true").lower() == "true"
        
        # Compression settings
        self.compression_enabled = os.getenv("UPSTREAM_LOG_COMPRESSION", "true").lower() == "true"
        self.compress_immediately = os.getenv("UPSTREAM_LOG_COMPRESS_IMMEDIATELY", "true").lower() == "true"
        
        # Cleanup settings
        self.retention_days = int(os.getenv("UPSTREAM_LOG_RETENTION_DAYS", "30"))
        self.cleanup_interval_hours = int(os.getenv("LOG_CLEANUP_INTERVAL_HOURS", "24"))
        
        # Log directories
        self.log_dir = Path(os.getenv("UPSTREAM_LOG_DIR", "./logs"))
        self.upstream_log_dir = self.log_dir / "upstream"
        
        # Specific log files to manage
        self.managed_log_files = [
            "upstream_requests.json",
            "upstream_responses.json", 
            "performance_metrics.json",
            "error_logs.json"
        ]
        
        # Logging for the rotation system itself
        self.enable_rotation_logging = os.getenv("LOG_ROTATION_LOGGING", "true").lower() == "true"
        
    def get_max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024
    
    def should_rotate_file(self, file_path: Path) -> bool:
        """Check if a file should be rotated based on size"""
        if not self.rotation_enabled or not file_path.exists():
            return False
        return file_path.stat().st_size >= self.get_max_file_size_bytes()

class LogRotator:
    """Handles log rotation and compression for upstream logs"""
    
    def __init__(self, config: Optional[LogRotationConfig] = None):
        self.config = config or LogRotationConfig()
        self.logger = self._setup_logger()
        self._rotation_lock = asyncio.Lock()
        
        # Ensure log directories exist
        self.config.log_dir.mkdir(exist_ok=True)
        self.config.upstream_log_dir.mkdir(exist_ok=True)
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for the rotation system"""
        logger = logging.getLogger("log_rotator")
        if not self.config.enable_rotation_logging:
            logger.setLevel(logging.CRITICAL + 1)  # Disable all logging
            return logger
            
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
        return logger
    
    async def rotate_file(self, file_path: Path) -> bool:
        """Rotate a single log file"""
        try:
            async with self._rotation_lock:
                if not file_path.exists():
                    self.logger.warning(f"File not found for rotation: {file_path}")
                    return False
                
                # Create rotated filename with timestamp
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                rotated_name = f"{file_path.stem}.{timestamp}{file_path.suffix}"
                rotated_path = file_path.parent / rotated_name
                
                # Move current file to rotated name
                shutil.move(str(file_path), str(rotated_path))
                self.logger.info(f"Rotated log file: {file_path.name} -> {rotated_name}")
                
                # Compress immediately if enabled
                if self.config.compression_enabled and self.config.compress_immediately:
                    await self._compress_file_async(rotated_path)
                
                # Clean up old backups
                await self._cleanup_old_backups(file_path)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to rotate file {file_path}: {e}")
            return False
    
    async def _compress_file_async(self, file_path: Path) -> bool:
        """Compress a file using gzip asynchronously"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            
            def compress_sync():
                with open(file_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            
            await asyncio.to_thread(compress_sync)
            
            # Remove original file after successful compression
            file_path.unlink()
            
            # Calculate compression ratio
            original_size = file_path.stat().st_size if file_path.exists() else 0
            compressed_size = compressed_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            self.logger.info(f"Compressed {file_path.name} ({original_size:,} bytes -> {compressed_size:,} bytes, {ratio:.1f}% reduction)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to compress file {file_path}: {e}")
            return False
    
    async def _cleanup_old_backups(self, original_file: Path):
        """Clean up old backup files beyond the retention limit"""
        try:
            # Get all backup files for this log file
            pattern = f"{original_file.stem}.*{original_file.suffix}*"
            backup_files = list(original_file.parent.glob(pattern))
            
            # Filter out the current file and sort by modification time
            backup_files = [f for f in backup_files if f != original_file]
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove excess backups beyond backup_count
            if len(backup_files) > self.config.backup_count:
                files_to_remove = backup_files[self.config.backup_count:]
                for old_file in files_to_remove:
                    old_file.unlink()
                    self.logger.info(f"Removed old backup: {old_file.name}")
                    
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups for {original_file}: {e}")
    
    async def cleanup_old_logs(self):
        """Clean up logs older than retention period"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.retention_days)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Check all log files in managed directories
            for log_dir in [self.config.log_dir, self.config.upstream_log_dir]:
                if not log_dir.exists():
                    continue
                    
                for log_file in log_dir.glob("*.json*"):
                    if log_file.stat().st_mtime < cutoff_timestamp:
                        log_file.unlink()
                        self.logger.info(f"Removed old log file: {log_file}")
                        
        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
    
    async def check_and_rotate_all_logs(self):
        """Check all managed log files and rotate if necessary"""
        if not self.config.rotation_enabled:
            return
            
        for log_name in self.config.managed_log_files:
            log_path = self.config.log_dir / log_name
            if self.config.should_rotate_file(log_path):
                await self.rotate_file(log_path)
    
    async def start_rotation_monitor(self, check_interval_seconds: int = 300):
        """Start background task to monitor and rotate logs"""
        self.logger.info("Starting log rotation monitor")
        
        while True:
            try:
                await asyncio.sleep(check_interval_seconds)
                await self.check_and_rotate_all_logs()
                
                # Run cleanup less frequently
                if int(time.time()) % (self.config.cleanup_interval_hours * 3600 // check_interval_seconds) == 0:
                    await self.cleanup_old_logs()
                    
            except Exception as e:
                self.logger.error(f"Error in rotation monitor: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def get_log_statistics(self) -> Dict[str, Any]:
        """Get statistics about log files"""
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "files": []
        }
        
        for log_dir in [self.config.log_dir, self.config.upstream_log_dir]:
            if not log_dir.exists():
                continue
                
            for log_file in log_dir.glob("*.json*"):
                file_stat = log_file.stat()
                file_info = {
                    "name": log_file.name,
                    "path": str(log_file),
                    "size_bytes": file_stat.st_size,
                    "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(file_stat.st_mtime, timezone.utc).isoformat(),
                    "is_compressed": log_file.suffix == '.gz'
                }
                
                stats["files"].append(file_info)
                stats["total_files"] += 1
                stats["total_size_bytes"] += file_stat.st_size
        
        stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)
        return stats

class RotatingLogBatcher:
    """Enhanced log batcher with rotation support"""
    
    def __init__(self, log_file: str, rotator: LogRotator, batch_size: int = 50, batch_timeout: float = 0.1):
        self.log_file = Path(log_file)
        self.rotator = rotator
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch: List[Dict[str, Any]] = []
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
                    print(f"[ROTATING_BATCHER_ERROR] Background flush timer error: {e}")
                    
        # Only start timer if not already running
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(flush_timer())
    
    async def add_entry(self, entry: Dict[str, Any]):
        """Add entry to batch with rotation check"""
        async with self.lock:
            # Check if rotation is needed before adding
            if self.rotator.config.should_rotate_file(self.log_file):
                await self._flush_batch()  # Flush current batch
                await self.rotator.rotate_file(self.log_file)
            
            self.batch.append(entry)
            
            # Flush if batch is full
            if len(self.batch) >= self.batch_size:
                await self._flush_batch()
    
    async def _flush_batch(self):
        """Flush current batch to file"""
        if not self.batch:
            return
            
        # Move current batch to local variable for processing
        current_batch = self.batch.copy()
        self.batch.clear()
        self.last_flush = time.time()
        
        # Process batch in background
        asyncio.create_task(self._write_batch_async(current_batch))
    
    async def _write_batch_async(self, batch: List[Dict[str, Any]]):
        """Write batch to file asynchronously"""
        try:
            def write_to_file():
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    for entry in batch:
                        # Handle both dict entries and PerformantLogEntry objects
                        if hasattr(entry, 'data'):
                            # It's a PerformantLogEntry object
                            log_data = {
                                "timestamp": getattr(entry, 'timestamp', time.time()),
                                "type": getattr(entry, 'type', 'unknown'),
                                "req_id": getattr(entry, 'req_id', 'unknown'),
                                **getattr(entry, 'data', {})
                            }
                        else:
                            # It's already a dict
                            log_data = entry
                        
                        f.write(json.dumps(log_data, separators=(',', ':'), ensure_ascii=False) + '\n')
            
            await asyncio.to_thread(write_to_file)
                    
        except Exception as e:
            print(f"[ROTATING_BATCHER_ERROR] Failed to write batch: {e}")
    
    async def force_flush(self):
        """Force flush current batch"""
        async with self.lock:
            await self._flush_batch()

# Global instance for easy access
_log_rotator: Optional[LogRotator] = None

def get_log_rotator() -> LogRotator:
    """Get global log rotator instance"""
    global _log_rotator
    if _log_rotator is None:
        _log_rotator = LogRotator()
    return _log_rotator

async def start_log_rotation_monitor():
    """Start the global log rotation monitor"""
    rotator = get_log_rotator()
    await rotator.start_rotation_monitor()