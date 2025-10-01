# Troubleshooting Guide

This comprehensive guide helps you diagnose and resolve common issues with the anthropic-proxy's intelligent context management system.

## 🚨 Quick Diagnostic Commands

### Health Check
```bash
# Basic health check
curl http://localhost:5000/health

# Check if service is running
docker compose ps

# View recent logs
docker compose logs --tail=50 anthropic-proxy
```

### Configuration Validation
```bash
# Verify environment variables
docker compose exec anthropic-proxy env | grep -E "(CONDENSATION|TOKEN|CACHE|CONTEXT)"

# Check .env file syntax
cat .env | grep -E "(^[^#].*=)" | while read line; do
    if [[ ! $line =~ ^[A-Z_][A-Z0-9_]*= ]]; then
        echo "Invalid line: $line"
    fi
done
```

### Performance Check
```bash
# Quick performance test
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{"model": "glm-4.6", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}' \
  -w "Time: %{time_total}s\n"
```

## 🧠 Intelligent Context Management Issues

### Issue: AI Condensation Not Working

#### Symptoms
- No condensation applied even at high context utilization
- Responses show `condensation_applied: false`
- High token usage without optimization

#### Diagnosis
```bash
# Check if AI condensation is enabled
grep ENABLE_AI_CONDENSATION .env

# Check API key configuration
grep SERVER_API_KEY .env

# Test AI condensation manually
python test_message_condensation.py

# Check logs for condensation attempts
docker compose logs anthropic-proxy | grep -i condensation
```

#### Solutions

**1. Enable AI Condensation**
```bash
# Add to .env file
ENABLE_AI_CONDENSATION=true
CONDENSATION_DEFAULT_STRATEGY=conversation_summary
CONDENSATION_CAUTION_THRESHOLD=0.70
CONDENSATION_WARNING_THRESHOLD=0.80
CONDENSATION_CRITICAL_THRESHOLD=0.90
```

**2. Verify API Key**
```bash
# Ensure valid API key is set
SERVER_API_KEY=your_valid_zai_api_key

# Test API key validity
curl -H "Authorization: Bearer $SERVER_API_KEY" \
  https://api.z.ai/api/anthropic/v1/messages \
  -d '{"model": "glm-4.6", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'
```

**3. Check Message Requirements**
```bash
# Ensure minimum message count is met
CONDENSATION_MIN_MESSAGES=3

# Verify thresholds are appropriate
CONDENSATION_WARNING_THRESHOLD=0.80  # Apply at 80% utilization
```

**4. Enable Debug Logging**
```bash
# Enable detailed logging
ENABLE_CONTEXT_PERFORMANCE_LOGGING=true
DEBUG=true

# Restart service
docker compose restart
```

### Issue: High Latency in Context Management

#### Symptoms
- Requests taking >500ms for context processing
- Slow response times even for simple requests
- Timeouts during AI condensation

#### Diagnosis
```bash
# Check processing times in logs
docker compose logs anthropic-proxy | grep -i "processing.*ms"

# Monitor resource usage
docker stats anthropic-proxy

# Check cache performance
python -c "
from context_window_manager import get_context_performance_stats
stats = get_context_performance_stats()
print(f'Cache hit ratio: {stats.get(\"cache_hit_ratio\", 0):.1%}')
print(f'Avg processing time: {stats.get(\"avg_processing_time_ms\", 0):.1f}ms')
"
```

#### Solutions

**1. Optimize Configuration**
```bash
# Reduce processing time
CONDENSATION_TIMEOUT=15                    # Reduce timeout
CONDENSATION_MAX_MESSAGES=5               # Process fewer messages
CONDENSATION_MIN_MESSAGES=3               # Lower minimum threshold

# Optimize caching
CONTEXT_CACHE_SIZE=200                     # Increase cache size
TIKTOKEN_CACHE_SIZE=2000                   # Increase token cache
```

**2. Enable Performance Mode**
```bash
# Disable logging for production
ENABLE_CONTEXT_PERFORMANCE_LOGGING=false
ENABLE_TOKEN_COUNTING_LOGGING=false
CACHE_ENABLE_LOGGING=false
```

**3. Resource Optimization**
```bash
# Allocate more resources to Docker
docker compose down
docker compose up -d --scale anthropic-proxy=2

# Or increase memory limits in docker-compose.yml
services:
  anthropic-proxy:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Issue: Inaccurate Token Counting

#### Symptoms
- Token counts don't match upstream API usage
- Context limit calculations seem incorrect
- Unexpected truncation or over-utilization

#### Diagnosis
```bash
# Check if accurate counting is enabled
grep ENABLE_ACCURATE_TOKEN_COUNTING .env

# Test token counting accuracy
python test_accurate_token_counter.py

# Compare with upstream API
curl -X POST http://localhost:5000/v1/messages/count_tokens \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{"model": "glm-4.6", "messages": [{"role": "user", "content": "test message"}]}'
```

#### Solutions

**1. Enable Accurate Counting**
```bash
# Enable tiktoken-based counting
ENABLE_ACCURATE_TOKEN_COUNTING=true
TIKTOKEN_CACHE_SIZE=1000

# Enable dynamic image token calculation
ENABLE_DYNAMIC_IMAGE_TOKENS=true
BASE_IMAGE_TOKENS=85
IMAGE_TOKENS_PER_CHAR=0.25
```

**2. Update tiktoken Library**
```bash
# Update to latest version
pip install --upgrade tiktoken

# Rebuild Docker image
docker compose down
docker compose build --no-cache
docker compose up -d
```

**3. Verify Configuration**
```bash
# Check token limits are correct
REAL_TEXT_MODEL_TOKENS=200000
REAL_VISION_MODEL_TOKENS=65536
ANTHROPIC_EXPECTED_TOKENS=200000
OPENAI_EXPECTED_TOKENS=200000
```

### Issue: Cache Performance Problems

#### Symptoms
- Low cache hit ratios (<80%)
- High memory usage
- Slow cache operations
- Cache-related errors in logs

#### Diagnosis
```bash
# Check cache statistics
python -c "
from context_window_manager import get_context_performance_stats
stats = get_context_performance_stats()
print('Cache Performance:')
for key, value in stats.items():
    if 'cache' in key.lower():
        print(f'  {key}: {value}')
"

# Monitor memory usage
docker stats anthropic-proxy --no-stream

# Check cache files
ls -la ./cache/
du -sh ./cache/
```

#### Solutions

**1. Optimize Cache Configuration**
```bash
# For high performance
CONTEXT_CACHE_SIZE=500
CONTEXT_ANALYSIS_CACHE_TTL=1800
CONDENSATION_CACHE_TTL=7200

# For memory efficiency
CONTEXT_CACHE_SIZE=50
CONTEXT_ANALYSIS_CACHE_TTL=300
CONDENSATION_CACHE_TTL=1800
```

**2. Clear Corrupted Cache**
```bash
# Clear cache files
rm -rf ./cache/*

# Clear in-memory caches
python -c "
from context_window_manager import clear_context_caches
clear_context_caches()
print('Caches cleared')
"

# Restart service
docker compose restart
```

**3. Enable Cache Monitoring**
```bash
# Enable cache logging
CACHE_ENABLE_LOGGING=true

# Monitor cache performance
watch -n 5 'docker compose logs anthropic-proxy | tail -20 | grep -i cache'
```

## 🔧 General System Issues

### Issue: Service Won't Start

#### Symptoms
- Docker container fails to start
- Health check failures
- Port binding errors

#### Diagnosis
```bash
# Check Docker status
docker compose ps
docker compose logs anthropic-proxy

# Check port availability
netstat -tlnp | grep :5000

# Check configuration syntax
docker compose config
```

#### Solutions

**1. Fix Port Conflicts**
```bash
# Kill processes using port 5000
sudo lsof -ti:5000 | xargs kill -9

# Or change port in docker-compose.yml
ports:
  - "5001:5000"  # Use port 5001 instead
```

**2. Fix Configuration Errors**
```bash
# Validate .env file
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
required_vars = ['SERVER_API_KEY', 'UPSTREAM_BASE', 'OPENAI_UPSTREAM_BASE']
for var in required_vars:
    if not os.getenv(var):
        print(f'Missing required variable: {var}')
"
```

**3. Rebuild Container**
```bash
# Clean rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Issue: Authentication Problems

#### Symptoms
- 401 Unauthorized errors
- API key authentication failures
- Forwarding issues

#### Diagnosis
```bash
# Test authentication
curl -H "Authorization: Bearer test" http://localhost:5000/v1/models

# Check API key configuration
grep SERVER_API_KEY .env

# Check forwarding configuration
grep FORWARD_CLIENT_KEY .env
```

#### Solutions

**1. Fix API Key Configuration**
```bash
# Set valid API key
SERVER_API_KEY=your_valid_zai_api_key

# Enable client key forwarding
FORWARD_CLIENT_KEY=true
```

**2. Test API Key Validity**
```bash
# Test with upstream service
curl -H "Authorization: Bearer $SERVER_API_KEY" \
  -H "Content-Type: application/json" \
  https://api.z.ai/api/anthropic/v1/messages \
  -d '{"model": "glm-4.6", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'
```

### Issue: Memory Leaks

#### Symptoms
- Memory usage continuously increases
- Container gets killed by OOM killer
- Performance degrades over time

#### Diagnosis
```bash
# Monitor memory usage
docker stats anthropic-proxy

# Check for memory leaks
watch -n 10 'docker stats --no-stream anthropic-proxy'

# Analyze memory patterns
python -c "
import psutil
import time
while True:
    process = psutil.Process()
    print(f'Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB')
    time.sleep(30)
"
```

#### Solutions

**1. Reduce Cache Sizes**
```bash
# Conservative cache settings
CONTEXT_CACHE_SIZE=50
TIKTOKEN_CACHE_SIZE=500
CONDENSATION_CACHE_TTL=1800
```

**2. Enable Cache Cleanup**
```bash
# Add to configuration
CACHE_CLEANUP_INTERVAL=1800
MAX_MEMORY_USAGE_MB=1024
```

**3. Monitor and Restart**
```bash
# Create monitoring script
cat > monitor_memory.sh << 'EOF'
#!/bin/bash
MEMORY_USAGE=$(docker stats --no-stream anthropic-proxy --format "{{.MemUsage}}" | sed 's/MiB//')
if (( $(echo "$MEMORY_USAGE > 2048" | bc -l) )); then
    echo "High memory usage detected: ${MEMORY_USAGE}MiB"
    docker compose restart anthropic-proxy
fi
EOF

chmod +x monitor_memory.sh

# Run every 5 minutes
*/5 * * * * /path/to/monitor_memory.sh
```

## 🖼️ Image Processing Issues

### Issue: Image Age Management Not Working

#### Symptoms
- Images not being replaced with descriptions
- Auto-switching to text endpoint not happening
- Old images remaining in context

#### Diagnosis
```bash
# Check image age configuration
grep IMAGE_AGE_THRESHOLD .env

# Test image age management
python test_image_handling_updates.py

# Check logs for image processing
docker compose logs anthropic-proxy | grep -i image
```

#### Solutions

**1. Configure Image Age Management**
```bash
# Set appropriate threshold
IMAGE_AGE_THRESHOLD=8                    # Messages before images are old
CACHE_CONTEXT_MESSAGES=2                 # Context for descriptions
IMAGE_AGE_TRUNCATION_MESSAGE="[Previous images in conversation context: {descriptions}]"
```

**2. Enable Image Description Generation**
```bash
# Ensure vision model is configured
AUTOVISION_MODEL=glm-4.6v
SERVER_API_KEY=your_valid_api_key
```

### Issue: Image Token Calculation Problems

#### Symptoms
- Incorrect token counts for images
- Fixed 1000 tokens per image instead of dynamic calculation
- Context limit issues with images

#### Diagnosis
```bash
# Check dynamic token calculation
grep ENABLE_DYNAMIC_IMAGE_TOKENS .env

# Test image token counting
python validate_image_handling.py
```

#### Solutions

**1. Enable Dynamic Token Calculation**
```bash
ENABLE_DYNAMIC_IMAGE_TOKENS=true
BASE_IMAGE_TOKENS=85
IMAGE_TOKENS_PER_CHAR=0.25
```

**2. Update Configuration**
```bash
# Verify image token settings
BASE_IMAGE_TOKENS=85                   # Base tokens for image metadata
IMAGE_TOKENS_PER_CHAR=0.25             # Tokens per character in description
```

## 🚀 Performance Issues

### Issue: Slow Response Times

#### Symptoms
- Requests taking >1 second
- Timeouts during processing
- Poor user experience

#### Diagnosis
```bash
# Measure response time
time curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test" \
  -d '{"model": "glm-4.6", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'

# Check system resources
docker stats anthropic-proxy
top -p $(docker inspect -f '{{.State.Pid}}' anthropic-proxy)
```

#### Solutions

**1. Optimize Configuration**
```bash
# High-performance settings
CONDENSATION_TIMEOUT=15
CONDENSATION_MAX_MESSAGES=5
ENABLE_CONTEXT_PERFORMANCE_LOGGING=false
```

**2. Enable Caching**
```bash
# Optimize cache settings
CONTEXT_CACHE_SIZE=200
TIKTOKEN_CACHE_SIZE=2000
CACHE_ENABLE_LOGGING=false
```

**3. Scale Horizontally**
```bash
# Run multiple instances
docker compose up -d --scale anthropic-proxy=3

# Add load balancer
# (Configure nginx or similar load balancer)
```

### Issue: High CPU Usage

#### Symptoms
- CPU usage consistently >80%
- System becoming unresponsive
- Thermal throttling

#### Diagnosis
```bash
# Monitor CPU usage
docker stats anthropic-proxy

# Check CPU-intensive processes
top -p $(docker inspect -f '{{.State.Pid}}' anthropic-proxy)

# Analyze CPU patterns
htop
```

#### Solutions

**1. Optimize Processing**
```bash
# Reduce processing load
CONDENSATION_MAX_MESSAGES=3
CONDENSATION_TIMEOUT=10
ENABLE_CONTEXT_PERFORMANCE_LOGGING=false
```

**2. Enable Async Processing**
```bash
# Ensure async operations are enabled
ENABLE_ASYNC_PROCESSING=true
MAX_CONCURRENT_REQUESTS=10
```

**3. Resource Allocation**
```bash
# Limit CPU usage in docker-compose.yml
services:
  anthropic-proxy:
    deploy:
      resources:
        limits:
          cpus: '2.0'
        reservations:
          cpus: '1.0'
```

## 🔍 Debugging Tools and Techniques

### Enable Comprehensive Debugging

```bash
# Enable all debug options
DEBUG=true
ENABLE_CONTEXT_PERFORMANCE_LOGGING=true
ENABLE_TOKEN_COUNTING_LOGGING=true
CACHE_ENABLE_LOGGING=true

# Lower thresholds for testing
CONDENSATION_CAUTION_THRESHOLD=0.30
CONDENSATION_WARNING_THRESHOLD=0.50
CONDENSATION_CRITICAL_THRESHOLD=0.70

# Restart service
docker compose restart
```

### Debug Scripts

**1. Context Analysis Debug Script**
```python
#!/usr/bin/env python3
import asyncio
from context_window_manager import analyze_context_state

async def debug_context():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! " * 1000},
        {"role": "assistant", "content": "I can help you! " * 1000},
    ]
    
    analysis = analyze_context_state(messages, is_vision=False)
    
    print("=== Context Analysis ===")
    print(f"Risk Level: {analysis.risk_level.value}")
    print(f"Utilization: {analysis.utilization_percent:.1f}%")
    print(f"Current Tokens: {analysis.current_tokens}")
    print(f"Limit Tokens: {analysis.limit_tokens}")
    print(f"Available Tokens: {analysis.available_tokens}")
    print(f"Should Condense: {analysis.should_condense}")
    print(f"Recommended Strategy: {analysis.recommended_strategy.value}")
    print(f"Messages Count: {analysis.messages_count}")
    print(f"Analysis Time: {analysis.analysis_time:.3f}s")

if __name__ == "__main__":
    asyncio.run(debug_context())
```

**2. Performance Monitoring Script**
```python
#!/usr/bin/env python3
import time
import asyncio
from context_window_manager import get_context_performance_stats

async def monitor_performance():
    while True:
        stats = get_context_performance_stats()
        
        print(f"\n=== Performance Stats ({time.strftime('%H:%M:%S')}) ===")
        print(f"Cache Hit Ratio: {stats.get('cache_hit_ratio', 0):.1%}")
        
        if 'condensation_stats' in stats:
            cond_stats = stats['condensation_stats']
            print(f"Condensation Success Rate: {cond_stats.get('success_rate', 0):.1%}")
            print(f"Avg Processing Time: {cond_stats.get('avg_processing_time_ms', 0):.1f}ms")
            print(f"Avg Tokens Saved: {cond_stats.get('avg_tokens_saved', 0):.1f}")
        
        print(f"Memory Usage: {stats.get('memory_usage_mb', 0):.1f} MB")
        
        await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(monitor_performance())
```

### Log Analysis

**1. Filter Relevant Logs**
```bash
# Context management logs
docker compose logs anthropic-proxy | grep -i -E "(context|condensation|token)"

# Error logs
docker compose logs anthropic-proxy | grep -i -E "(error|exception|failed)"

# Performance logs
docker compose logs anthropic-proxy | grep -i -E "(processing|latency|cache)"
```

**2. Real-time Log Monitoring**
```bash
# Monitor context management in real-time
docker compose logs -f anthropic-proxy | grep -i --line-buffered "context"

# Monitor errors
docker compose logs -f anthropic-proxy | grep -i --line-buffered -E "(error|exception|critical)"
```

## 📞 Getting Help

### When to Seek Help

- Issues persist after trying all solutions
- Performance degrades significantly
- Unexpected behavior not covered in this guide
- Need help with configuration optimization

### Information to Provide

When seeking help, provide:

1. **System Information**:
   ```bash
   docker --version
   docker compose version
   python --version
   uname -a
   ```

2. **Configuration**:
   ```bash
   # Sanitize your .env file (remove API keys)
   grep -E "^[^#].*=" .env | grep -v "API_KEY"
   ```

3. **Logs**:
   ```bash
   # Recent logs (last 100 lines)
   docker compose logs --tail=100 anthropic-proxy
   ```

4. **Error Details**:
   - Exact error messages
   Steps to reproduce
   Expected vs actual behavior

### Community Resources

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check [INTELLIGENT_CONTEXT_MANAGEMENT.md](INTELLIGENT_CONTEXT_MANAGEMENT.md)
- **Performance Guide**: See [PERFORMANCE_GUIDE.md](PERFORMANCE_GUIDE.md)
- **Migration Guide**: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

## 🔧 Maintenance and Prevention

### Regular Maintenance Tasks

1. **Weekly**:
   - Check cache hit ratios
   - Monitor memory usage
   - Review error logs

2. **Monthly**:
   - Update dependencies
   - Review and optimize configuration
   - Run full test suite

3. **Quarterly**:
   - Performance benchmarking
   - Capacity planning
   - Security audit

### Preventive Measures

1. **Monitoring Setup**:
   ```bash
   # Set up basic monitoring
   ENABLE_CONTEXT_PERFORMANCE_LOGGING=true
   
   # Create health check script
   cat > health_check.sh << 'EOF'
   #!/bin/bash
   if ! curl -f http://localhost:5000/health > /dev/null 2>&1; then
       echo "Service unhealthy, restarting..."
       docker compose restart
   fi
   EOF
   
   # Run every 5 minutes
   */5 * * * * /path/to/health_check.sh
   ```

2. **Backup Configuration**:
   ```bash
   # Backup configuration regularly
   cp .env .env.backup.$(date +%Y%m%d)
   cp docker-compose.yml docker-compose.yml.backup.$(date +%Y%m%d)
   ```

3. **Log Rotation**:
   ```bash
   # Set up log rotation
   cat > /etc/logrotate.d/anthropic-proxy << 'EOF'
   /var/log/anthropic-proxy/*.log {
       daily
       rotate 7
       compress
       delaycompress
       missingok
       notifempty
   }
   EOF
   ```

By following this troubleshooting guide and implementing preventive measures, you can maintain a healthy and performant intelligent context management system.