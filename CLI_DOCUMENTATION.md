# Anthropic Proxy CLI Documentation

## Overview

The Anthropic Proxy CLI provides comprehensive management capabilities for the proxy server, including intelligent auto-switching, performance monitoring, and endpoint discovery.

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd anthropic-proxy

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x proxy-cli
```

## Configuration

The CLI uses a `config.yaml` file for configuration. Each server can have dual endpoints:

```yaml
servers:
  cn:
    api_key: ''  # Leave empty to use SERVER_API_KEY from .env
    endpoints:
      anthropic: https://open.bigmodel.cn/api/anthropic
      openai: https://open.bigmodel.cn/api/paas/v4
    region: China
  inter:
    api_key: ''  # Leave empty to use SERVER_API_KEY from .env
    endpoints:
      anthropic: https://api.z.ai/api/anthropic
      openai: https://api.z.ai/api/coding/paas/v4
    region: International
current_server: cn
cli:
  auto_switch_enabled: false
  auto_switch_interval: 60
  refresh_interval: 2
```

## CLI Commands

### Basic Commands

#### Start Proxy
```bash
./proxy-cli start
```

#### Stop Proxy
```bash
./proxy-cli stop
```

#### Restart Proxy
```bash
./proxy-cli restart
```

#### Check Status
```bash
./proxy-cli status
```

### Server Management

#### List All Servers
```bash
./proxy-cli servers
```

#### Switch Server
```bash
./proxy-cli switch cn
./proxy-cli switch inter
```

#### View Configuration
```bash
./proxy-cli config
```

### Intelligent Auto-Switching

#### Basic Auto-Switching
```bash
./proxy-cli auto-switch
```

#### Custom Auto-Switching Interval
```bash
./proxy-cli auto-switch --interval 30
```

#### Intelligent Auto-Switching with Endpoint Discovery
```bash
./proxy-cli smart-switch
```

#### Custom Intelligent Switching Interval
```bash
./proxy-cli smart-switch --interval 120
```

### Endpoint Discovery

#### Discover Endpoints for a Domain
```bash
./proxy-cli discover-endpoints --domain api.z.ai
```

#### Test Specific Endpoint
```bash
./proxy-cli test-endpoint --ip 123.45.67.89 --domain api.z.ai
```

### Monitoring

#### Real-time Status Monitoring
```bash
./proxy-cli monitor
```

#### Health Check Loop
```bash
./proxy-cli health-check --interval 30
```

#### View Logs
```bash
./proxy-cli logs
./proxy-cli logs --lines 100
```

### Configuration Management

#### Set API Key
```bash
./proxy-cli set-api-key --server cn --key "your-api-key"
```

#### Set Refresh Interval
```bash
./proxy-cli set-refresh-interval 5
```

#### Export Configuration
```bash
./proxy-cli export-config --filename backup.yaml
```

#### Import Configuration
```bash
./proxy-cli import-config --filename backup.yaml
```

## Advanced Features

### Dual Endpoint Configuration

Each server supports dual endpoints for different API types:

- **Anthropic Endpoint**: For Anthropic-compatible API requests
- **OpenAI Endpoint**: For OpenAI-compatible API requests (including vision models)

The CLI automatically selects the appropriate endpoint based on the request type.

### Intelligent Auto-Switching

The intelligent auto-switching feature uses:

1. **Performance Monitoring**: Tracks latency, response times, and request rates
2. **Endpoint Discovery**: Uses check-host.net API to discover multiple IP endpoints
3. **Thinking-Based Testing**: Validates endpoints with actual API requests
4. **Automatic Failover**: Switches to better endpoints when performance degrades

#### Performance Metrics

The system monitors:
- Latency (ms)
- Requests per second
- Average response time
- Success rate

#### Switching Criteria

Auto-switching occurs when:
- Current server fails (timeout or error)
- Latency exceeds 800ms
- Request rate exceeds 50 req/s
- Average response time exceeds 2000ms
- Better endpoint found with at least 20% improvement

### Environment Variables

The CLI supports the following environment variables:

- `SERVER_API_KEY`: Default API key for all servers
- `PROXY_HOST`: Proxy server host (default: 0.0.0.0)
- `PROXY_PORT`: Proxy server port (default: 5000)
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENABLE_STATS`: Enable statistics collection (default: true)

## Examples

### Example 1: Basic Server Switching

```bash
# Check current server status
./proxy-cli servers

# Switch to international server
./proxy-cli switch inter

# Restart proxy with new server
./proxy-cli restart
```

### Example 2: Intelligent Auto-Switching

```bash
# Start intelligent auto-switching with 2-minute intervals
./proxy-cli smart-switch --interval 120

# The system will:
# 1. Monitor current server performance
# 2. Discover alternative endpoints using check-host.net
# 3. Test discovered endpoints with actual API requests
# 4. Switch to better endpoints automatically
```

### Example 3: Manual Endpoint Discovery

```bash
# Discover endpoints for a domain
./proxy-cli discover-endpoints --domain api.z.ai

# Test a specific endpoint
./proxy-cli test-endpoint --ip 123.45.67.89 --domain api.z.ai

# Switch to a better endpoint manually
./proxy-cli switch-endpoint --server inter --endpoint https://123.45.67.89/api/anthropic
```

### Example 4: Configuration Management

```bash
# Export current configuration
./proxy-cli export-config --filename backup.yaml

# View configuration summary
./proxy-cli config

# Set custom refresh interval
./proxy-cli set-refresh-interval 3
```

## Troubleshooting

### Common Issues

#### "Illegal header" Error
- Ensure API key is configured in config.yaml or SERVER_API_KEY environment variable
- Check that the API key is valid and not expired

#### Server Timeout
- Check network connectivity
- Verify endpoint URLs are correct
- Try switching to an alternative server

#### Auto-Switching Not Working
- Ensure auto_switch_enabled is set to true in config.yaml
- Check that both servers are configured correctly
- Verify API keys are valid for all servers

### Debug Commands

#### Enable Debug Logging
```bash
export LOG_LEVEL=DEBUG
./proxy-cli status
```

#### Test Server Connectivity
```bash
./proxy-cli test-server --server cn
./proxy-cli test-server --server inter
```

#### View Detailed Performance Metrics
```bash
./proxy-cli performance --detailed
```

## API Reference

### ProxyManager Class

The main class for managing proxy server operations.

#### Methods

- `start()`: Start the proxy server
- `stop()`: Stop the proxy server
- `restart()`: Restart the proxy server
- `is_running()`: Check if proxy is running
- `get_status()`: Get detailed proxy status
- `switch_server(server_name)`: Switch to a different server
- `measure_server_performance(server_name)`: Measure server performance
- `auto_switch_if_needed()`: Auto-switch if current server is underperforming
- `intelligent_auto_switch_with_discovery()`: Intelligent auto-switching with endpoint discovery

### Config Class

Configuration management for the CLI.

#### Methods

- `get_all_servers()`: Get all configured servers
- `get_current_server()`: Get current server name
- `set_current_server(server_name)`: Set current server
- `update_server_endpoint(server_name, new_endpoint)`: Update server endpoint
- `get_cli_setting(key, default)`: Get CLI configuration setting
- `set_cli_setting(key, value)`: Set CLI configuration setting

## Contributing

To contribute to the CLI:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.