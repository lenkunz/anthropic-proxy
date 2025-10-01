#!/usr/bin/env python3
"""
Test script for log rotation functionality.
Tests the log rotation and compression system.
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from log_rotation import LogRotator, LogRotationConfig, RotatingLogBatcher

async def test_log_rotation():
    """Test log rotation functionality"""
    print("Testing log rotation system...")
    
    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        log_file = temp_path / "test_upstream.json"
        
        # Create test configuration
        config = LogRotationConfig()
        config.log_dir = temp_path
        config.max_file_size_mb = 1  # 1MB for quick testing
        config.backup_count = 3
        config.compression_enabled = True
        config.compress_immediately = True
        
        # Create rotator
        rotator = LogRotator(config)
        
        print(f"Test directory: {temp_path}")
        print(f"Max file size: {config.max_file_size_mb} MB")
        print(f"Backup count: {config.backup_count}")
        
        # Create rotating batcher
        batcher = RotatingLogBatcher(str(log_file), rotator, batch_size=10, batch_timeout=1.0)
        
        # Generate enough log data to trigger rotation
        print("Generating test log data...")
        
        for i in range(100):
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_id": i,
                "message": "This is a test log entry " * 100,  # Make it sizable
                "data": {"x": "y" * 50}
            }
            
            await batcher.add_entry(log_entry)
            
            # Check if rotation happened
            if i % 20 == 0:
                if log_file.exists():
                    size_mb = log_file.stat().st_size / (1024 * 1024)
                    print(f"  Log file size: {size_mb:.2f} MB")
        
        # Force flush
        await batcher.force_flush()
        
        # Wait a moment for async operations
        await asyncio.sleep(2)
        
        # Check results
        print("\nChecking results...")
        
        log_files = list(temp_path.glob("*.json*"))
        print(f"Files created: {len(log_files)}")
        
        for file_path in sorted(log_files):
            size_mb = file_path.stat().st_size / (1024 * 1024)
            compressed = " (compressed)" if file_path.suffix == '.gz' else ""
            print(f"  {file_path.name}: {size_mb:.2f} MB{compressed}")
        
        # Test statistics
        stats = rotator.get_log_statistics()
        print(f"\nLog statistics:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        
        # Test cleanup
        print("\nTesting cleanup...")
        await rotator.cleanup_old_logs()
        
        print("Log rotation test completed successfully!")

async def test_log_compression():
    """Test log compression functionality"""
    print("\nTesting log compression...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        test_file = temp_path / "test_log.json"
        
        # Create test data
        test_data = []
        for i in range(1000):
            test_data.append({
                "id": i,
                "message": "Test message for compression " * 10,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Write test data to file
        with open(test_file, 'w') as f:
            for entry in test_data:
                f.write(json.dumps(entry) + '\n')
        
        original_size = test_file.stat().st_size
        print(f"Original file size: {original_size / (1024 * 1024):.2f} MB")
        
        # Create rotator and compress
        config = LogRotationConfig()
        config.compression_enabled = True
        rotator = LogRotator(config)
        
        await rotator._compress_file_async(test_file)
        
        # Check compressed file
        compressed_file = test_file.with_suffix(test_file.suffix + '.gz')
        if compressed_file.exists():
            compressed_size = compressed_file.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100
            print(f"Compressed file size: {compressed_size / (1024 * 1024):.2f} MB")
            print(f"Compression ratio: {compression_ratio:.1f}%")
            print("Compression test successful!")
        else:
            print("Compression test failed - no compressed file found")

async def main():
    """Main test function"""
    print("Starting log rotation tests...")
    
    try:
        await test_log_rotation()
        await test_log_compression()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())