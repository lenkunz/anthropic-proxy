#!/usr/bin/env python3
"""Simple log reader to examine enhanced error logging"""

import json
import os
from datetime import datetime

def read_json_lines_file(file_path):
    """Read a JSON Lines file (one JSON object per line)"""
    entries = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        entries.append(entry)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Skipped invalid JSON line in {file_path}: {line[:50]}...")
        return entries
    except Exception as e:
        print(f"❌ Could not read {file_path}: {e}")
        return []

def format_error_entry(entry):
    """Format a single error log entry for display"""
    print("🔍 Enhanced Error Log Entry:")
    print(f"   Timestamp: {entry.get('timestamp', 'unknown')}")
    print(f"   Request ID: {entry.get('req_id', 'unknown')}")
    print(f"   Type: {entry.get('type', 'unknown')}")
    print(f"   Where: {entry.get('where', 'unknown')}")
    
    if 'model' in entry:
        print(f"   Model: {entry['model']}")
    
    if 'upstream_status' in entry:
        print(f"   Upstream Status: {entry['upstream_status']}")
        
    if 'upstream_url' in entry:
        print(f"   Upstream URL: {entry['upstream_url']}")
        
    if 'exc' in entry and entry['exc']:
        exc = entry['exc']
        print(f"   Exception Type: {exc.get('type', 'unknown')}")
        print(f"   Exception Message: {exc.get('message', 'unknown')}")
        if 'traceback' in exc:
            print(f"   Traceback: {exc['traceback'][:200]}...")
    
    if 'image_content_type' in entry:
        print(f"   Image Content Type: {entry['image_content_type']}")
        
    if 'message_role' in entry:
        print(f"   Message Role: {entry['message_role']}")
    
    print("   " + "="*50)

def main():
    """Check for enhanced error logs"""
    logs_dir = "/home/souta/IKP/cs-refactor/cashout/anthropic-proxy/logs"
    
    print("📋 Enhanced Error Logging Analysis")
    print("="*60)
    
    # Check for error logs first
    error_files = ['errors.json']
    found_errors = False
    
    for error_file in error_files:
        error_path = os.path.join(logs_dir, error_file)
        if os.path.exists(error_path):
            print(f"\n📄 Reading {error_file}...")
            entries = read_json_lines_file(error_path)
            
            for entry in entries:
                format_error_entry(entry)
                found_errors = True
    
    if not found_errors:
        print("\n🔍 No error logs found. Checking all log files for recent entries...")
        
        try:
            log_files = [f for f in os.listdir(logs_dir) if f.endswith('.json')]
            log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
            
            print(f"Found {len(log_files)} log files:")
            for log_file in log_files[:3]:  # Check the 3 most recent
                print(f"\n📄 Checking {log_file}...")
                log_path = os.path.join(logs_dir, log_file)
                entries = read_json_lines_file(log_path)
                
                # Show the most recent few entries
                for entry in entries[-2:]:
                    if any(key in entry for key in ['error', 'exc', 'where', 'upstream_status']):
                        format_error_entry(entry)
                    else:
                        print(f"   📝 Regular entry: {entry.get('type', 'unknown')} - {entry.get('timestamp', 'unknown')}")
                        
        except Exception as e:
            print(f"❌ Could not list log files: {e}")
    
    print(f"\n📊 Summary: {'Enhanced error logging is working!' if found_errors else 'No enhanced error logs found in recent files.'}")

if __name__ == "__main__":
    main()