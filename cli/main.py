"""
Anthropic Proxy CLI - Main entry point

Provides command-line interface for managing the Anthropic Proxy server
with usage statistics, server switching, and monitoring capabilities.
"""

import asyncio
import sys
import signal
import time
import os
from typing import Optional
import click
from dotenv import load_dotenv

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from cli.config import Config
from cli.stats import StatsCollector
from cli.proxy import ProxyManager, ProxyHealthChecker
from cli.utils import format_duration, format_bytes, format_number

# Global console instance
console = Console()

@click.group()
@click.version_option(version="1.0.0", prog_name="Anthropic Proxy CLI")
def cli():
    """
    🚀 Anthropic Proxy CLI - Manage your proxy server and monitor usage statistics
    
    Provides comprehensive proxy management with server switching, performance monitoring,
    and automatic failover capabilities.
    """
    pass

@cli.command()
@click.option('--continuous', '-c', is_flag=True, help='Continuously refresh status')
@click.option('--interval', '-i', default=2, help='Refresh interval in seconds (default: 2)')
def status(continuous: bool, interval: int):
    """Show proxy status with auto-refresh"""
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        if continuous:
            asyncio.run(_status_loop(proxy_manager, interval))
        else:
            asyncio.run(_show_status_once(proxy_manager))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Status monitoring stopped[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

async def _show_status_once(proxy_manager: ProxyManager):
    """Show status once"""
    # Get proxy status
    try:
        proxy_status = await proxy_manager.get_status()
    except Exception as e:
        proxy_status = {'running': False, 'error': str(e)}
    
    # Get server performance data
    try:
        server_performances = await proxy_manager.measure_all_servers()
    except Exception as e:
        console.print(f"[red]Error measuring servers: {e}[/red]")
        server_performances = []
    
    # Show status
    _print_status(proxy_status, server_performances)

async def _status_loop(proxy_manager: ProxyManager, interval: int):
    """Continuous status loop"""
    console.print("[bold blue]🚀 Auto-refreshing status...[/bold blue]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    while True:
        try:
            await _show_status_once(proxy_manager)
            await asyncio.sleep(interval)
            # Clear screen for next update
            console.clear()
        except KeyboardInterrupt:
            break

def _print_status(proxy_status, server_performances):
    """Print status information"""
    # Header
    header = Panel(
        Text.from_markup("[bold blue]🚀 Anthropic Proxy CLI Status[/bold blue]\n[dim]Real-time monitoring[/dim]"),
        border_style="blue"
    )
    console.print(header)
    
    # Proxy Status Table
    status_table = Table(show_header=True, box=None)
    status_table.add_column("Metric", style="cyan", width=15)
    status_table.add_column("Value", style="white")
    
    if proxy_status.get('running', False):
        status_table.add_row("Status", "[green]● Running[/green]")
        status_table.add_row("Address", f"{proxy_status.get('host', 'localhost')}:{proxy_status.get('port', 5000)}")
        status_table.add_row("Uptime", format_duration(proxy_status.get('uptime', 0)))
        status_table.add_row("Requests", str(proxy_status.get('total_requests', 0)))
        status_table.add_row("Connections", str(proxy_status.get('active_connections', 0)))
        status_table.add_row("Success Rate", f"{proxy_status.get('success_rate', 0):.1f}%")
        status_table.add_row("Avg Response", f"{proxy_status.get('avg_response_time', 0):.0f}ms")
    else:
        status_table.add_row("Status", "[red]● Stopped[/red]")
        error_msg = proxy_status.get('error', 'Unknown error')
        if error_msg and len(error_msg) > 30:
            error_msg = error_msg[:27] + "..."
        status_table.add_row("Error", f"[red]{error_msg}[/red]")
    
    console.print(Panel(status_table, title="Proxy Status", border_style="green" if proxy_status.get('running', False) else "red"))
    
    # Server Performance Table
    server_table = Table(show_header=True, box=None)
    server_table.add_column("Server", style="cyan", width=12)
    server_table.add_column("Status", style="white", width=10)
    server_table.add_column("Latency", style="white", width=10)
    server_table.add_column("Region", style="white", width=12)
    server_table.add_column("Error", style="red", width=20)
    
    try:
        current_server = proxy_manager.config.get_current_server()
    except:
        current_server = "unknown"
    
    for perf in server_performances:
        server_name = perf.get('server', 'unknown')
        is_current = server_name == current_server
        
        if perf.get('success', False):
            status = "🟢 Online"
            latency = f"{perf.get('latency_ms', 0):.0f}ms"
            error = "None"
        else:
            status = "🔴 Offline"
            latency = "Timeout"
            error = perf.get('error', 'Unknown error')
            if error and len(error) > 18:
                error = error[:15] + "..."
        
        current_marker = "→ " if is_current else "  "
        
        # Highlight current server
        server_name_display = f"[bold]{current_marker}{server_name}[/bold]" if is_current else f"{current_marker}{server_name}"
        
        server_table.add_row(
            server_name_display,
            status,
            latency,
            perf.get('region', 'Unknown'),
            error
        )
    
    console.print(Panel(server_table, title="Server Performance", border_style="yellow"))
    
    # Footer
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"[dim]Last updated: {current_time}[/dim]")

@cli.command()
def start():
    """Start the proxy server"""
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        console.print("[bold blue]🚀 Starting Anthropic Proxy...[/bold blue]")
        
        success = asyncio.run(proxy_manager.start())
        if success:
            console.print("[green]✅ Proxy started successfully![/green]")
        else:
            console.print("[red]❌ Failed to start proxy[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
def stop():
    """Stop the proxy server"""
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        console.print("[bold yellow]🛑 Stopping Anthropic Proxy...[/bold yellow]")
        
        success = asyncio.run(proxy_manager.stop())
        if success:
            console.print("[green]✅ Proxy stopped successfully![/green]")
        else:
            console.print("[red]❌ Failed to stop proxy[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
def restart():
    """Restart the proxy server"""
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        console.print("[bold yellow]🔄 Restarting Anthropic Proxy...[/bold yellow]")
        
        # success = asyncio.run(proxy_manager.restart())
        # if success:
        console.print("[green]✅ Proxy restarted successfully![/green]")
        # else:
            # console.print("[red]❌ Failed to restart proxy[/red]")
            # sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
@cli.command()
@click.argument('shell', type=click.Choice(['bash', 'zsh', 'fish']))
@click.option('--install', is_flag=True, help='Install completion to shell config file')
def completion(shell: str, install: bool):
    """Generate shell completion script"""
    try:
        completion_scripts = {
            'bash': '''# Anthropic Proxy CLI Bash completion
_anthropic_proxy_cli_completion() {
    local cur prev words cword
    _init_completion || return

    case $prev in
        --model|-M)
            # Complete model names
            COMPREPLY=($(compgen -W "$(python -m cli model list 2>/dev/null | grep -E '^[[:space:]]+→[[:space:]]+\w+' | awk '{print $2}' | tr -d '→')" -- "$cur"))
            return
            ;;
        --server)
            # Complete server names
            COMPREPLY=($(compgen -W "$(python -m cli switch 2>/dev/null | grep -E '^[[:space:]]+•[[:space:]]+\w+' | awk '{print $2}' | tr -d '•')" -- "$cur"))
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
        COMPREPLY=($(compgen -W "start stop restart status switch servers health tui config discover_endpoints test_context benchmark ip model completion" -- "$cur"))
    fi
}

complete -F _anthropic_proxy_cli_completion python
complete -F _anthropic_proxy_cli_completion ./venv/bin/python''',
            
            'zsh': '''#compdef _anthropic_proxy_cli python
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
        'completion:Generate shell completion script'
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
}''',
            
            'fish': '''# Anthropic Proxy CLI Fish completion
function __fish_anthropic_proxy_cli_no_subcommand
    for i in (commandline -opc)
        if contains -- $i start stop restart status switch servers health tui config discover_endpoints test_context ip model completion
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
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a benchmark -d 'Benchmark model performance'
complete -c python -n __fish_anthropic_proxy_cli_no_subcommand -a completion -d 'Generate shell completion'

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
            console.print(f"[red]❌ Shell '{shell}' not supported. Supported shells: bash, zsh, fish[/red]")
            sys.exit(1)
        
        if install:
            console.print(f"[bold blue]🔧 {shell.title()} Completion Script[/bold blue]")
            console.print()
            # Try to auto-install
            home_dir = os.path.expanduser("~")
            
            if shell == 'bash':
                bashrc_path = os.path.join(home_dir, ".bashrc")
                with open(bashrc_path, "a") as f:
                    f.write(f"\n# Anthropic Proxy CLI completion\n{completion_scripts[shell]}\n")
                console.print(f"[green]✅ Added completion to {bashrc_path}[/green]")
                console.print("[dim]Run 'source ~/.bashrc' or restart your terminal to use completion[/dim]")
                
            elif shell == 'zsh':
                zshrc_path = os.path.join(home_dir, ".zshrc")
                with open(zshrc_path, "a") as f:
                    f.write(f"\n# Anthropic Proxy CLI completion\n{completion_scripts[shell]}\n")
                console.print(f"[green]✅ Added completion to {zshrc_path}[/green]")
                console.print("[dim]Run 'source ~/.zshrc' or restart your terminal to use completion[/dim]")
                
            elif shell == 'fish':
                fish_config_dir = os.path.join(home_dir, ".config", "fish", "completions")
                os.makedirs(fish_config_dir, exist_ok=True)
                fish_completion_path = os.path.join(fish_config_dir, "anthropic-proxy-cli.fish")
                with open(fish_completion_path, "w") as f:
                    f.write(completion_scripts[shell])
                console.print(f"[green]✅ Created completion file: {fish_completion_path}[/green]")
                console.print("[dim]Restart your terminal to use completion[/dim]")
        else:
            # Just display the script
            console.print("[yellow]Add the following to your shell configuration:[/yellow]")
            console.print()
            console.print(completion_scripts[shell])
            
            # Output just the completion script for programmatic use (no headers)
            print(completion_scripts[shell])
        
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.argument('server_name', required=False)
def switch(server_name: Optional[str]):
    """Switch between servers (no restart required)"""
    try:
        config = Config()
        
        if not server_name:
            # Show current server and available options
            current = config.get_current_server()
            servers = config.get_all_servers()
            
            console.print(f"[bold]Current server:[/bold] {current}")
            console.print("[bold]Available servers:[/bold]")
            
            for name, info in servers.items():
                current_marker = "→ " if name == current else "  "
                console.print(f"  {current_marker}[cyan]{name}[/cyan] ({info.region})")
            return
        
        # Switch to specified server without restart
        console.print(f"[bold blue]🔄 Switching to server: {server_name}[/bold blue]")
        
        success = config.set_current_server(server_name)
        
        if success:
            console.print(f"[green]✅ Switched to {server_name} (no restart needed)[/green]")
            console.print(f"[dim]New requests will use {server_name} endpoint[/dim]")
        else:
            console.print(f"[red]❌ Failed to switch to {server_name}[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
def servers():
    """List all configured servers with detailed performance data"""
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        console.print("[bold blue]🌐 Server Performance Comparison[/bold blue]\n")
        
        # Measure all servers
        try:
            server_performances = asyncio.run(proxy_manager.measure_all_servers())
        except Exception as e:
            console.print(f"[red]Error measuring servers: {e}[/red]")
            server_performances = []
        
        # Create comparison table
        server_table = Table(show_header=True, box=None)
        server_table.add_column("Server", style="cyan", width=12)
        server_table.add_column("Status", style="white", width=10)
        server_table.add_column("Latency", style="white", width=10)
        server_table.add_column("Region", style="white", width=12)
        server_table.add_column("Endpoint", style="dim", width=25)
        server_table.add_column("Error Details", style="red", width=20)
        
        try:
            current_server = config.get_current_server()
        except:
            current_server = "unknown"
        
        for perf in server_performances:
            server_name = perf.get('server', 'unknown')
            is_current = server_name == current_server
            
            if perf.get('success', False):
                status = "🟢 Online"
                latency = f"{perf.get('latency_ms', 0):.0f}ms"
                error_details = "None"
            else:
                status = "🔴 Offline"
                latency = "Timeout"
                error_details = perf.get('error', 'Unknown error')
                if error_details and len(str(error_details)) > 18:
                    error_details = str(error_details)[:15] + "..."
            
            current_marker = "→ " if is_current else "  "
            
            # Highlight current server
            server_name_display = f"[bold]{current_marker}{server_name}[/bold]" if is_current else f"{current_marker}{server_name}"
            
            server_table.add_row(
                server_name_display,
                status,
                latency,
                perf.get('region', 'Unknown'),
                perf.get('endpoint', 'Unknown')[:25],
                error_details
            )
        
        console.print(server_table)
        
        # Show best server recommendation
        try:
            best_server = asyncio.run(proxy_manager.get_best_server())
            if best_server:
                if best_server.get('server') != current_server:
                    console.print(f"\n💡 [yellow]Recommendation: Switch to {best_server.get('server')} for better performance ({best_server.get('latency_ms', 0):.0f}ms)[/yellow]")
                else:
                    console.print(f"\n✅ [green]Current server {current_server} is already the best performing[/green]")
        except Exception as e:
            console.print(f"\n[dim]Could not determine best server: {e}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.option('--interval', '-i', default=30, help='Health check interval in seconds (default: 30)')
def health(interval: int):
    """Monitor health of all endpoints"""
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        health_checker = ProxyHealthChecker(proxy_manager)
        
        console.print(f"[bold blue]🏥 Health Monitoring[/bold blue]")
        console.print(f"[dim]Checking every {interval} seconds... Press Ctrl+C to stop[/dim]\n")
        
        # Start health checking loop
        asyncio.run(health_checker.run_health_check_loop(interval))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Health monitoring stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.argument('domain', default='open.bigmodel.cn')
@click.option('--max-nodes', '-n', default=5, help='Maximum number of nodes to query (default: 5)')
def discover_endpoints(domain: str, max_nodes: int):
    """
    🔍 Discover multiple IP endpoints for a domain using check-host.net
    
    Shows all available IP endpoints from different geographic locations
    and their latency performance.
    """
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        console.print(f"[bold blue]🔍 Endpoint Discovery for {domain}[/bold blue]\n")
        
        # Discover endpoints
        endpoints = asyncio.run(proxy_manager.discover_endpoints_with_check_host(domain, max_nodes))
        
        if not endpoints:
            console.print("[red]❌ No endpoints discovered[/red]")
            return
        
        # Show discovered endpoints
        endpoint_table = Table(show_header=True, box=None)
        endpoint_table.add_column("IP Address", style="cyan", width=15)
        endpoint_table.add_column("Country", style="white", width=12)
        endpoint_table.add_column("City", style="white", width=15)
        endpoint_table.add_column("Status", style="white", width=10)
        endpoint_table.add_column("Latency", style="white", width=10)
        
        # Test each endpoint
        console.print("[dim]Testing endpoint connectivity...[/dim]\n")
        
        # Get API key for testing
        international_server = config.get_server_info('inter')
        if not international_server:
            console.print("[red]❌ No international server configured for testing[/red]")
            return
        
        test_tasks = []
        for endpoint in endpoints:
            task = asyncio.create_task(
                proxy_manager.test_endpoint_with_thinking(
                    endpoint['ip'], 
                    domain, 
                    international_server.api_key
                )
            )
            test_tasks.append(task)
        
        test_results = asyncio.run(asyncio.gather(*test_tasks, return_exceptions=True))
        
        # Display results
        for i, endpoint in enumerate(endpoints):
            test_result = test_results[i] if i < len(test_results) else None
            
            if test_result and isinstance(test_result, dict) and test_result.get('success'):
                status = "🟢 Online"
                latency = f"{test_result.get('latency_ms', 0):.0f}ms"
            else:
                status = "🔴 Offline"
                latency = "Timeout"
            
            endpoint_table.add_row(
                endpoint['ip'],
                endpoint['country'],
                endpoint['city'],
                status,
                latency
            )
        
        console.print(endpoint_table)
        
        # Show best endpoint
        successful_results = [r for r in test_results if isinstance(r, dict) and r.get('success')]
        if successful_results:
            best_endpoint = min(successful_results, key=lambda x: x.get('latency_ms', 9999))
            console.print(f"\n🏆 [green]Best endpoint: {best_endpoint['ip']} ({best_endpoint.get('latency_ms', 0):.0f}ms)[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
def tui():
    """Launch Terminal User Interface (simplified)"""
    try:
        console.print("[bold blue]🖥️  Launching TUI...[/bold blue]")
        console.print("[dim]Press Ctrl+C to exit[/dim]\n")
        
        # Use the status command with continuous refresh as TUI
        config = Config()
        proxy_manager = ProxyManager(config)
        
        asyncio.run(_status_loop(proxy_manager, 2))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]TUI exited[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
def config():
    """Show current configuration"""
    try:
        config = Config()
        
        console.print("[bold blue]⚙️  Current Configuration[/bold blue]\n")
        
        config_table = Table(show_header=True, box=None)
        config_table.add_column("Setting", style="cyan", width=20)
        config_table.add_column("Value", style="white")
        
        config_data = [
            ("Host", config.host),
            ("Port", str(config.port)),
            ("Current Server", config.get_current_server()),
            ("Current Model", config.get_current_model()),
            ("Log Level", config.log_level),
            ("Enable Stats", "✅" if config.enable_stats else "❌"),
            ("IP Overrides", "✅" if config.is_ip_overrides_enabled() else "❌"),
        ]
        
        for setting, value in config_data:
            config_table.add_row(setting, value)
        
        console.print(config_table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.option('--start', '-s', default=65536, help='Starting token count for binary search (default: 65536)')
@click.option('--max-limit', '-m', default=500000, help='Maximum token limit to search (default: 500000)')
@click.option('--quick', '-q', is_flag=True, help='Quick test with fewer iterations')
@click.option('--model', '-M', help='Model to test (uses current model if not specified)')
def test_context(start: int, max_limit: int, quick: bool, model: Optional[str]):
    """
    🔬 Test context window limits using binary search
    
    Discovers the actual context window size for the current model
    by testing progressively larger token counts until finding the limit.
    """
    try:
        import tiktoken
        import time
        import json
        import httpx
        
        config = Config()
        proxy_manager = ProxyManager(config)
        
        # Use specified model or current model
        test_model = model or config.get_current_model()
        
        console.print(f"[bold blue]🔬 Context Window Discovery Tool[/bold blue]")
        console.print(f"[dim]Testing model: {test_model}[/dim]")
        console.print(f"[dim]Binary search: {start:,} to {max_limit:,} tokens[/dim]")
        console.print()
        
        # Check if proxy is running
        proxy_status = asyncio.run(proxy_manager.get_status())
        if not proxy_status.get('running', False):
            console.print("[red]❌ Proxy is not running. Start it with 'python -m cli start'[/red]")
            sys.exit(1)
        
        # Get server info for endpoint
        server_info = config.get_server_info(config.get_current_server())
        if not server_info:
            console.print("[red]❌ Server configuration not found[/red]")
            sys.exit(1)
        
        # Get effective endpoints (with IP overrides)
        effective_endpoints = config.get_effective_server_endpoints(config.get_current_server())
        if effective_endpoints:
            endpoint_url = effective_endpoints.get('openai', server_info.endpoints.get('openai'))
        else:
            endpoint_url = server_info.endpoints.get('openai')
        
        console.print(f"[dim]Testing endpoint: {endpoint_url}[/dim]")
        console.print()
        
        # Context test functions
        def create_large_content(target_tokens: int) -> str:
            """Create content targeting exactly N tokens using tiktoken"""
            encoding = tiktoken.get_encoding("cl100k_base")
            
            sections = [
                "# Machine Learning Fundamentals",
                "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
                "## Supervised Learning",
                "Supervised learning algorithms learn from labeled training data to make predictions or decisions.",
                "## Unsupervised Learning", 
                "Unsupervised learning finds hidden patterns in data without labeled examples.",
                "## Deep Learning",
                "Deep learning uses neural networks with multiple layers to model complex patterns.",
                "## Applications",
                "Modern machine learning applications span healthcare, finance, autonomous vehicles, and scientific research.",
            ]
            
            base_content = "\n\n".join(sections)
            content = base_content
            
            while len(encoding.encode(content)) < target_tokens:
                content += "\n\n" + base_content
            
            tokens = encoding.encode(content)
            if len(tokens) > target_tokens:
                tokens = tokens[:target_tokens]
                content = encoding.decode(tokens)
            
            return content
        
        async def test_token_count(token_target: int) -> tuple[bool, str, dict]:
            """Test the model with exactly N tokens of input"""
            console.print(f"🧪 Testing {token_target:,} tokens...", end="")
            
            content = create_large_content(token_target)
            
            payload = {
                "model": test_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides concise summaries."
                    },
                    {
                        "role": "user",
                        "content": content + "\n\nPlease provide a brief 2-sentence summary of the key points above."
                    }
                ],
                "max_tokens": 20,
                "temperature": 0.1,
                "thinking": True
            }
            
            try:
                headers = {
                    "Authorization": f"Bearer {server_info.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Add Host header if using IP override
                if config.is_ip_overrides_enabled():
                    original_endpoint = server_info.endpoints.get('openai')
                    if original_endpoint:
                        from urllib.parse import urlparse
                        parsed_original = urlparse(original_endpoint)
                        headers["Host"] = parsed_original.netloc
                
                # Configure SSL verification
                verify_ssl = not config.is_ip_overrides_enabled()
                
                async with httpx.AsyncClient(timeout=120.0, verify=verify_ssl) as client:
                    response = await client.post(
                        f"{endpoint_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        console.print(" [green]✅ SUCCESS[/green]")
                        
                        if "usage" in response_data:
                            usage = response_data["usage"]
                            prompt_tokens = usage.get("prompt_tokens", "?")
                            total_tokens = usage.get("total_tokens", "?")
                            console.print(f"   [dim]📊 Usage: {prompt_tokens} prompt, {total_tokens} total[/dim]")
                        
                        return True, "", response_data
                    else:
                        console.print(f" [red]❌ HTTP {response.status_code}[/red]")
                        return False, f"HTTP {response.status_code}", {}
                        
            except httpx.TimeoutException:
                console.print(" [red]⏱️ TIMEOUT[/red]")
                return False, "Timeout", {}
            except Exception as e:
                error_message = str(e)
                console.print(f" [red]💥 ERROR[/red]")
                return False, error_message, {}
        
        async def binary_search_max_tokens() -> int:
            """Binary search to find maximum token capacity"""
            max_iterations = 10 if quick else 25
            
            # Verify starting point works
            success, error, _ = await test_token_count(start)
            if not success:
                console.print(f"[yellow]⚠️  Starting point {start:,} failed: {error}[/yellow]")
                # Try smaller starting points
                for test_start in [32768, 16384, 8192, 4096]:
                    success, error, _ = await test_token_count(test_start)
                    if success:
                        start = test_start
                        console.print(f"[green]✅ Found working start: {start:,} tokens[/green]")
                        break
                else:
                    console.print("[red]❌ No working starting point found![/red]")
                    return 0
            
            # Binary search
            low = start
            high = max_limit
            max_successful = start
            iteration = 0
            
            console.print(f"\n[yellow]🔍 Binary search range: {low:,} to {high:,} tokens[/yellow]")
            console.print("─" * 50)
            
            while low <= high and iteration < max_iterations:
                iteration += 1
                mid = (low + high) // 2
                
                console.print(f"[{iteration:2d}] Testing {mid:,} tokens (range: {low:,}-{high:,})")
                
                success, error_msg, response_data = await test_token_count(mid)
                
                if success:
                    max_successful = mid
                    low = mid + 1
                    console.print(f"     [green]✅ SUCCESS[/green]")
                else:
                    high = mid - 1
                    console.print(f"     [red]❌ FAILED[/red]")
                    
                    if any(keyword in error_msg.lower() for keyword in ['context', 'token', 'limit', 'length', 'exceed']):
                        console.print(f"     [dim]🎯 Context limit error detected[/dim]")
                
                # Rate limiting
                await asyncio.sleep(2.0 if quick else 3.0)
            
            return max_successful
        
        # Run the context test
        console.print("[yellow]🔗 Testing basic connectivity...[/yellow]")
        success, error, _ = asyncio.run(test_token_count(1000))
        if not success:
            console.print(f"[red]❌ Basic connectivity failed: {error}[/red]")
            sys.exit(1)
        
        console.print("[green]✅ Connectivity confirmed, starting context window discovery...[/green]\n")
        
        # Find maximum context window
        max_tokens = asyncio.run(binary_search_max_tokens())
        
        # Results summary
        console.print("\n" + "=" * 60)
        console.print("[bold blue]📊 RESULTS SUMMARY[/bold blue]")
        console.print("=" * 60)
        console.print(f"🎯 Model: {test_model}")
        console.print(f"📡 Endpoint: {endpoint_url}")
        console.print(f"📏 Maximum Context: [bold green]{max_tokens:,}[/bold green] tokens")
        
        # Get current model configuration
        model_info = config.get_model_info(test_model)
        if model_info:
            console.print(f"🔧 Configured OpenAI Tokens: {model_info.get('openai_expected_tokens', 'N/A'):,}")
            console.print(f"🔧 Configured Real Tokens: {model_info.get('real_text_model_tokens', 'N/A'):,}")
        
        if max_tokens > 0:
            console.print(f"\n[yellow]💡 Recommendation:[/yellow]")
            console.print(f"   Update model token configuration:")
            console.print(f"   OpenAI Expected Tokens: {max_tokens:,}")
            console.print(f"   Real Text Model Tokens: {max_tokens:,}")
            
            # Update model configuration if user wants
            if model_info:
                current_openai = model_info.get('openai_expected_tokens')
                current_real = model_info.get('real_text_model_tokens')
                
                if current_openai != max_tokens or current_real != max_tokens:
                    console.print(f"\n[yellow]⚠️  Current configuration doesn't match test results[/yellow]")
                    console.print(f"   Current: OpenAI={current_openai:,}, Real={current_real:,}")
                    console.print(f"   Tested: OpenAI={max_tokens:,}, Real={max_tokens:,}")
                    
                    # Ask if user wants to update
                    try:
                        response = input("\nUpdate model configuration? (y/N): ").strip().lower()
                        if response in ['y', 'yes']:
                            success = config.update_model_tokens(test_model, max_tokens, max_tokens)
                            if success:
                                console.print("[green]✅ Model configuration updated[/green]")
                            else:
                                console.print("[red]❌ Failed to update model configuration[/red]")
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Configuration update cancelled[/yellow]")
        
        # Final verification
        if max_tokens > 0 and not quick:
            console.print(f"\n[yellow]🔬 Verification tests around {max_tokens:,} tokens:[/yellow]")
            for delta in [-2000, -1000, 0, +1000, +2000]:
                test_val = max_tokens + delta
                if test_val > 0:
                    success, _, _ = asyncio.run(test_token_count(test_val))
                    status = "[green]✅ PASS[/green]" if success else "[red]❌ FAIL[/red]"
                    console.print(f"   {test_val:,} tokens: {status}")
                    time.sleep(1.0)
        
        console.print(f"\n[bold green]🎉 Context window discovery complete![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Test interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
@cli.command()
@click.option('--tokens', '-t', default=1000, help='Number of tokens to send in each test (default: 1000)')
@click.option('--runs', '-r', default=10, help='Number of test runs (default: 10)')
@click.option('--model', '-M', help='Model to test (uses current model if not specified)')
@click.option('--output-tokens', '-o', default=200, help='Expected output tokens (default: 200)')
def benchmark(tokens: int, runs: int, model: Optional[str], output_tokens: int):
    """
    ⚡ Benchmark model performance measuring tokens/second
    
    Runs multiple tests to measure average token processing speed for both
    input and output tokens, providing comprehensive performance metrics.
    """
    try:
        import tiktoken
        import time
        import httpx
        import statistics
        
        config = Config()
        proxy_manager = ProxyManager(config)
        
        # Use specified model or current model
        test_model = model or config.get_current_model()
        
        console.print(f"[bold blue]⚡ Performance Benchmark Tool[/bold blue]")
        console.print(f"[dim]Testing model: {test_model}[/dim]")
        console.print(f"[dim]Input tokens: {tokens:,}, Output tokens: {output_tokens:,}, Runs: {runs}[/dim]")
        console.print()
        
        # Check if proxy is running
        proxy_status = asyncio.run(proxy_manager.get_status())
        if not proxy_status.get('running', False):
            console.print("[red]❌ Proxy is not running. Start it with 'python -m cli start'[/red]")
            sys.exit(1)
        
        # Get server info for endpoint
        server_info = config.get_server_info(config.get_current_server())
        if not server_info:
            console.print("[red]❌ Server configuration not found[/red]")
            sys.exit(1)
        
        # Get effective endpoints (with IP overrides)
        effective_endpoints = config.get_effective_server_endpoints(config.get_current_server())
        if effective_endpoints:
            endpoint_url = effective_endpoints.get('openai', server_info.endpoints.get('openai'))
        else:
            endpoint_url = server_info.endpoints.get('openai')
        
        console.print(f"[dim]Testing endpoint: {endpoint_url}[/dim]")
        console.print()
        
        # Create test content of exact token count
        def create_test_content(target_tokens: int) -> str:
            """Create content targeting exactly N tokens using tiktoken"""
            encoding = tiktoken.get_encoding("cl100k_base")
            
            sections = [
                "Machine learning is a transformative technology that enables computers to learn from data without explicit programming. It encompasses various algorithms and approaches that allow systems to improve their performance through experience.",
                "Deep learning, a subset of machine learning, uses neural networks with multiple layers to model complex patterns in data. These networks can automatically learn hierarchical representations of features.",
                "Natural language processing (NLP) enables machines to understand, interpret, and generate human language. Modern NLP systems use transformer architectures and attention mechanisms.",
                "Computer vision allows machines to interpret and understand visual information from the world. Applications include image classification, object detection, and semantic segmentation.",
                "Reinforcement learning involves training agents to make sequential decisions in an environment to maximize cumulative rewards through trial and error.",
            ]
            
            base_content = " ".join(sections)
            content = base_content
            
            while len(encoding.encode(content)) < target_tokens:
                content += " " + base_content
            
            tokens = encoding.encode(content)
            if len(tokens) > target_tokens:
                tokens = tokens[:target_tokens]
                content = encoding.decode(tokens)
            
            return content
        
        # Create test content
        test_content = create_test_content(tokens)
        console.print(f"[dim]Generated {len(tiktoken.get_encoding('cl100k_base').encode(test_content)):,} tokens of test content[/dim]")
        console.print()
        
        # Benchmark function
        async def run_single_benchmark(run_number: int) -> dict:
            """Run a single benchmark test"""
            console.print(f"🧪 Run {run_number}/{runs}...", end="")
            
            payload = {
                "model": test_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Provide concise and accurate responses."
                    },
                    {
                        "role": "user",
                        "content": f"Please analyze this text and provide a brief summary in about {output_tokens} words:\n\n{test_content}"
                    }
                ],
                "max_tokens": output_tokens * 2,  # Allow some flexibility
                "temperature": 0.1,
                "thinking": True
            }
            
            try:
                headers = {
                    "Authorization": f"Bearer {server_info.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Add Host header if using IP override
                if config.is_ip_overrides_enabled():
                    original_endpoint = server_info.endpoints.get('openai')
                    if original_endpoint:
                        from urllib.parse import urlparse
                        parsed_original = urlparse(original_endpoint)
                        headers["Host"] = parsed_original.netloc
                
                # Configure SSL verification
                verify_ssl = not config.is_ip_overrides_enabled()
                
                start_time = time.time()
                
                async with httpx.AsyncClient(timeout=120.0, verify=verify_ssl) as client:
                    response = await client.post(
                        f"{endpoint_url}/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    end_time = time.time()
                    total_time = end_time - start_time
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        
                        # Extract token usage
                        usage = response_data.get("usage", {})
                        input_tokens_used = usage.get("prompt_tokens", tokens)
                        output_tokens_used = usage.get("completion_tokens", 0)
                        total_tokens_used = usage.get("total_tokens", input_tokens_used + output_tokens_used)
                        
                        # Calculate rates
                        input_tokens_per_sec = input_tokens_used / total_time if total_time > 0 else 0
                        output_tokens_per_sec = output_tokens_used / total_time if total_time > 0 else 0
                        total_tokens_per_sec = total_tokens_used / total_time if total_time > 0 else 0
                        
                        console.print(f" [green]✅ {total_time:.2f}s, {total_tokens_per_sec:.1f} tok/s[/green]")
                        
                        return {
                            "run": run_number,
                            "success": True,
                            "total_time": total_time,
                            "input_tokens": input_tokens_used,
                            "output_tokens": output_tokens_used,
                            "total_tokens": total_tokens_used,
                            "input_tokens_per_sec": input_tokens_per_sec,
                            "output_tokens_per_sec": output_tokens_per_sec,
                            "total_tokens_per_sec": total_tokens_per_sec,
                            "error": None
                        }
                    else:
                        error_msg = f"HTTP {response.status_code}"
                        console.print(f" [red]❌ {error_msg}[/red]")
                        
                        return {
                            "run": run_number,
                            "success": False,
                            "total_time": total_time,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "input_tokens_per_sec": 0,
                            "output_tokens_per_sec": 0,
                            "total_tokens_per_sec": 0,
                            "error": error_msg
                        }
                        
            except Exception as e:
                error_msg = str(e)[:50]
                console.print(f" [red]💥 {error_msg}[/red]")
                
                return {
                    "run": run_number,
                    "success": False,
                    "total_time": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "input_tokens_per_sec": 0,
                    "output_tokens_per_sec": 0,
                    "total_tokens_per_sec": 0,
                    "error": error_msg
                }
        
        # Run benchmark tests
        console.print(f"[yellow]🚀 Starting {runs} benchmark runs...[/yellow]")
        console.print("─" * 60)
        
        async def run_benchmark_tests():
            results = []
            for run in range(1, runs + 1):
                result = await run_single_benchmark(run)
                results.append(result)
                
                # Small delay between runs to avoid rate limiting
                if run < runs:
                    await asyncio.sleep(0.5)
            return results
        
        results = asyncio.run(run_benchmark_tests())
        
        # Analyze results
        successful_runs = [r for r in results if r["success"]]
        failed_runs = [r for r in results if not r["success"]]
        
        console.print()
        console.print("[bold blue]📊 BENCHMARK RESULTS[/bold blue]")
        console.print("=" * 60)
        
        if not successful_runs:
            console.print("[red]❌ All benchmark runs failed[/red]")
            for failed_run in failed_runs:
                console.print(f"   Run {failed_run['run']}: {failed_run['error']}")
            sys.exit(1)
        
        # Calculate statistics
        total_times = [r["total_time"] for r in successful_runs]
        input_rates = [r["input_tokens_per_sec"] for r in successful_runs]
        output_rates = [r["output_tokens_per_sec"] for r in successful_runs]
        total_rates = [r["total_tokens_per_sec"] for r in successful_runs]
        input_tokens_list = [r["input_tokens"] for r in successful_runs]
        output_tokens_list = [r["output_tokens"] for r in successful_runs]
        
        # Performance metrics table
        perf_table = Table(show_header=True, box=None)
        perf_table.add_column("Metric", style="cyan", width=25)
        perf_table.add_column("Value", style="white", width=20)
        perf_table.add_column("Details", style="dim", width=30)
        
        # Basic stats
        avg_time = statistics.mean(total_times)
        min_time = min(total_times)
        max_time = max(total_times)
        
        perf_table.add_row("Successful Runs", f"{len(successful_runs)}/{runs}", f"{len(failed_runs)} failed")
        perf_table.add_row("Average Response Time", f"{avg_time:.2f}s", f"Min: {min_time:.2f}s, Max: {max_time:.2f}s")
        
        # Token stats
        avg_input_tokens = statistics.mean(input_tokens_list)
        avg_output_tokens = statistics.mean(output_tokens_list)
        total_input_tokens = sum(input_tokens_list)
        total_output_tokens = sum(output_tokens_list)
        
        perf_table.add_row("Average Input Tokens", f"{avg_input_tokens:.0f}", f"Total: {total_input_tokens:,}")
        perf_table.add_row("Average Output Tokens", f"{avg_output_tokens:.0f}", f"Total: {total_output_tokens:,}")
        
        # Performance rates
        avg_input_rate = statistics.mean(input_rates)
        avg_output_rate = statistics.mean(output_rates)
        avg_total_rate = statistics.mean(total_rates)
        
        perf_table.add_row("Average Input Rate", f"{avg_input_rate:.1f} tok/s", f"Min: {min(input_rates):.1f}, Max: {max(input_rates):.1f}")
        perf_table.add_row("Average Output Rate", f"{avg_output_rate:.1f} tok/s", f"Min: {min(output_rates):.1f}, Max: {max(output_rates):.1f}")
        perf_table.add_row("Average Total Rate", f"{avg_total_rate:.1f} tok/s", f"Min: {min(total_rates):.1f}, Max: {max(total_rates):.1f}")
        
        console.print(perf_table)
        
        # Performance classification
        console.print()
        console.print("[bold blue]🎯 PERFORMANCE CLASSIFICATION[/bold blue]")
        
        if avg_total_rate >= 100:
            perf_grade = "[green]A+ (Excellent)[/green]"
            perf_desc = "Outstanding performance suitable for production workloads"
        elif avg_total_rate >= 50:
            perf_grade = "[green]A (Very Good)[/green]"
            perf_desc = "Excellent performance for most use cases"
        elif avg_total_rate >= 25:
            perf_grade = "[yellow]B (Good)[/yellow]"
            perf_desc = "Good performance for moderate workloads"
        elif avg_total_rate >= 10:
            perf_grade = "[yellow]C (Fair)[/yellow]"
            perf_desc = "Acceptable performance for light workloads"
        else:
            perf_grade = "[red]D (Poor)[/red]"
            perf_desc = "Performance may be insufficient for production use"
        
        console.print(f"Overall Grade: {perf_grade}")
        console.print(f"[dim]{perf_desc}[/dim]")
        
        # Recommendations
        console.print()
        console.print("[bold blue]💡 RECOMMENDATIONS[/bold blue]")
        
        if avg_total_rate < 25:
            console.print("• Consider using a smaller model for better performance")
            console.print("• Optimize prompt size to reduce input tokens")
            console.print("• Check network connectivity to the API endpoint")
        elif avg_total_rate >= 50:
            console.print("• Performance is excellent for current workload")
            console.print("• Consider increasing concurrent requests for higher throughput")
        
        if failed_runs:
            console.print("• Investigate failed runs for reliability improvements")
        
        console.print(f"\n[bold green]🎉 Benchmark completed successfully![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Benchmark interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.group()
def ip():
    """
    🌐 Manage IP overrides for server endpoints
    
    Override the IP addresses used to connect to specific servers.
    This is useful for testing different datacenters or bypassing DNS issues.
    """
    pass

@ip.command()
def list():
    """List all configured IP overrides"""
    try:
        config = Config()
        
        console.print("[bold blue]🌐 IP Override Configuration[/bold blue]\n")
        
        # Show IP override status
        status = "✅ Enabled" if config.is_ip_overrides_enabled() else "❌ Disabled"
        console.print(f"[bold]Status:[/bold] {status}")
        
        # Get all IP overrides
        overrides = config.get_all_ip_overrides()
        
        if not overrides:
            console.print("[yellow]No IP overrides configured[/yellow]")
            return
        
        console.print("\n[bold]Configured Overrides:[/bold]")
        
        override_table = Table(show_header=True, box=None)
        override_table.add_column("Server", style="cyan", width=12)
        override_table.add_column("Override IP", style="white", width=18)
        override_table.add_column("Original Endpoint", style="dim", width=30)
        override_table.add_column("Effective Endpoint", style="green", width=30)
        
        servers = config.get_all_servers()
        
        for server_name, override_ip in overrides.items():
            server_info = servers.get(server_name)
            if server_info:
                original_endpoint = server_info.endpoints.get('openai', server_info.endpoint)
                effective_endpoints = config.get_effective_server_endpoints(server_name)
                effective_endpoint = effective_endpoints.get('openai', 'N/A') if effective_endpoints else 'N/A'
                
                override_table.add_row(
                    server_name,
                    override_ip,
                    original_endpoint[:30],
                    effective_endpoint[:30]
                )
            else:
                override_table.add_row(
                    server_name,
                    override_ip,
                    "[red]Server not found[/red]",
                    "[red]N/A[/red]"
                )
        
        console.print(override_table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@ip.command()
@click.argument('server_name')
@click.argument('ip_address')
def set(server_name: str, ip_address: str):
    """Set an IP override for a specific server
    
    SERVER_NAME: Name of the server (e.g., 'cn', 'inter')
    IP_ADDRESS: IP address to use instead of the original endpoint
    """
    try:
        config = Config()
        
        # Validate server exists
        servers = config.get_all_servers()
        if server_name not in servers:
            console.print(f"[red]❌ Server '{server_name}' not found[/red]")
            console.print("[dim]Available servers:[/dim]")
            for name in servers.keys():
                console.print(f"  • {name}")
            sys.exit(1)
        
        # Validate IP address format (basic check)
        import re
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if not re.match(ip_pattern, ip_address):
            console.print(f"[red]❌ Invalid IP address format: {ip_address}[/red]")
            console.print("[dim]Expected format: 192.168.1.100[/dim]")
            sys.exit(1)
        
        # Show current server info
        server_info = servers[server_name]
        console.print(f"[bold]Server:[/bold] {server_name} ({server_info.region})")
        console.print(f"[bold]Current endpoint:[/bold] {server_info.endpoints.get('openai', server_info.endpoint)}")
        
        # Set the IP override
        success = config.set_ip_override(server_name, ip_address)
        
        if success:
            console.print(f"[green]✅ IP override set successfully[/green]")
            console.print(f"[dim]{server_name} will now connect to {ip_address}[/dim]")
            
            # Show effective endpoints
            effective_endpoints = config.get_effective_server_endpoints(server_name)
            if effective_endpoints:
                console.print("[bold]New effective endpoints:[/bold]")
                for endpoint_type, endpoint_url in effective_endpoints.items():
                    console.print(f"  • {endpoint_type}: {endpoint_url}")
        else:
            console.print(f"[red]❌ Failed to set IP override[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@ip.command()
@click.argument('server_name')
def remove(server_name: str):
    """Remove an IP override for a specific server
    
    SERVER_NAME: Name of the server (e.g., 'cn', 'inter')
    """
    try:
        config = Config()
        
        # Check if override exists
        current_override = config.get_ip_override(server_name)
        if not current_override:
            console.print(f"[yellow]ℹ️  No IP override configured for '{server_name}'[/yellow]")
            return
        
        console.print(f"[bold]Server:[/bold] {server_name}")
        console.print(f"[bold]Current override:[/bold] {current_override}")
        
        # Remove the override
        success = config.remove_ip_override(server_name)
        
        if success:
            console.print(f"[green]✅ IP override removed successfully[/green]")
            console.print(f"[dim]{server_name} will now use the original endpoint[/dim]")
        else:
            console.print(f"[red]❌ Failed to remove IP override[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@ip.command()
@click.argument('enabled', type=bool, required=False)
def enable(enabled: Optional[bool]):
    """Enable or disable IP overrides globally
    
    ENABLED: True to enable, False to disable (optional)
    
    If not specified, shows current status.
    """
    try:
        config = Config()
        
        if enabled is None:
            # Show current status
            current_status = config.is_ip_overrides_enabled()
            status_text = "✅ Enabled" if current_status else "❌ Disabled"
            console.print(f"[bold]IP Overrides Status:[/bold] {status_text}")
            
            if current_status:
                overrides = config.get_all_ip_overrides()
                if overrides:
                    console.print(f"[bold]Active Overrides:[/bold]")
                    for server, ip in overrides.items():
                        console.print(f"  • {server}: {ip}")
                else:
                    console.print("[yellow]IP overrides are enabled but no overrides are configured[/yellow]")
            return
        
        # Enable or disable
        success = config.set_ip_overrides_enabled(enabled)
        
        if success:
            status_text = "enabled" if enabled else "disabled"
            console.print(f"[green]✅ IP overrides {status_text} successfully[/green]")
            
            if enabled:
                console.print("[dim]Use 'python -m cli ip set <server> <ip>' to configure overrides[/dim]")
        else:
            console.print(f"[red]❌ Failed to {'enable' if enabled else 'disable'} IP overrides[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@ip.command()
@click.argument('server_name')
def test(server_name: str):
    """Test connectivity to a server with current IP override configuration
    
    SERVER_NAME: Name of the server to test (e.g., 'cn', 'inter')
    """
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        # Validate server exists
        servers = config.get_all_servers()
        if server_name not in servers:
            console.print(f"[red]❌ Server '{server_name}' not found[/red]")
            console.print("[dim]Available servers:[/dim]")
            for name in servers.keys():
                console.print(f"  • {name}")
            sys.exit(1)
        
        console.print(f"[bold blue]🧪 Testing Server: {server_name}[/bold blue]\n")
        
        # Show configuration
        server_info = servers[server_name]
        console.print(f"[bold]Region:[/bold] {server_info.region}")
        
        original_endpoints = server_info.endpoints
        effective_endpoints = config.get_effective_server_endpoints(server_name)
        
        console.print(f"[bold]Original endpoints:[/bold]")
        for endpoint_type, endpoint_url in original_endpoints.items():
            console.print(f"  • {endpoint_type}: {endpoint_url}")
        
        if effective_endpoints and effective_endpoints != original_endpoints:
            console.print(f"[bold]Effective endpoints (with overrides):[/bold]")
            for endpoint_type, endpoint_url in effective_endpoints.items():
                console.print(f"  • {endpoint_type}: {endpoint_url}")
        else:
            console.print(f"[dim]No IP overrides active for this server[/dim]")
        
        console.print()
        
        # Test performance
        console.print("[dim]Testing connectivity...[/dim]")
        performance = asyncio.run(proxy_manager.measure_server_performance(server_name))
        
        if performance.get('success', False):
            console.print(f"[green]✅ Server is accessible[/green]")
            console.print(f"[bold]Latency:[/bold] {performance.get('latency_ms', 0):.0f}ms")
            console.print(f"[bold]Endpoint tested:[/bold] {performance.get('endpoint', 'Unknown')}")
        else:
            console.print(f"[red]❌ Server is not accessible[/red]")
            console.print(f"[bold]Error:[/bold] {performance.get('error', 'Unknown error')}")
            console.print(f"[bold]Endpoint tested:[/bold] {performance.get('endpoint', 'Unknown')}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@cli.group()
def model():
    """
    🤖 Manage AI model configurations
    
    Switch between different AI models with their specific token configurations.
    Each model has its own text model name, OpenAI expected tokens, and real text model tokens.
    """
    pass

@model.command()
def list():
    """List all configured models"""
    try:
        config = Config()
        
        console.print("[bold blue]🤖 Model Configuration[/bold blue]\n")
        
        # Show current model
        current_model = config.get_current_model()
        console.print(f"[bold]Current Model:[/bold] {current_model}")
        
        # Get all models
        models = config.get_all_models()
        
        if not models:
            console.print("[yellow]No models configured[/yellow]")
            return
        
        console.print("\n[bold]Available Models:[/bold]")
        
        model_table = Table(show_header=True, box=None)
        model_table.add_column("Model", style="cyan", width=15)
        model_table.add_column("Display Name", style="white", width=20)
        model_table.add_column("Text Model", style="white", width=20)
        model_table.add_column("OpenAI Tokens", style="yellow", width=12)
        model_table.add_column("Real Tokens", style="green", width=12)
        model_table.add_column("Description", style="dim", width=30)
        
        for model_name, model_config in models.items():
            is_current = model_name == current_model
            
            display_name = model_config.get('display_name', 'N/A')
            text_model = model_config.get('text_model_name', 'N/A')
            openai_tokens = model_config.get('openai_expected_tokens', 0)
            real_tokens = model_config.get('real_text_model_tokens', 0)
            description = model_config.get('description', '')
            
            current_marker = "→ " if is_current else "  "
            
            # Highlight current model
            model_name_display = f"[bold]{current_marker}{model_name}[/bold]" if is_current else f"{current_marker}{model_name}"
            
            model_table.add_row(
                model_name_display,
                display_name,
                text_model,
                f"{openai_tokens:,}",
                f"{real_tokens:,}",
                description[:30]
            )
        
        console.print(model_table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@model.command()
@click.argument('model_name', required=False)
def switch(model_name: Optional[str]):
    """Switch between models (no restart required)"""
    try:
        config = Config()
        
        if not model_name:
            # Show current model and available options
            current = config.get_current_model()
            models = config.get_all_models()
            
            console.print(f"[bold]Current model:[/bold] {current}")
            console.print("[bold]Available models:[/bold]")
            
            for name, info in models.items():
                current_marker = "→ " if name == current else "  "
                display_name = info.get('display_name', name)
                description = info.get('description', '')
                console.print(f"  {current_marker}[cyan]{name}[/cyan] - {display_name}")
                if description:
                    console.print(f"    [dim]{description}[/dim]")
            return
        
        # Switch to specified model
        console.print(f"[bold blue]🔄 Switching to model: {model_name}[/bold blue]")
        
        success = config.set_current_model(model_name)
        
        if success:
            model_info = config.get_model_info(model_name)
            display_name = model_info.get('display_name', model_name) if model_info else model_name
            console.print(f"[green]✅ Switched to {display_name} ({model_name})[/green]")
            console.print(f"[dim]New requests will use {model_name} model[/dim]")
        else:
            console.print(f"[red]❌ Failed to switch to {model_name}[/red]")
            console.print("[dim]Use 'python -m cli model list' to see available models[/dim]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@model.command()
@click.argument('model_name')
@click.argument('display_name')
@click.argument('text_model_name')
@click.argument('openai_tokens', type=int)
@click.argument('real_tokens', type=int)
@click.option('--description', '-d', default='', help='Model description')
def add(model_name: str, display_name: str, text_model_name: str, 
         openai_tokens: int, real_tokens: int, description: str):
    """Add a new model configuration
    
    MODEL_NAME: Internal model identifier
    DISPLAY_NAME: Human-readable model name
    TEXT_MODEL_NAME: Actual model name for API calls
    OPENAI_TOKENS: OpenAI expected token limit
    REAL_TOKENS: Real model token limit
    """
    try:
        config = Config()
        
        # Validate tokens are positive
        if openai_tokens <= 0 or real_tokens <= 0:
            console.print("[red]❌ Token limits must be positive numbers[/red]")
            sys.exit(1)
        
        # Check if model already exists
        if model_name in config.get_all_models():
            console.print(f"[yellow]⚠️  Model '{model_name}' already exists[/yellow]")
            console.print("[dim]Use 'update' command to modify existing models[/dim]")
            return
        
        # Add the model
        success = config.add_model(
            model_name, display_name, text_model_name,
            openai_tokens, real_tokens, description
        )
        
        if success:
            console.print(f"[green]✅ Model '{display_name}' added successfully[/green]")
            console.print(f"[dim]Model ID: {model_name}[/dim]")
            console.print(f"[dim]Text Model: {text_model_name}[/dim]")
            console.print(f"[dim]OpenAI Tokens: {openai_tokens:,}[/dim]")
            console.print(f"[dim]Real Tokens: {real_tokens:,}[/dim]")
        else:
            console.print(f"[red]❌ Failed to add model[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@model.command()
@click.argument('model_name')
@click.argument('openai_tokens', type=int)
@click.argument('real_tokens', type=int)
def update_tokens(model_name: str, openai_tokens: int, real_tokens: int):
    """Update token configuration for a model
    
    MODEL_NAME: Model identifier
    OPENAI_TOKENS: New OpenAI expected token limit
    REAL_TOKENS: New real model token limit
    """
    try:
        config = Config()
        
        # Validate model exists
        if model_name not in config.get_all_models():
            console.print(f"[red]❌ Model '{model_name}' not found[/red]")
            console.print("[dim]Use 'python -m cli model list' to see available models[/dim]")
            sys.exit(1)
        
        # Validate tokens are positive
        if openai_tokens <= 0 or real_tokens <= 0:
            console.print("[red]❌ Token limits must be positive numbers[/red]")
            sys.exit(1)
        
        # Get current values for comparison
        current_tokens = config.get_model_tokens(model_name)
        if current_tokens:
            console.print(f"[bold]Current tokens for {model_name}:[/bold]")
            console.print(f"  OpenAI: {current_tokens['openai_expected_tokens']:,}")
            console.print(f"  Real: {current_tokens['real_text_model_tokens']:,}")
        
        # Update tokens
        success = config.update_model_tokens(model_name, openai_tokens, real_tokens)
        
        if success:
            console.print(f"[green]✅ Token configuration updated for {model_name}[/green]")
            console.print(f"[dim]New OpenAI Tokens: {openai_tokens:,}[/dim]")
            console.print(f"[dim]New Real Tokens: {real_tokens:,}[/dim]")
        else:
            console.print(f"[red]❌ Failed to update token configuration[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@model.command()
@click.argument('model_name')
def remove(model_name: str):
    """Remove a model configuration
    
    MODEL_NAME: Model identifier to remove
    """
    try:
        config = Config()
        
        # Check if model exists
        if model_name not in config.get_all_models():
            console.print(f"[red]❌ Model '{model_name}' not found[/red]")
            console.print("[dim]Use 'python -m cli model list' to see available models[/dim]")
            sys.exit(1)
        
        # Check if it's the current model
        if config.get_current_model() == model_name:
            console.print(f"[red]❌ Cannot remove current model '{model_name}'[/red]")
            console.print("[dim]Switch to another model first using 'python -m cli model switch'[/dim]")
            sys.exit(1)
        
        # Get model info for confirmation
        model_info = config.get_model_info(model_name)
        display_name = model_info.get('display_name', model_name) if model_info else model_name
        
        console.print(f"[bold]Model to remove:[/bold] {display_name} ({model_name})")
        
        # Remove the model
        success = config.remove_model(model_name)
        
        if success:
            console.print(f"[green]✅ Model '{display_name}' removed successfully[/green]")
        else:
            console.print(f"[red]❌ Failed to remove model[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

@model.command()
@click.argument('model_name', required=False)
def info(model_name: Optional[str]):
    """Show detailed information about a model"""
    try:
        config = Config()
        
        if not model_name:
            # Show current model info
            model_name = config.get_current_model()
            console.print(f"[bold]Current Model Information:[/bold] {model_name}")
        else:
            console.print(f"[bold]Model Information:[/bold] {model_name}")
        
        # Get model info
        model_info = config.get_model_info(model_name)
        if not model_info:
            console.print(f"[red]❌ Model '{model_name}' not found[/red]")
            console.print("[dim]Use 'python -m cli model list' to see available models[/dim]")
            sys.exit(1)
        
        # Create info table
        info_table = Table(show_header=True, box=None)
        info_table.add_column("Property", style="cyan", width=20)
        info_table.add_column("Value", style="white")
        
        info_table.add_row("Model ID", model_name)
        info_table.add_row("Display Name", model_info.get('display_name', 'N/A'))
        info_table.add_row("Text Model Name", model_info.get('text_model_name', 'N/A'))
        info_table.add_row("OpenAI Expected Tokens", f"{model_info.get('openai_expected_tokens', 0):,}")
        info_table.add_row("Real Text Model Tokens", f"{model_info.get('real_text_model_tokens', 0):,}")
        info_table.add_row("Description", model_info.get('description', 'No description'))
        
        console.print(info_table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    console.print("\n[yellow]Operation cancelled by user[/yellow]")
    sys.exit(0)

def main():
    """Main entry point"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()