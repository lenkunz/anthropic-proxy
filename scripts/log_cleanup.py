#!/usr/bin/env python3
"""
Log cleanup script for anthropic-proxy.
Manages old log files, disk space usage, and provides log statistics.
"""

import os
import sys
import argparse
import json
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
import asyncio

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from log_rotation import LogRotator, LogRotationConfig

class LogCleanupManager:
    """Manages log cleanup and maintenance tasks"""
    
    def __init__(self, config: Optional[LogRotationConfig] = None):
        self.config = config or LogRotationConfig()
        self.rotator = LogRotator(self.config)
        
    async def cleanup_old_logs(self, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up logs older than retention period"""
        stats = {
            "deleted_files": [],
            "total_freed_bytes": 0,
            "total_freed_mb": 0,
            "errors": []
        }
        
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.retention_days)
            cutoff_timestamp = cutoff_time.timestamp()
            
            # Check all log files in managed directories
            for log_dir in [self.config.log_dir, self.config.upstream_log_dir]:
                if not log_dir.exists():
                    continue
                    
                for log_file in log_dir.glob("*.json*"):
                    try:
                        file_stat = log_file.stat()
                        if file_stat.st_mtime < cutoff_timestamp:
                            file_size = file_stat.st_size
                            
                            if not dry_run:
                                log_file.unlink()
                            
                            stats["deleted_files"].append({
                                "name": log_file.name,
                                "path": str(log_file),
                                "size_bytes": file_size,
                                "size_mb": round(file_size / (1024 * 1024), 2),
                                "modified": datetime.fromtimestamp(file_stat.st_mtime, timezone.utc).isoformat()
                            })
                            stats["total_freed_bytes"] += file_size
                            
                    except Exception as e:
                        stats["errors"].append(f"Error processing {log_file}: {e}")
            
            stats["total_freed_mb"] = round(stats["total_freed_bytes"] / (1024 * 1024), 2)
            
        except Exception as e:
            stats["errors"].append(f"Cleanup failed: {e}")
            
        return stats
    
    async def compress_logs(self, dry_run: bool = False) -> Dict[str, Any]:
        """Compress uncompressed log files"""
        stats = {
            "compressed_files": [],
            "total_saved_bytes": 0,
            "total_saved_mb": 0,
            "errors": []
        }
        
        if not self.config.compression_enabled:
            stats["errors"].append("Compression is disabled in configuration")
            return stats
        
        try:
            # Find uncompressed log files
            for log_dir in [self.config.log_dir, self.config.upstream_log_dir]:
                if not log_dir.exists():
                    continue
                    
                for log_file in log_dir.glob("*.json"):
                    if log_file.suffix == '.gz':  # Skip already compressed files
                        continue
                        
                    try:
                        # Skip if file is too recent (might be actively written)
                        file_age = datetime.now(timezone.utc).timestamp() - log_file.stat().st_mtime
                        if file_age < 3600:  # Less than 1 hour old
                            continue
                            
                        original_size = log_file.stat().st_size
                        compressed_path = log_file.with_suffix(log_file.suffix + '.gz')
                        
                        if not dry_run:
                            # Compress the file
                            def compress_sync():
                                with open(log_file, 'rb') as f_in:
                                    with gzip.open(compressed_path, 'wb') as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                            
                            await asyncio.to_thread(compress_sync)
                            
                            # Remove original file after successful compression
                            log_file.unlink()
                        
                        # Calculate compression ratio
                        if not dry_run and compressed_path.exists():
                            compressed_size = compressed_path.stat().st_size
                        else:
                            # Estimate compression ratio (typically 70-80% reduction)
                            compressed_size = original_size * 0.25
                        
                        saved_bytes = original_size - compressed_size
                        compression_ratio = (saved_bytes / original_size) * 100 if original_size > 0 else 0
                        
                        stats["compressed_files"].append({
                            "name": log_file.name,
                            "original_size_mb": round(original_size / (1024 * 1024), 2),
                            "compressed_size_mb": round(compressed_size / (1024 * 1024), 2),
                            "compression_ratio": round(compression_ratio, 1),
                            "saved_mb": round(saved_bytes / (1024 * 1024), 2)
                        })
                        stats["total_saved_bytes"] += saved_bytes
                        
                    except Exception as e:
                        stats["errors"].append(f"Error compressing {log_file}: {e}")
            
            stats["total_saved_mb"] = round(stats["total_saved_bytes"] / (1024 * 1024), 2)
            
        except Exception as e:
            stats["errors"].append(f"Compression failed: {e}")
            
        return stats
    
    def get_disk_usage_stats(self) -> Dict[str, Any]:
        """Get disk usage statistics for log directories"""
        stats = {
            "log_directory": str(self.config.log_dir),
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "file_count": 0,
            "compressed_files": 0,
            "uncompressed_files": 0,
            "largest_files": [],
            "file_types": {}
        }
        
        try:
            all_files = []
            
            for log_dir in [self.config.log_dir, self.config.upstream_log_dir]:
                if not log_dir.exists():
                    continue
                    
                for log_file in log_dir.glob("*.json*"):
                    file_stat = log_file.stat()
                    file_size = file_stat.st_size
                    
                    all_files.append({
                        "name": log_file.name,
                        "path": str(log_file),
                        "size_bytes": file_size,
                        "size_mb": round(file_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(file_stat.st_mtime, timezone.utc).isoformat(),
                        "is_compressed": log_file.suffix == '.gz'
                    })
                    
                    stats["total_size_bytes"] += file_size
                    stats["file_count"] += 1
                    
                    if log_file.suffix == '.gz':
                        stats["compressed_files"] += 1
                    else:
                        stats["uncompressed_files"] += 1
                    
                    # Track file types
                    ext = log_file.suffix
                    stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
            
            # Sort by size and get top 10 largest files
            all_files.sort(key=lambda x: x["size_bytes"], reverse=True)
            stats["largest_files"] = all_files[:10]
            stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)
            
        except Exception as e:
            stats["error"] = str(e)
            
        return stats

async def main():
    """Main function for CLI usage"""
    parser = argparse.ArgumentParser(description="Log cleanup and maintenance for anthropic-proxy")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without actually deleting")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old logs")
    parser.add_argument("--compress", action="store_true", help="Compress uncompressed logs")
    parser.add_argument("--stats", action="store_true", help="Show disk usage statistics")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
    args = parser.parse_args()
    
    if not any([args.cleanup, args.compress, args.stats]):
        parser.print_help()
        return
    
    manager = LogCleanupManager()
    
    if args.stats:
        stats = manager.get_disk_usage_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"Log Directory Statistics:")
            print(f"  Directory: {stats['log_directory']}")
            print(f"  Total files: {stats['file_count']}")
            print(f"  Total size: {stats['total_size_mb']} MB")
            print(f"  Compressed files: {stats['compressed_files']}")
            print(f"  Uncompressed files: {stats['uncompressed_files']}")
            print(f"  File types: {stats['file_types']}")
            
            if stats['largest_files']:
                print(f"\n  Largest files:")
                for file_info in stats['largest_files'][:5]:
                    print(f"    {file_info['name']}: {file_info['size_mb']} MB")
    
    if args.cleanup:
        print("Cleaning up old logs...")
        cleanup_stats = await manager.cleanup_old_logs(args.dry_run)
        
        if args.json:
            print(json.dumps(cleanup_stats, indent=2))
        else:
            if cleanup_stats['deleted_files']:
                print(f"  Deleted {len(cleanup_stats['deleted_files'])} files")
                print(f"  Freed {cleanup_stats['total_freed_mb']} MB")
            else:
                print("  No files to delete")
                
            if cleanup_stats['errors']:
                print(f"  Errors: {cleanup_stats['errors']}")
    
    if args.compress:
        print("Compressing logs...")
        compress_stats = await manager.compress_logs(args.dry_run)
        
        if args.json:
            print(json.dumps(compress_stats, indent=2))
        else:
            if compress_stats['compressed_files']:
                print(f"  Compressed {len(compress_stats['compressed_files'])} files")
                print(f"  Saved {compress_stats['total_saved_mb']} MB")
            else:
                print("  No files to compress")
                
            if compress_stats['errors']:
                print(f"  Errors: {compress_stats['errors']}")

if __name__ == "__main__":
    asyncio.run(main())