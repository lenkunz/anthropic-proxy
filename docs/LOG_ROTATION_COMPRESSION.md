# Log Rotation and Compression System

This document describes the comprehensive log rotation and compression system implemented for the anthropic-proxy project's upstream logs.

## Overview

The log rotation system automatically manages upstream log files to prevent disk space issues while maintaining access to historical log data. The system provides:

- **Automatic log rotation** based on file size and time
- **Gzip compression** for efficient storage
- **Configurable retention policies**
- **Background monitoring** with minimal performance impact
- **Docker-compatible** implementation

## Architecture

### Core Components

1. **LogRotationConfig** (`src/log_rotation.py`)
   - Configuration management for all rotation settings
   - Environment variable integration
   - Default value handling

2. **LogRotator** (`src/log_rotation.py`)
   - Main rotation engine
   - File size monitoring and rotation triggers
   - Gzip compression implementation
   - Cleanup operations based on retention policies

3. **RotatingLogBatcher** (`src/log_rotation.py`)
   - Enhanced log batcher with rotation awareness
   - Integration with existing async logging system
   - Automatic rotation checking during write operations

4. **Log Rotation Monitor** (`src/main.py`)
   - Background task for periodic log management
   - Startup and shutdown coordination
   - Error handling and logging

## Configuration

### Environment Variables

All log rotation settings are configurable via environment variables in the `.env` file:

```bash
# Enable/disable log rotation
UPSTREAM_LOG_ROTATION=true

# Rotation settings
UPSTREAM_LOG_MAX_SIZE_MB=50          # Rotate when file exceeds 50MB
UPSTREAM_LOG_BACKUP_COUNT=10          # Keep 10 backup files
UPSTREAM_LOG_COMPRESSION=true         # Enable gzip compression
UPSTREAM_LOG_COMPRESS_IMMEDIATELY=true  # Compress immediately after rotation

# Cleanup settings
UPSTREAM_LOG_RETENTION_DAYS=30        # Delete files older than 30 days
LOG_CLEANUP_INTERVAL_HOURS=24        # Run cleanup every 24 hours

# Logging
LOG_ROTATION_LOGGING=true            # Enable rotation system logging
```

### Configuration Details

| Variable | Default | Description |
|----------|---------|-------------|
| `UPSTREAM_LOG_ROTATION` | `true` | Enable/disable the entire rotation system |
| `UPSTREAM_LOG_MAX_SIZE_MB` | `50` | Maximum file size before rotation (MB) |
| `UPSTREAM_LOG_BACKUP_COUNT` | `10` | Number of backup files to keep |
| `UPSTREAM_LOG_COMPRESSION` | `true` | Enable gzip compression |
| `UPSTREAM_LOG_COMPRESS_IMMEDIATELY` | `true` | Compress files immediately after rotation |
| `UPSTREAM_LOG_RETENTION_DAYS` | `30` | Days to keep rotated files |
| `LOG_CLEANUP_INTERVAL_HOURS` | `24` | Hours between cleanup runs |
| `LOG_ROTATION_LOGGING` | `true` | Log rotation system events |

## File Management

### Log Files Managed

The system manages all upstream log files:

- `upstream_requests.json` - API request logs
- `upstream_responses.json` - API response logs
- `performance_metrics.json` - Performance metrics
- `error_logs.json` - Error logs

### Rotation Process

1. **Size Check**: Before each write operation, the system checks if the current log file exceeds the configured maximum size
2. **File Rotation**: When the size limit is reached:
   - The current file is renamed with a timestamp: `filename.YYYYMMDD_HHMMSS.json`
   - A new empty file is created with the original name
   - The rotation is logged for monitoring
3. **Compression**: If compression is enabled:
   - The rotated file is immediately compressed using gzip
   - The compressed file gets a `.gz` extension
   - Original uncompressed file is removed
4. **Backup Management**: The system maintains only the configured number of backup files

### Cleanup Process

1. **Age-based Cleanup**: Files older than the retention period are automatically deleted
2. **Count-based Cleanup**: If backup count exceeds the limit, oldest files are removed
3. **Safety Checks**: Only files matching rotation patterns are affected

## Implementation Details

### Integration with Async Logging

The rotation system integrates seamlessly with the existing async logging infrastructure:

```python
# In AsyncUpstreamLogger.__init__()
self.upstream_requests_batcher = RotatingLogBatcher(
    log_dir / "upstream_requests.json",
    config=rotation_config
)
```

### Background Monitoring

A background task runs periodically to ensure rotation happens even during low-traffic periods:

```python
@app.on_event("startup")
async def startup_event():
    # Start log rotation monitor
    await log_rotation_monitor.start()
```

### Error Handling

The system includes comprehensive error handling:

- **Graceful degradation**: If rotation fails, logging continues
- **Error logging**: All rotation errors are logged for debugging
- **Recovery attempts**: Failed operations are retried on subsequent writes

## Docker Integration

### Volume Mounting

The system works with Docker volumes for persistent log storage:

```yaml
# docker-compose.yml
services:
  anthropic-proxy:
    volumes:
      - ./logs:/app/logs
    environment:
      - UPSTREAM_LOG_ROTATION=true
      - UPSTREAM_LOG_MAX_SIZE_MB=50
      # ... other rotation settings
```

### Container Considerations

- **Permissions**: Log files are created with appropriate permissions for the app user
- **Performance**: Async operations minimize impact on container performance
- **Monitoring**: Container logs include rotation system events

## Monitoring and Management

### Log Monitor Script

Use the provided monitoring script to check log status:

```bash
python3 scripts/log_monitor.py
```

Output includes:
- Total log file count and size
- File type breakdown
- Largest files list
- Compression statistics

### Manual Operations

#### Force Rotation
```python
from src.log_rotation import LogRotator, LogRotationConfig

config = LogRotationConfig()
rotator = LogRotator(config)
await rotator.rotate_file(Path("logs/upstream_requests.json"))
```

#### Manual Cleanup
```python
await rotator.cleanup_old_logs(Path("logs"))
```

## Performance Impact

### Minimal Overhead

- **Async Operations**: All rotation and compression operations are non-blocking
- **Batch Processing**: Rotation checks are bundled with write operations
- **Background Tasks**: Cleanup runs during low-traffic periods

### Resource Usage

- **Memory**: Minimal additional memory usage (< 1MB)
- **CPU**: Compression is the most CPU-intensive operation but runs asynchronously
- **Disk**: Temporary disk space needed during rotation/compression

## Troubleshooting

### Common Issues

1. **Rotation Not Triggering**
   - Check `UPSTREAM_LOG_ROTATION=true` in environment
   - Verify file size exceeds `UPSTREAM_LOG_MAX_SIZE_MB`
   - Check file permissions

2. **Compression Not Working**
   - Ensure `UPSTREAM_LOG_COMPRESSION=true`
   - Check available disk space
   - Verify gzip is available in container

3. **Too Many Log Files**
   - Adjust `UPSTREAM_LOG_BACKUP_COUNT` setting
   - Check `UPSTREAM_LOG_RETENTION_DAYS` configuration
   - Manually run cleanup script

### Debug Logging

Enable detailed rotation logging:

```bash
LOG_ROTATION_LOGGING=true
```

This will log rotation events including:
- File rotation triggers
- Compression operations
- Cleanup activities
- Error conditions

## Testing

### Test Suite

Run the comprehensive test suite:

```bash
python3 test_log_rotation.py
```

Tests cover:
- Rotation triggers based on file size
- Compression functionality and efficiency
- Cleanup operations
- Configuration validation
- Error handling

### Manual Testing

Create test log files to verify rotation:

```python
# Create a large test file
python3 -c "
import json
import os

# Create test data
test_data = [{'test': 'data'}] * 100000

# Write to log file
with open('logs/test_upstream.json', 'w') as f:
    for item in test_data:
        f.write(json.dumps(item) + '\n')

print(f'Created test file: {os.path.getsize(\"logs/test_upstream.json\")} bytes')
"
```

## Best Practices

### Production Configuration

```bash
# Recommended production settings
UPSTREAM_LOG_ROTATION=true
UPSTREAM_LOG_MAX_SIZE_MB=100
UPSTREAM_LOG_BACKUP_COUNT=20
UPSTREAM_LOG_COMPRESSION=true
UPSTREAM_LOG_COMPRESS_IMMEDIATELY=true
UPSTREAM_LOG_RETENTION_DAYS=90
LOG_CLEANUP_INTERVAL_HOURS=12
LOG_ROTATION_LOGGING=true
```

### Monitoring Recommendations

1. **Regular Log Monitoring**: Use the log monitor script weekly
2. **Disk Space Monitoring**: Set up alerts for log directory size
3. **Performance Monitoring**: Monitor application performance during high log volume
4. **Backup Strategy**: Ensure log backups align with data retention policies

### Maintenance

1. **Periodic Review**: Review rotation settings quarterly
2. **Log Analysis**: Analyze log growth patterns
3. **Storage Planning**: Plan storage capacity based on log growth rates
4. **Testing**: Test rotation system after configuration changes

## File Examples

### Rotated File Names

```
upstream_requests.json                    # Active log file
upstream_requests.20251001_121111.json.gz  # Compressed rotated file
upstream_requests.20251001_133037.json.gz  # Another rotated file
```

### Compression Efficiency

Typical compression ratios for log files:
- **Text logs**: 85-95% size reduction
- **JSON logs**: 80-90% size reduction
- **Structured logs**: 75-85% size reduction

## Security Considerations

### File Permissions

- Log files are created with `0644` permissions
- Log directories are created with `0755` permissions
- Container runs as non-root user for security

### Sensitive Data

- Log rotation preserves existing data access controls
- Compressed files maintain the same permissions as originals
- No data is exposed during rotation/compression processes

## Future Enhancements

### Planned Features

1. **Log Aggregation**: Integration with external log aggregation systems
2. **Advanced Filtering**: Content-based log rotation triggers
3. **Remote Storage**: Support for cloud storage backends
4. **Real-time Monitoring**: Web-based log monitoring interface
5. **Custom Compression**: Support for different compression algorithms

### Extension Points

The system is designed for easy extension:
- Custom rotation triggers
- Alternative compression methods
- Different cleanup strategies
- Integration with monitoring systems

## Conclusion

The log rotation and compression system provides a robust, configurable solution for managing upstream logs in the anthropic-proxy project. It ensures efficient disk space usage while maintaining access to historical log data for debugging and analysis purposes.

The system is designed to be:
- **Reliable**: Comprehensive error handling and recovery
- **Efficient**: Minimal performance impact
- **Configurable**: Flexible settings for different environments
- **Maintainable**: Clean, well-documented code structure
- **Scalable**: Handles high-volume logging scenarios

For questions or issues, refer to the troubleshooting section or check the system logs for detailed error information.