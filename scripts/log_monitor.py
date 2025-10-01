#!/usr/bin/env python3
"""
Log monitoring script for anthropic-proxy.
Provides simple log statistics and monitoring functionality.
"""

import os
import sys
import json
import gzip
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

def get_log_stats(log_dir: str = "./logs") -> Dict[str, Any]:
    """Get statistics about log files"""
    log_path = Path(log_dir)
    
    if not log_path.exists():
        return {"error": f"Log directory {log_dir} does not exist"}
    
    stats = {
        "directory": str(log_path),
        "total_files": 0,
        "total_size_mb": 0,
        "file_types": {},
        "files": []
    }
    
    for log_file in log_path.glob("*.json*"):
        try:
            file_stat = log_file.stat()
            file_size_mb = round(file_stat.st_size / (1024 * 1024), 2)
            
            file_info = {
                "name": log_file.name,
                "size_mb": file_size_mb,
                "modified": datetime.fromtimestamp(file_stat.st_mtime, timezone.utc).isoformat(),
                "is_compressed": log_file.suffix == '.gz'
            }
            
            stats["files"].append(file_info)
            stats["total_files"] += 1
            stats["total_size_mb"] += file_size_mb
            
            # Count file types
            ext = log_file.suffix
            stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
            
        except Exception as e:
            print(f"Error processing {log_file}: {e}")
    
    # Sort files by size (largest first)
    stats["files"].sort(key=lambda x: x["size_mb"], reverse=True)
    stats["total_size_mb"] = round(stats["total_size_mb"], 2)
    
    return stats

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Log monitoring for anthropic-proxy")
    parser.add_argument("--dir", default="./logs", help="Log directory path")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    stats = get_log_stats(args.dir)
    
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"Log Statistics for: {stats['directory']}")
        print(f"Total files: {stats['total_files']}")
        print(f"Total size: {stats['total_size_mb']} MB")
        print(f"File types: {stats['file_types']}")
        
        if stats['files']:
            print(f"\nTop 10 largest files:")
            for i, file_info in enumerate(stats['files'][:10], 1):
                compressed = " (compressed)" if file_info['is_compressed'] else ""
                print(f"  {i}. {file_info['name']} - {file_info['size_mb']} MB{compressed}")

if __name__ == "__main__":
    main()