#!/usr/bin/env python3
"""
Shell completion script for Anthropic Proxy CLI
"""

import click
from .main import cli

@click.command()
@click.argument('shell', type=click.Choice(['bash', 'zsh', 'fish']))
def install_completion(shell: str):
    """Install shell completion for the CLI"""
    
    completion_scripts = {
        'bash': '''
# Anthropic Proxy CLI Bash completion
_anthropic_proxy_cli_completion() {
    local cur prev words cword
    _init_completion || return

    case $prev in
        --model|-M)
            # Complete model names
            COMPREPLY=($(compgen -W "$(python -m cli model list 2>/dev/null | grep -E '^\s+→\s+\w+' | awk '{print $2}' | tr -d '→')" -- "$cur"))
            return
            ;;
        --server)
            # Complete server names
            COMPREPLY=($(compgen -W "$(python -m cli switch 2>/dev/null | grep -E '^\s+•\s+\w+' | awk '{print $2}' | tr -d '•')" -- "$cur"))
            return
            ;;
        ip)
            COMPREPLY=($(compgen -W "list set remove enable test" -- "$cur"))
            return
            ;;
        model)
            COMPREPLY=($(compgen -W "list switch add remove update_tokens info" -- "$cur"))
            return
            ;;
        set|remove|test)
            # Complete server names for IP commands
            COMPREPLY=($(compgen -W "$(python -m cli switch 2>/dev/null | grep -E '^\s+•\s+\w+' | awk '{print $2}' | tr -d '•')" -- "$cur"))
            return
            ;;
        switch|remove|info)
            # Complete model names for model commands
            COMPREPLY=($(compgen -W "$(python -m cli model list 2>/dev/null | grep -E '^\s+→\s+\w+|^\s+\w+' | awk '{print $2}' | tr -d '→')" -- "$cur"))
            return
            ;;
        update_tokens|remove)
            # Complete model names for model commands
            COMPREPLY=($(compgen -W "$(python -m cli model list 2>/dev/null | grep -E '^\s+→\s+\w+|^\s+\w+' | awk '{print $2}' | tr -d '→')" -- "$cur"))
            return
            ;;
        *)
            ;;
    esac

    # Main command completion
    if [[ $cur == -* ]]; then
        COMPREPLY=($(compgen -W "--help --version" -- "$cur"))
    else
        COMPREPLY=($(compgen -W "start stop restart status switch servers health tui config discover_endpoints test_context ip model" -- "$cur"))
    fi
}

complete -F _anthropic_proxy_cli_completion python
complete -F _anthropic_proxy_cli_completion ./venv/bin/python
''',
        
        'zsh': '''
#compdef _anthropic_proxy_cli python
_anthropic_proxy_cli() {
    local -a commands
    commands=(
        'start:Start the proxy server'
        'stop:Stop the proxy server'
        'restart:Restart the proxy server'
        'status:Show proxy status with auto-refresh'
        'switch:Switch between servers'
        'servers:List all configured servers'
        'health:Monitor health of all endpoints'
        'tui:Launch Terminal User Interface'
        'config:Show current configuration'
        'discover_endpoints:Discover multiple IP endpoints'
        'test_context:Test context window limits'
        'ip:Manage IP overrides'
        'model:Manage AI model configurations'
    )

    local -a ip_commands
    ip_commands=(
        'list:List all configured IP overrides'
        'set:Set an IP override for a specific server'
        'remove:Remove an IP override'
        'enable:Enable or disable IP overrides globally'
        'test:Test connectivity to a server'
    )

    local -a model_commands
    model_commands=(
        'list:List all configured models'
        'switch:Switch between models'
        'add:Add a new model configuration'
        'remove:Remove a model configuration'
        'update_tokens:Update token configuration'
        'info:Show detailed information about a model'
    )

    local context state line
    _arguments -C \\
        '1: :->command' \\
        '*:: :->args' \\
        && return

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $line[1] in
                ip)
                    _arguments '1: :->ip_command' '*:: :->ip_args' && return
                    ;;
                model)
                    _arguments '1: :->model_command' '*:: :->model_args' && return
                    ;;
            esac
            ;;
        ip_command)
            _describe 'ip command' ip_commands
            ;;
        model_command)
            _describe 'model command' model_commands
            ;;
        ip_args)
            case $line[2] in
                set|remove|test)
                    _arguments '1:server name:_servers' && return
                    ;;
                enable)
                    _arguments '1:enabled:(true false)' && return
                    ;;
            esac
            ;;
        model_args)
            case $line[2] in
                switch|remove|info|update_tokens)
                    _arguments '1:model name:_models' && return
                    ;;
            esac
            ;;
    esac
}

_servers() {
    local -a servers
    servers=($(python -m cli switch 2>/dev/null | grep -E '^\s+•\s+\w+' | awk '{print $2}' | tr -d '•'))
    _describe 'servers' servers
}

_models() {
    local -a models
    models=($(python -m cli model list 2>/dev/null | grep -E '^\s+→\s+\w+|^\s+\w+' | awk '{print $2}' | tr -d '→'))
    _describe 'models' models
}
''',
        
        'fish': '''
# Anthropic Proxy CLI Fish completion
function __fish_anthropic_proxy_cli_no_subcommand
    for i in (commandline -opc)
        if contains -- $i start stop restart status switch servers health tui config discover_endpoints test_context ip model
            return 1
        end
    end
    return 0
end

function __fish_anthropic_proxy_cli_servers
    python -m cli switch 2>/dev/null | grep -E '^\s+•\s+\w+' | awk '{print $2}' | tr -d '•'
end

function __fish_anthropic_proxy_cli_models
    python -m cli model list 2>/dev/null | grep -E '^\s+→\s+\w+|^\s+\w+' | awk '{print $2}' | tr -d '→'
end

complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -f
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a start -d 'Start the proxy server'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a stop -d 'Stop the proxy server'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a restart -d 'Restart the proxy server'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a status -d 'Show proxy status'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a switch -d 'Switch between servers' -a '(__fish_anthropic_proxy_cli_servers)'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a servers -d 'List all configured servers'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a health -d 'Monitor health of endpoints'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a tui -d 'Launch Terminal User Interface'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a config -d 'Show current configuration'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a discover_endpoints -d 'Discover IP endpoints'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a test_context -d 'Test context window limits'

# IP commands
complete -c python -n '__fish_seen_subcommand_from_options ip' -a list -d 'List IP overrides'
complete -c python -n '__fish_seen_subcommand_from_options ip' -a set -d 'Set IP override' -a '(__fish_anthropic_proxy_cli_servers)'
complete -c python -n '__fish_seen_subcommand_from_options ip' -a remove -d 'Remove IP override' -a '(__fish_anthropic_proxy_cli_servers)'
complete -c python -n '__fish_seen_subcommand_from_options ip' -a enable -d 'Enable/disable IP overrides' -a '(true false)'
complete -c python -n '__fish_seen_subcommand_from_options ip' -a test -d 'Test server connectivity' -a '(__fish_anthropic_proxy_cli_servers)'

# Model commands
complete -c python -n '__fish_seen_subcommand_from_options model' -a list -d 'List models'
complete -c python -n '__fish_seen_subcommand_from_options model' -a switch -d 'Switch models' -a '(__fish_anthropic_proxy_cli_models)'
complete -c python -n '__fish_seen_subcommand_from_options model' -a remove -d 'Remove model' -a '(__fish_anthropic_proxy_cli_models)'
complete -c python -n '__fish_seen_subcommand_from_options model' -a info -d 'Show model info' -a '(__fish_anthropic_proxy_cli_models)'
complete -c python -n '__fish_seen_subcommand_from_options model' -a update_tokens -d 'Update model tokens' -a '(__fish_anthropic_proxy_cli_models)'
complete -c python -n '__fish_seen_subcommand_from_options model' -a add -d 'Add new model'

# Options
complete -c python -l s -d 'Start token count' -n '__fish_seen_subcommand_from_options test_context'
complete -c python -l m -d 'Max token limit' -n '__fish_seen_subcommand_from_options test_context'
complete -c python -l q -d 'Quick test' -n '__fish_seen_subcommand_from_options test_context'
complete -c python -l M -d 'Model to test' -n '__fish_seen_subcommand_from_options test_context' -a '(__fish_anthropic_proxy_cli_models)'
complete -c python -l c -d 'Continuous refresh' -n '__fish_seen_subcommand_from_options status'
complete -c python -l i -d 'Refresh interval' -n '__fish_seen_subcommand_from_options status health'
complete -c python -l n -d 'Max nodes' -n '__fish_seen_subcommand_from_options discover_endpoints'
complete -c python -l d -d 'Description' -n '__fish_seen_subcommand_from_options model add'
'''
    }
    
    if shell not in completion_scripts:
        click.echo(f"Shell '{shell}' not supported. Supported shells: bash, zsh, fish")
        return
    
    click.echo(f"To install {shell} completion, add the following to your {shell} configuration:")
    click.echo()
    click.echo(completion_scripts[shell])

if __name__ == '__main__':
    install_completion()