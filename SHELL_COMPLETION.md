# Shell Auto-Completion for Anthropic Proxy CLI

This guide explains how to set up and use shell auto-completion for the Anthropic Proxy CLI.

## Supported Shells

- **Bash** - Complete support with dynamic completion for servers and models
- **Zsh** - Advanced completion with descriptions and context-aware suggestions
- **Fish** - Modern completion with automatic descriptions

## Quick Installation

### Automated Installation (Recommended)

Run the installation script which will automatically detect your shell and install completion:

```bash
./install_completion.sh
```

### Manual Installation

#### Bash Completion

```bash
# Generate and install bash completion
./venv/bin/python -m cli completion bash --install

# Or manually add to ~/.bashrc:
./venv/bin/python -m cli completion bash >> ~/.bashrc
source ~/.bashrc
```

#### Zsh Completion

```bash
# Generate and install zsh completion
./venv/bin/python -m cli completion zsh --install

# Or manually add to ~/.zshrc:
./venv/bin/python -m cli completion zsh >> ~/.zshrc
source ~/.zshrc
```

#### Fish Completion

```bash
# Generate and install fish completion
./venv/bin/python -m cli completion fish --install

# Fish completion will be automatically loaded from ~/.config/fish/completions/
```

## Usage Examples

Once completion is installed, you can use tab completion:

### Basic Command Completion

```bash
./venv/bin/python <TAB>
# Shows: start stop restart status switch servers health tui config discover_endpoints test_context ip model completion

./venv/bin/python st<TAB>
# Completes to: start status

./venv/bin/python model <TAB>
# Shows: list switch add remove update_tokens info
```

### Dynamic Server Completion

```bash
./venv/bin/python ip set <TAB>
# Shows available servers: cn inter

./venv/bin/python switch <TAB>
# Shows available servers: cn inter
```

### Dynamic Model Completion

```bash
./venv/bin/python model switch <TAB>
# Shows available models: glm-4.6 glm-4.6-plus gpt-4o gpt-4o-mini

./venv/bin/python test-context --model <TAB>
# Shows available models: glm-4.6 glm-4.6-plus gpt-4o gpt-4o-mini
```

### Option Completion

```bash
./venv/bin/python test-context <TAB>
# Shows: --help --start --max-limit --quick --model

./venv/bin/python test-context --model <TAB>
# Shows available models
```

## Completion Features

### Smart Context-Aware Completion

- **Server Names**: Completes server names for IP and server commands
- **Model Names**: Completes model names for model-related commands
- **Options**: Completes command-specific options
- **Subcommands**: Completes appropriate subcommands for each command group

### Dynamic Data Integration

The completion system integrates with your actual configuration:

- **Live Server List**: Shows servers from your current `config.yaml`
- **Live Model List**: Shows models from your current configuration
- **Real-time Updates**: Completion updates immediately when you add/remove servers or models

### Command Groups

#### IP Override Commands
- `ip list` - List IP overrides
- `ip set <server>` - Set IP override for server
- `ip remove <server>` - Remove IP override
- `ip enable <true|false>` - Enable/disable IP overrides
- `ip test <server>` - Test server connectivity

#### Model Management Commands
- `model list` - List all models
- `model switch <model>` - Switch to model
- `model add <params>` - Add new model
- `model remove <model>` - Remove model
- `model update_tokens <model>` - Update token configuration
- `model info <model>` - Show model information

#### Testing Commands
- `test-context --model <model>` - Test context for specific model
- `test-context --quick` - Quick test with fewer iterations
- `test-context --start <tokens>` - Custom starting point
- `test-context --max-limit <tokens>` - Custom maximum limit

## Troubleshooting

### Completion Not Working

1. **Restart your terminal** after installing completion
2. **Check shell detection**: `echo $SHELL`
3. **Verify installation**: Run the installation script again
4. **Manual installation**: Use manual commands if automated installation fails

### Bash Issues

```bash
# Check if bash completion is installed
type _init_completion

# Install bash completion if needed (Ubuntu/Debian)
sudo apt-get install bash-completion

# Source bash completion
source /usr/share/bash-completion/bash_completion
```

### Zsh Issues

```bash
# Check if zsh completion is working
autoload -U compinit && compinit

# Add to ~/.zshrc if not present
echo 'autoload -U compinit && compinit' >> ~/.zshrc
```

### Fish Issues

```bash
# Check fish completion directory
ls ~/.config/fish/completions/

# Fish should automatically load completions
```

## Advanced Usage

### Custom Completion Scripts

You can create custom completion scripts by modifying the generated completion functions:

```bash
# Edit bash completion
vim ~/.bashrc

# Edit zsh completion  
vim ~/.zshrc

# Edit fish completion
vim ~/.config/fish/completions/anthropic-proxy-cli.fish
```

### Multiple Python Environments

If you use multiple Python environments, you may need to register completion for each:

```bash
# Register completion for different Python executables
complete -F _anthropic_proxy_cli_completion python3
complete -F _anthropic_proxy_cli_completion ./other-venv/bin/python
```

## Development

### Adding New Completion

To add completion for new commands:

1. Add the command to the main command list in completion scripts
2. Add appropriate completion logic for the command's arguments
3. Test with: `./venv/bin/python -m cli completion <shell>`

### Testing Completion

```bash
# Test bash completion
complete -p python

# Test zsh completion
echo $commands[(i)anthropic_proxy_cli]

# Test fish completion
complete -C python
```

## Support

If you encounter issues with shell completion:

1. Check this documentation first
2. Try manual installation
3. Verify your shell version supports completion
4. Check for conflicting completion scripts
5. Open an issue with your shell type and error details