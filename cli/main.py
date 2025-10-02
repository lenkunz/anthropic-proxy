"""
Anthropic Proxy CLI - Main entry point

Provides command-line interface for managing the Anthropic Proxy server
with usage statistics, server switching, and monitoring capabilities.
"""

import asyncio
import sys
import signal
import time
from typing import Optional
import click

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
        if len(error_msg) > 30:
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
            if len(error) > 18:
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
        
        success = asyncio.run(proxy_manager.restart())
        if success:
            console.print("[green]✅ Proxy restarted successfully![/green]")
        else:
            console.print("[red]❌ Failed to restart proxy[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
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
                if error_details and len(error_details) > 18:
                    error_details = error_details[:15] + "..."
            
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
@click.option('--interval', '-i', default=60, help='Monitoring interval in seconds (default: 60)')
def auto_switch(interval: int):
    """Enable automatic server switching based on performance (no restart)"""
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        console.print(f"[bold blue]🔄 Auto-Switching Enabled (No Restart Mode)[/bold blue]")
        console.print(f"[dim]Monitoring every {interval} seconds... Press Ctrl+C to stop[/dim]\n")
        
        # Start auto-switching loop
        asyncio.run(proxy_manager.monitor_and_auto_switch(interval))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Auto-switching stopped[/yellow]")
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
@click.option('--interval', '-i', default=120, help='Intelligent monitoring interval in seconds (default: 120)')
def smart_switch(interval: int):
    """
    🧠 Intelligent auto-switching with endpoint discovery
    
    Uses check-host.net API to discover multiple IP endpoints and 
    automatically switches to the best performing endpoint based on:
    - Real-time performance monitoring
    - Multi-endpoint latency testing
    - Thinking-based endpoint validation
    """
    try:
        config = Config()
        proxy_manager = ProxyManager(config)
        
        console.print("[bold blue]🧠 Intelligent Auto-Switching[/bold blue]")
        console.print("[dim]Features:[/dim]")
        console.print("  • check-host.net endpoint discovery")
        console.print("  • Multi-datacenter latency testing")
        console.print("  • Thinking-based endpoint validation")
        console.print("  • Performance-based automatic switching")
        console.print(f"[dim]Monitoring every {interval} seconds... Press Ctrl+C to stop[/dim]\n")
        
        # Start intelligent monitoring loop
        asyncio.run(proxy_manager.monitor_with_intelligent_switching(interval))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Intelligent auto-switching stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

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
            ("Log Level", config.log_level),
            ("Enable Stats", "✅" if config.enable_stats else "❌"),
        ]
        
        for setting, value in config_data:
            config_table.add_row(setting, value)
        
        console.print(config_table)
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    console.print("\n[yellow]Operation cancelled by user[/yellow]")
    sys.exit(0)

def main():
    """Main entry point"""
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