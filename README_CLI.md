# Anthropic Proxy CLI

A comprehensive command-line interface for managing the Anthropic Proxy server with advanced features like IP overrides, model switching, and auto-completion.

## Features

- 🚀 **Server Management**: Start, stop, restart, and monitor the proxy server
- 🌐 **IP Overrides**: Override server IPs for testing different datacenters
- 🤖 **Model Management**: Switch between AI models with token configuration
- 🔬 **Context Testing**: Test context window limits using binary search
- 📊 **Performance Monitoring**: Real-time server performance and health monitoring
- 🔍 **Endpoint Discovery**: Discover multiple IP endpoints for domains
- 🖥️ **Auto-completion**: Full shell auto-completion support (bash, zsh, fish)
- ⚡ **No-Restart Switching**: Switch servers and models without restarting

## Quick Start

### 1. Install Dependencies

```bash
pip install --break-system-packages httpx click pyyaml requests rich aiofiles
```

### 2. Setup Auto-completion

```bash
# Run the setup script
./setup.sh install

# Or manually install completion
PYTHONPATH=. python3 -m cli completion bash >> ~/.bashrc
source ~/.bashrc
```

### 3. Basic Usage

```bash
# Show current status
PYTHONPATH=. python3 -m cli status

# List available servers
PYTHONPATH=. python3 -m cli switch

# Switch to a server
PYTHONPATH=. python3 -m cli switch server_name

# List available models
PYTHONPATH=. python3 -m cli model list

# Switch to a model
PYTHONPATH=. python3 -m cli model switch model_name
```

## Commands

### Server Management

```bash
# Start the proxy server
PYTHONPATH=. python3 -m cli start

# Stop the proxy server
PYTHONPATH=. python3 -m cli stop

# Restart the proxy server
PYTHONPATH=. python3 -m cli restart

# Show real-time status with auto-refresh
PYTHONPATH=. python3 -m cli status --continuous

# Show current configuration
PYTHONPATH=. python3 -m cli config
```

### Server Switching

```bash
# List all servers with performance data
PYTHONPATH=. python3 -m cli servers

# Switch between servers (no restart required)
PYTHONPATH=. python3 -m cli switch [server_name]

# Monitor health of all endpoints
PYTHONPATH=. python3 -m cli health

# Discover multiple IP endpoints for a domain
PYTHONPATH=. python3 -m cli discover-endpoints open.bigmodel.cn
```

### IP Override Management

```bash
# List all IP overrides
PYTHONPATH=. python3 -m cli ip list

# Set an IP override for a server
PYTHONPATH=. python3 -m cli ip set server_name 192.168.1.100

# Remove an IP override
PYTHONPATH=. python3 -m cli ip remove server_name

# Enable/disable IP overrides globally
PYTHONPATH=. python3 -m cli ip enable true
PYTHONPATH=. python3 -m cli ip enable false

# Test connectivity to a server
PYTHONPATH=. python3 -m cli ip test server_name
```

### Model Management

```bash
# List all configured models
PYTHONPATH=. python3 -m cli model list

# Switch between models
PYTHONPATH=. python3 -m cli model switch [model_name]

# Add a new model
PYTHONPATH=. python3 -m cli model add glm-4.6 "GLM-4.6" glm-4.6 200000 200000

# Update token configuration
PYTHONPATH=. python3 -m cli model update_tokens glm-4.6 200000 200000

# Show detailed model information
PYTHONPATH=. python3 -m cli model info [model_name]

# Remove a model
PYTHONPATH=. python3 -m cli model remove model_name
```

### Context Testing

```bash
# Test context window limits
PYTHONPATH=. python3 -m cli test-context

# Quick test with fewer iterations
PYTHONPATH=. python3 -m cli test-context --quick

# Test specific model
PYTHONPATH=. python3 -m cli test-context --model glm-4.6

# Custom search range
PYTHONPATH=. python3 -m cli test-context --start 32768 --max-limit 200000
```

### Auto-completion

```bash
# Generate completion script
PYTHONPATH=. python3 -m cli completion bash   # or zsh, fish

# Install auto-completion automatically
./setup.sh install

# Manual installation
PYTHONPATH=. python3 -m cli completion bash --install
```

## Configuration

The CLI uses a `config.yaml` file for configuration. Key settings include:

- **Servers**: Configure multiple server endpoints with regions
- **Models**: Define AI models with token configurations
- **IP Overrides**: Override server IPs for testing
- **Logging**: Configure log levels and output

### Example Configuration

```yaml
servers:
  cn:
    region: "China"
    endpoint: "https://cn.example.com"
    api_key: "your_api_key"
  inter:
    region: "International"
    endpoint: "https://api.example.com"
    api_key: "your_api_key"

models:
  glm-4.6:
    display_name: "GLM-4.6"
    text_model_name: "glm-4.6"
    openai_expected_tokens: 200000
    real_text_model_tokens: 200000
    description: "Latest GLM model"

ip_overrides:
  enabled: true
  overrides:
    cn: "192.168.1.100"

current_server: "cn"
current_model: "glm-4.6"
```

## Auto-completion

The CLI provides comprehensive auto-completion for:

- Commands and subcommands
- Server names
- Model names
- Command options
- File paths

### Setup Auto-completion

```bash
# Bash
./setup.sh install
source ~/.bashrc

# Zsh
PYTHONPATH=. python3 -m cli completion zsh --install
source ~/.zshrc

# Fish
PYTHONPATH=. python3 -m cli completion fish --install
```

### Using Auto-completion

```bash
# Tab completion for commands
PYTHONPATH=. python3 -m cli <TAB>

# Tab completion for servers
PYTHONPATH=. python3 -m cli switch <TAB>

# Tab completion for models
PYTHONPATH=. python3 -m cli model switch <TAB>

# Tab completion for options
PYTHONPATH=. python3 -m cli test-context --<TAB>
```

## Advanced Features

### Context Window Discovery

The CLI includes a sophisticated context window discovery tool that:

- Uses binary search to find exact token limits
- Tests with actual API requests
- Provides detailed performance metrics
- Automatically updates model configurations

```bash
# Full context discovery
PYTHONPATH=. python3 -m cli test-context

# Quick test for verification
PYTHONPATH=. python3 -m cli test-context --quick
```

### Endpoint Discovery

Discover multiple IP endpoints for any domain:

```bash
# Discover endpoints for a domain
PYTHONPATH=. python3 -m cli discover-endpoints open.bigmodel.cn

# Limit number of nodes to query
PYTHONPATH=. python3 -m cli discover-endpoints open.bigmodel.cn --max-nodes 10
```

### Performance Monitoring

Real-time monitoring with automatic refresh:

```bash
# Continuous status monitoring
PYTHONPATH=. python3 -m cli status --continuous --interval 5

# Health monitoring
PYTHONPATH=. python3 -m cli health --interval 30
```

## Troubleshooting

### Common Issues

1. **Module not found errors**
   ```bash
   export PYTHONPATH=.
   pip install --break-system-packages httpx click pyyaml requests rich aiofiles
   ```

2. **Auto-completion not working**
   ```bash
   # Reinstall completion
   ./setup.sh install
   source ~/.bashrc
   ```

3. **Permission denied errors**
   ```bash
   # Use user directory for completion
   ./setup.sh install
   ```

### Debug Mode

Enable debug logging:

```bash
# Set log level in config.yaml
log_level: "DEBUG"

# Or use environment variable
export ANTHROPIC_PROXY_LOG_LEVEL=DEBUG
```

## Development

### Project Structure

```
cli/
├── __main__.py      # Module entry point
├── main.py          # Main CLI commands
├── config.py        # Configuration management
├── proxy.py         # Proxy server management
├── stats.py         # Statistics collection
└── utils.py         # Utility functions
```

### Adding New Commands

1. Add command function to `cli/main.py`
2. Use `@cli.command()` decorator
3. Add arguments with `@click.argument()`
4. Add options with `@click.option()`

Example:
```python
@cli.command()
@click.argument('name')
@click.option('--verbose', '-v', is_flag=True)
def hello(name: str, verbose: bool):
    """Say hello to someone"""
    if verbose:
        console.print(f"[bold]Hello, {name}![/bold]")
    else:
        console.print(f"Hello, {name}!")
```

## License

This project is licensed under the MIT License.