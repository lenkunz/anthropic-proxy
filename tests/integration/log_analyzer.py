#!/usr/bin/env python3

"""
Simple log analyzer for anthropic-proxy logs.
Provides easy ways to view and filter log information.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

def analyze_logs(logs_dir: str = "logs", hours: int = 1) -> None:
    """Analyze recent logs and display a summary."""
    
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        print(f"Logs directory {logs_dir} not found")
        return
    
    print(f"=== Log Analysis for {logs_dir} ===\\n")
    
    # Get log files
    log_files = list(logs_path.glob("*.log"))
    json_files = list(logs_path.glob("*.json"))
    
    if not log_files and not json_files:
        print("No log files found")
        return
    
    # Display file sizes and dates
    print("Log Files:")
    print("-" * 50)
    for log_file in sorted(log_files + json_files):
        try:
            stat = log_file.stat()
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime)
            print(f"{log_file.name:25} {size:8} bytes  {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"{log_file.name:25} Error: {e}")
    
    print()
    
    # Analyze recent access logs if available
    access_log = logs_path / "access.log"
    if access_log.exists():
        print("Recent Access Log Entries:")
        print("-" * 50)
        try:
            with access_log.open('r') as f:
                lines = f.readlines()
                # Show last 10 lines
                for line in lines[-10:]:
                    print(line.strip())
        except Exception as e:
            print(f"Error reading access log: {e}")
        print()
    
    # Analyze recent error logs if available
    error_log = logs_path / "errors.log"
    if error_log.exists():
        print("Recent Error Log Entries:")
        print("-" * 50)
        try:
            with error_log.open('r') as f:
                lines = f.readlines()
                # Show last 5 lines
                for line in lines[-5:]:
                    print(line.strip())
        except Exception as e:
            print(f"Error reading error log: {e}")
        print()
    
    # Count requests by endpoint
    api_log = logs_path / "api_requests.json"
    if api_log.exists():
        print("API Request Summary:")
        print("-" * 50)
        endpoints = {}
        models = {}
        try:
            with api_log.open('r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        url = data.get('url', 'unknown')
                        model = data.get('model', 'unknown')
                        
                        # Extract endpoint from URL
                        if '/v1/chat/completions' in url:
                            endpoint = '/v1/chat/completions'
                        elif '/v1/models' in url:
                            endpoint = '/v1/models'
                        elif '/health' in url:
                            endpoint = '/health'
                        else:
                            endpoint = url
                        
                        endpoints[endpoint] = endpoints.get(endpoint, 0) + 1
                        if model != 'unknown':
                            models[model] = models.get(model, 0) + 1
                    except json.JSONDecodeError:
                        continue
            
            for endpoint, count in endpoints.items():
                print(f"  {endpoint:30} {count:5} requests")
            
            print("\\nModel Usage:")
            for model, count in models.items():
                print(f"  {model:30} {count:5} requests")
                
        except Exception as e:
            print(f"Error reading API request log: {e}")

def tail_logs(logs_dir: str = "logs", file_name: str = "application.log", lines: int = 20) -> None:
    """Show the last N lines of a specific log file."""
    
    log_file = Path(logs_dir) / file_name
    if not log_file.exists():
        print(f"Log file {log_file} not found")
        return
    
    print(f"=== Last {lines} lines of {file_name} ===\\n")
    
    try:
        with log_file.open('r') as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print(line.rstrip())
    except Exception as e:
        print(f"Error reading log file: {e}")

def search_logs(logs_dir: str = "logs", query: str = "", log_level: str = "") -> None:
    """Search through log files for specific content."""
    
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        print(f"Logs directory {logs_dir} not found")
        return
    
    print(f"=== Searching logs for: '{query}' (level: {log_level or 'any'}) ===\\n")
    
    # Search text log files
    for log_file in logs_path.glob("*.log"):
        try:
            with log_file.open('r') as f:
                for line_num, line in enumerate(f, 1):
                    if query.lower() in line.lower():
                        if not log_level or log_level.upper() in line.upper():
                            print(f"{log_file.name}:{line_num}: {line.strip()}")
        except Exception as e:
            print(f"Error searching {log_file}: {e}")
    
    # Search JSON log files
    for json_file in logs_path.glob("*.json"):
        try:
            with json_file.open('r') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        line_str = json.dumps(data, indent=None)
                        if query.lower() in line_str.lower():
                            if not log_level or log_level.lower() == data.get('level', '').lower():
                                print(f"{json_file.name}:{line_num}: {line.strip()}")
                    except json.JSONDecodeError:
                        # Also search raw content for non-JSON lines
                        if query.lower() in line.lower():
                            print(f"{json_file.name}:{line_num}: {line.strip()}")
        except Exception as e:
            print(f"Error searching {json_file}: {e}")

def main():
    """Main command line interface."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze anthropic-proxy logs")
    parser.add_argument("--logs-dir", default="logs", help="Directory containing log files")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze and summarize logs")
    analyze_parser.add_argument("--hours", type=int, default=1, help="Hours of history to analyze")
    
    # Tail command
    tail_parser = subparsers.add_parser("tail", help="Show last lines of a log file")
    tail_parser.add_argument("--file", default="application.log", help="Log file name")
    tail_parser.add_argument("--lines", type=int, default=20, help="Number of lines to show")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search through log files")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--level", help="Filter by log level (ERROR, INFO, DEBUG, etc.)")
    
    args = parser.parse_args()
    
    if not args.command:
        # Default to analyze
        analyze_logs(args.logs_dir)
    elif args.command == "analyze":
        analyze_logs(args.logs_dir, args.hours)
    elif args.command == "tail":
        tail_logs(args.logs_dir, args.file, args.lines)
    elif args.command == "search":
        search_logs(args.logs_dir, args.query, args.level or "")

if __name__ == "__main__":
    main()