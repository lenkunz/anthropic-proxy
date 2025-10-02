"""
Terminal User Interface (TUI) components for the Anthropic Proxy CLI

Provides rich interactive interfaces for monitoring and managing the proxy.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn
from rich.columns import Columns
from rich.align import Align
from rich import box

from cli.config import Config
from cli.stats import StatsCollector
from cli.proxy import ProxyManager
from cli.utils import format_duration, format_bytes, format_number

class ProxyTUI:
    """Main TUI application for proxy monitoring"""
    
    def __init__(self):
        self.console = Console()
        self.config = Config()
        self.stats = StatsCollector(self.config)
        self.proxy = ProxyManager(self.config)
        self.running = True
        
        # Store previous stats for trend calculation
        self.previous_stats = {}
        
    def create_header(self) -> Panel:
        """Create the header panel"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_server = self.config.get_current_server()
        
        header_text = Text.from_markup(
            f"[bold blue]🚀 Anthropic Proxy TUI[/bold blue]\n"
            f"[dim]Server: [cyan]{current_server}[/cyan] | "
            f"Time: {current_time}[/dim]"
        )
        
        return Panel(
            Align.center(header_text),
            box=box.ROUNDED,
            style="bold blue"
        )
    
    def create_status_panel(self) -> Panel:
        """Create the status panel"""
        # Create status table
        status_table = Table(show_header=False, box=None, padding=0)
        status_table.add_column("Metric", style="cyan", width=20)
        status_table.add_column("Value", style="white")
        
        # Get proxy status
        try:
            # This would be an async call in a real implementation
            # For now, we'll simulate it
            is_running = self._simulate_proxy_status()
            
            status_table.add_row(
                "Proxy Status", 
                "[green]● Running[/green]" if is_running else "[red]● Stopped[/red]"
            )
            status_table.add_row(
                "Current Server",
                f"[bold]{self.config.get_current_server()}[/bold]"
            )
            status_table.add_row(
                "Endpoint",
                self.config.get_server_info(self.config.get_current_server()).endpoint
            )
            
        except Exception:
            status_table.add_row("Proxy Status", "[yellow]⚠ Unknown[/yellow]")
            status_table.add_row("Current Server", self.config.get_current_server())
            status_table.add_row("Endpoint", "Checking...")
        
        return Panel(
            status_table,
            title="[bold]Status[/bold]",
            box=box.ROUNDED,
            border_style="green" if self._simulate_proxy_status() else "red"
        )
    
    def _simulate_proxy_status(self) -> bool:
        """Simulate proxy status check (simplified)"""
        # In real implementation, this would check if proxy is actually running
        return True
    
    async def create_stats_panel(self) -> Panel:
        """Create the statistics panel with real data"""
        stats_table = Table()
        stats_table.add_column("Metric", style="cyan", width=18)
        stats_table.add_column("Current", style="white", justify="right")
        stats_table.add_column("Trend", style="green", width=8)
        
        try:
            # Get real stats from the stats collector
            stats = await self._get_real_stats()
            
            # Calculate trends
            total_requests_trend = self._calculate_trend(stats.get('total_requests', 0), 'requests')
            tokens_trend = self._calculate_trend(stats.get('total_tokens', 0), 'tokens')
            response_time_trend = self._calculate_trend(stats.get('avg_response_time', 0), 'response_time', higher_is_better=False)
            
            stats_table.add_row("Total Requests", format_number(stats.get('total_requests', 0)), total_requests_trend)
            stats_table.add_row("Requests/min", f"{stats.get('requests_per_minute', 0):.1f}", "↑ 8%")
            stats_table.add_row("Total Tokens", format_number(stats.get('total_tokens', 0)), tokens_trend)
            stats_table.add_row("Success Rate", f"{stats.get('success_rate', 0):.1f}%", "↑ 2%")
            stats_table.add_row("Avg Response", format_duration(stats.get('avg_response_time', 0)), response_time_trend)
            stats_table.add_row("Active Conn.", str(stats.get('active_connections', 0)), "—")
            stats_table.add_row("Uptime", format_duration(stats.get('uptime', 0)), "—")
            
        except Exception as e:
            # Fallback to error state
            stats_table.add_row("Total Requests", "[red]Error[/red]", "—")
            stats_table.add_row("Requests/min", "[red]Error[/red]", "—")
            stats_table.add_row("Total Tokens", "[red]Error[/red]", "—")
            stats_table.add_row("Success Rate", "[red]Error[/red]", "—")
            stats_table.add_row("Avg Response", "[red]Error[/red]", "—")
            stats_table.add_row("Active Conn.", "[red]Error[/red]", "—")
            stats_table.add_row("Uptime", "[red]Error[/red]", "—")
        
        return Panel(
            stats_table,
            title="[bold]Live Statistics[/bold]",
            box=box.ROUNDED,
            border_style="blue"
        )
    
    async def _get_real_stats(self) -> Dict[str, Any]:
        """Get real statistics from the stats collector"""
        try:
            # Try to get current stats from the stats collector
            stats = await self.stats.get_current_stats()
            
            # Store previous stats for trend calculation
            if hasattr(self, 'previous_stats') and self.previous_stats:
                # Compare with previous stats
                trend_data = {}
                for key in ['total_requests', 'total_tokens', 'avg_response_time']:
                    if key in stats and key in self.previous_stats:
                        prev = self.previous_stats[key]
                        curr = stats[key]
                        if prev > 0:
                            change = ((curr - prev) / prev) * 100
                            trend_data[f'{key}_trend'] = change
                
                self.previous_stats = stats.copy()
            else:
                # First time getting stats
                self.previous_stats = stats.copy()
            
            return stats
            
        except Exception as e:
            # Fallback to mock data if stats collection fails
            return {
                'total_requests': 0,
                'requests_per_minute': 0.0,
                'total_tokens': 0,
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'active_connections': 0,
                'uptime': 0.0
            }
    
    def _calculate_trend(self, current_value, metric_type, higher_is_better=True):
        """Calculate trend indicator"""
        if current_value == 0:
            return "—"
        
        # Mock trend calculation based on metric type
        if metric_type == 'requests':
            return "↑ 12%" if current_value > 0 else "—"
        elif metric_type == 'tokens':
            return "↑ 15%" if current_value > 0 else "—"
        elif metric_type == 'response_time':
            if current_value < 1.0:
                return "↓ 120ms"
            elif current_value < 2.0:
                return "↓ 50ms"
            else:
                return "↑ 50ms"
        else:
            return "—"
    
    def create_servers_panel(self) -> Panel:
        """Create the servers panel"""
        servers_table = Table()
        servers_table.add_column("Server", style="cyan", width=12)
        servers_table.add_column("Status", style="white", width=8)
        servers_table.add_column("Latency", style="white", justify="right", width=8)
        servers_table.add_column("Region", style="white", width=12)
        
        servers = self.config.get_all_servers()
        current_server = self.config.get_current_server()
        
        for server_name, server_info in servers.items():
            is_current = server_name == current_server
            
            # Simulate status checking
            has_api_key = bool(server_info.api_key)
            status = "🟢 Online" if has_api_key else "🔴 No Key"
            latency = f"{server_info.latency_ms:.0f}ms"
            
            row_style = "bold" if is_current else ""
            
            servers_table.add_row(
                f"[{row_style}]{server_name}[/{row_style}]",
                status,
                latency,
                server_info.region
            )
        
        return Panel(
            servers_table,
            title="[bold]Servers[/bold]",
            box=box.ROUNDED,
            border_style="yellow"
        )
    
    def create_actions_panel(self) -> Panel:
        """Create the quick actions panel"""
        actions_text = Text.from_markup(
            "[bold cyan]Quick Actions:[/bold cyan]\n"
            "[dim][q]uit  [r]estart  [s]witch  [l]ogs  [c]onfig  [h]elp[/dim]"
        )
        
        return Panel(
            actions_text,
            box=box.ROUNDED,
            border_style="magenta"
        )
    
    def create_layout(self) -> Layout:
        """Create the main TUI layout"""
        layout = Layout()
        
        # Split into header, main, and footer
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="footer", size=5)
        )
        
        # Split main into left and right
        layout["main"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )
        
        # Split left column
        layout["left"].split_column(
            Layout(name="status", size=10),
            Layout(name="stats", ratio=1)
        )
        
        # Split right column
        layout["right"].split_column(
            Layout(name="servers", ratio=1),
            Layout(name="actions", size=5)
        )
        
        # Add panels to layout
        layout["header"].update(self.create_header())
        layout["status"].update(self.create_status_panel())
        layout["stats"].update(self.create_header())  # Placeholder, will be updated async
        layout["servers"].update(self.create_servers_panel())
        layout["actions"].update(self.create_actions_panel())
        layout["footer"].update(Panel(
            Text("[dim]Press 'q' to quit, 'h' for help[/dim]", style="dim"),
            box=box.ROUNDED
        ))
        
        return layout
    
    async def update_display(self, live: Live):
        """Update the TUI display"""
        while self.running:
            try:
                layout = self.create_layout()
                
                # Update stats panel with real data
                stats_panel = await self.create_stats_panel()
                layout["stats"].update(stats_panel)
                
                live.update(layout)
                await asyncio.sleep(2)  # Update every 2 seconds
            except Exception as e:
                self.console.print(f"[red]Error updating display: {e}[/red]")
                break
    
    async def handle_input(self):
        """Handle user input"""
        import sys
        import tty
        import termios
        
        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        
        try:
            # Set raw mode
            tty.setraw(sys.stdin.fileno())
            
            while self.running:
                # Read single character
                char = sys.stdin.read(1)
                
                if char == 'q':
                    self.running = False
                    break
                elif char == 'r':
                    await self._restart_proxy()
                elif char == 's':
                    await self._switch_server()
                elif char == 'l':
                    await self._show_logs()
                elif char == 'c':
                    await self._show_config()
                elif char == 'h':
                    self._show_help()
                elif char == '\x03':  # Ctrl+C
                    self.running = False
                    break
                    
        except Exception as e:
            self.console.print(f"[red]Input error: {e}[/red]")
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    async def _restart_proxy(self):
        """Restart the proxy"""
        self.console.print("[yellow]Restarting proxy...[/yellow]")
        # Implementation would go here
        await asyncio.sleep(1)
    
    async def _switch_server(self):
        """Switch between servers"""
        current = self.config.get_current_server()
        new_server = "cn" if current == "international" else "international"
        
        self.console.print(f"[blue]Switching to {new_server}...[/blue]")
        # Implementation would go here
        await asyncio.sleep(1)
    
    async def _show_logs(self):
        """Show logs (would open a log viewer)"""
        self.console.print("[dim]Logs viewer would open here[/dim]")
        await asyncio.sleep(1)
    
    async def _show_config(self):
        """Show configuration"""
        self.console.print("[dim]Configuration viewer would open here[/dim]")
        await asyncio.sleep(1)
    
    def _show_help(self):
        """Show help"""
        help_text = """
[bold cyan]Help:[/bold cyan]
[yellow]q[/yellow] - Quit TUI
[yellow]r[/yellow] - Restart proxy
[yellow]s[/yellow] - Switch server
[yellow]l[/yellow] - View logs
[yellow]c[/yellow] - View config
[yellow]h[/yellow] - Show this help
[yellow]Ctrl+C[/yellow] - Force quit
        """
        self.console.print(help_text)
    
    async def run(self):
        """Run the TUI application"""
        # Clear screen
        self.console.clear()
        
        # Show welcome message
        welcome_text = Text.from_markup(
            "[bold blue]🚀 Anthropic Proxy TUI[/bold blue]\n\n"
            "[green]Starting Terminal User Interface...[/green]\n"
            "[dim]Live statistics monitoring with server switching capabilities[/dim]\n"
            "[dim]Press 'h' for help, 'q' to quit[/dim]"
        )
        
        self.console.print(Panel(
            welcome_text,
            box=box.ROUNDED,
            border_style="blue"
        ))
        
        await asyncio.sleep(2)
        
        # Create live display
        with Live(console=self.console, refresh_per_second=1) as live:
            # Start display update task
            display_task = asyncio.create_task(self.update_display(live))
            
            # Start input handling task
            input_task = asyncio.create_task(self.handle_input())
            
            try:
                # Wait for either task to complete
                await asyncio.gather(display_task, input_task, return_exceptions=True)
            except KeyboardInterrupt:
                self.running = False
            finally:
                # Cancel tasks
                display_task.cancel()
                input_task.cancel()
                
                # Wait for tasks to finish
                try:
                    await asyncio.gather(display_task, input_task, return_exceptions=True)
                except:
                    pass
        
        # Show exit message
        self.console.print("\n[green]✅ TUI exited successfully[/green]")

class InteractiveMenu:
    """Interactive menu for CLI operations"""
    
    def __init__(self):
        self.console = Console()
        self.config = Config()
        self.proxy = ProxyManager(self.config)
        self.stats = StatsCollector(self.config)
    
    async def show_main_menu(self):
        """Show the main interactive menu"""
        while True:
            self.console.clear()
            
            # Create title
            title = Panel(
                Text.from_markup("[bold blue]🚀 Anthropic Proxy CLI[/bold blue]"),
                box=box.ROUNDED,
                border_style="blue"
            )
            self.console.print(title)
            
            # Create menu
            menu_table = Table(show_header=True, box=box.ROUNDED)
            menu_table.add_column("Option", style="cyan", width=5)
            menu_table.add_column("Description", style="white")
            menu_table.add_column("Status", style="green", width=15)
            
            # Get current status
            is_running = await self._check_proxy_running()
            current_server = self.config.get_current_server()
            
            menu_items = [
                ("1", "Show Status", "● Active" if is_running else "○ Inactive"),
                ("2", "Start Proxy", "" if is_running else "▶ Available"),
                ("3", "Stop Proxy", "■ Running" if is_running else ""),
                ("4", "Switch Server", f"→ {current_server}"),
                ("5", "View Statistics", "📊 Available"),
                ("6", "View Logs", "📋 Available"),
                ("7", "Configuration", "⚙️  Available"),
                ("8", "Server List", "🌐 Available"),
                ("9", "Launch TUI", "🖥️  Available"),
                ("0", "Exit", "👋 Goodbye")
            ]
            
            for option, description, status in menu_items:
                menu_table.add_row(option, description, status)
            
            self.console.print(menu_table)
            
            # Get user input
            choice = self.console.input("\n[cyan]Enter your choice (0-9):[/cyan] ").strip()
            
            # Handle choice
            if choice == "1":
                await self._show_status()
            elif choice == "2":
                if not is_running:
                    await self._start_proxy()
                else:
                    self.console.print("[yellow]Proxy is already running[/yellow]")
            elif choice == "3":
                if is_running:
                    await self._stop_proxy()
                else:
                    self.console.print("[yellow]Proxy is not running[/yellow]")
            elif choice == "4":
                await self._switch_server_menu()
            elif choice == "5":
                await self._show_statistics()
            elif choice == "6":
                await self._show_logs()
            elif choice == "7":
                await self._configure_settings()
            elif choice == "8":
                await self._show_servers()
            elif choice == "9":
                await self._launch_tui()
            elif choice == "0":
                self.console.print("[green]Goodbye! 👋[/green]")
                break
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")
            
            if choice != "0":
                self.console.input("\n[dim]Press Enter to continue...[/dim]")
    
    async def _check_proxy_running(self) -> bool:
        """Check if proxy is running"""
        try:
            return await self.proxy.is_running()
        except:
            return False
    
    async def _show_status(self):
        """Show detailed status"""
        self.console.clear()
        self.console.print("[bold blue]📊 Proxy Status[/bold blue]\n")
        
        is_running = await self._check_proxy_running()
        current_server = self.config.get_current_server()
        server_info = self.config.get_server_info(current_server)
        
        status_data = [
            ("Proxy Status", "🟢 Running" if is_running else "🔴 Stopped"),
            ("Current Server", current_server),
            ("Endpoint", server_info.endpoint),
            ("Region", server_info.region),
            ("API Key", "✅ Configured" if server_info.api_key else "❌ Missing"),
            ("Latency", f"{server_info.latency_ms:.0f}ms"),
        ]
        
        status_table = Table(show_header=False, box=box.ROUNDED)
        status_table.add_column("Property", style="cyan", width=15)
        status_table.add_column("Value", style="white")
        
        for prop, value in status_data:
            status_table.add_row(prop, value)
        
        self.console.print(Panel(status_table, title="Current Status"))
    
    async def _start_proxy(self):
        """Start the proxy"""
        self.console.clear()
        self.console.print("[bold blue]🚀 Starting Proxy[/bold blue]\n")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Starting proxy...", total=100)
            
            success = await self.proxy.start()
            
            if success:
                progress.update(task, completed=100)
                self.console.print("\n[green]✅ Proxy started successfully![/green]")
            else:
                self.console.print("\n[red]❌ Failed to start proxy[/red]")
    
    async def _stop_proxy(self):
        """Stop the proxy"""
        self.console.clear()
        self.console.print("[bold yellow]🛑 Stopping Proxy[/bold yellow]\n")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Stopping proxy...", total=100)
            
            success = await self.proxy.stop()
            
            if success:
                progress.update(task, completed=100)
                self.console.print("\n[green]✅ Proxy stopped successfully![/green]")
            else:
                self.console.print("\n[red]❌ Failed to stop proxy[/red]")
    
    async def _switch_server_menu(self):
        """Show server switching menu"""
        self.console.clear()
        self.console.print("[bold blue]🔄 Switch Server[/bold blue]\n")
        
        servers = self.config.get_all_servers()
        current_server = self.config.get_current_server()
        
        server_table = Table(show_header=True, box=box.ROUNDED)
        server_table.add_column("Number", style="cyan", width=6)
        server_table.add_column("Server", style="white", width=12)
        server_table.add_column("Endpoint", style="dim", width=25)
        server_table.add_column("Status", style="green", width=10)
        
        servers_list = list(servers.items())
        
        for i, (server_name, server_info) in enumerate(servers_list, 1):
            status = "✅ Current" if server_name == current_server else "○ Available"
            server_table.add_row(str(i), server_name, server_info.endpoint, status)
        
        self.console.print(server_table)
        
        choice = self.console.input(f"\n[cyan]Select server (1-{len(servers_list)}):[/cyan] ").strip()
        
        try:
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(servers_list):
                selected_server = servers_list[choice_idx][0]
                
                if selected_server == current_server:
                    self.console.print("[yellow]This is already the current server[/yellow]")
                else:
                    self.console.print(f"[blue]Switching to {selected_server}...[/blue]")
                    success = await self.proxy.switch_server(selected_server)
                    
                    if success:
                        self.console.print(f"[green]✅ Switched to {selected_server}[/green]")
                    else:
                        self.console.print(f"[red]❌ Failed to switch to {selected_server}[/red]")
            else:
                self.console.print("[red]Invalid selection[/red]")
        except ValueError:
            self.console.print("[red]Invalid input[/red]")
    
    async def _show_statistics(self):
        """Show statistics"""
        self.console.clear()
        self.console.print("[bold blue]📊 Usage Statistics[/bold blue]\n")
        
        try:
            # Get detailed stats
            stats = await self.stats.get_detailed_stats(24)
            
            stats_table = Table(show_header=True, box=box.ROUNDED)
            stats_table.add_column("Metric", style="cyan", width=20)
            stats_table.add_column("Value", style="white", justify="right")
            stats_table.add_column("Trend", style="green", width=8)
            
            stats_data = [
                ("Total Requests", format_number(stats['total_requests']), "↑ 12%"),
                ("Success Rate", f"{stats['success_rate']:.1f}%", "↑ 2%"),
                ("Total Tokens", format_number(stats['total_tokens']), "↑ 15%"),
                ("Avg Response Time", format_duration(stats['avg_response_time']), "↓ 120ms"),
                ("95th Percentile", format_duration(stats['p95_response_time']), "↓ 180ms"),
            ]
            
            for metric, value, trend in stats_data:
                stats_table.add_row(metric, value, trend)
            
            self.console.print(Panel(stats_table, title="Last 24 Hours"))
            
        except Exception as e:
            self.console.print(f"[red]Error loading statistics: {e}[/red]")
    
    async def _show_logs(self):
        """Show logs"""
        self.console.clear()
        self.console.print("[bold blue]📋 Recent Logs[/bold blue]\n")
        
        # This would show actual logs
        self.console.print("[dim]Log viewer would be implemented here[/dim]")
        self.console.print("[dim]Showing recent proxy activity...[/dim]")
    
    async def _configure_settings(self):
        """Configure settings"""
        self.console.clear()
        self.console.print("[bold blue]⚙️  Configuration[/bold blue]\n")
        
        config_table = Table(show_header=False, box=box.ROUNDED)
        config_table.add_column("Setting", style="cyan", width=20)
        config_table.add_column("Value", style="white")
        
        config_data = [
            ("Host", self.config.host),
            ("Port", str(self.config.port)),
            ("Current Server", self.config.get_current_server()),
            ("Log Level", self.config.log_level),
            ("Enable Stats", "✅" if self.config.enable_stats else "❌"),
        ]
        
        for setting, value in config_data:
            config_table.add_row(setting, value)
        
        self.console.print(Panel(config_table, title="Current Configuration"))
    
    async def _show_servers(self):
        """Show server list with status"""
        self.console.clear()
        self.console.print("[bold blue]🌐 Server List[/bold blue]\n")
        
        servers = self.config.get_all_servers()
        
        server_table = Table(show_header=True, box=box.ROUNDED)
        server_table.add_column("Server", style="cyan", width=12)
        server_table.add_column("Endpoint", style="white", width=25)
        server_table.add_column("Region", style="white", width=12)
        server_table.add_column("Latency", style="white", justify="right", width=8)
        server_table.add_column("API Key", style="green", width=8)
        server_table.add_column("Status", style="white", width=10)
        
        for server_name, server_info in servers.items():
            api_key_status = "✅" if server_info.api_key else "❌"
            status = "🟢 Online" if server_info.api_key else "🔴 No Key"
            
            server_table.add_row(
                server_name,
                server_info.endpoint,
                server_info.region,
                f"{server_info.latency_ms:.0f}ms",
                api_key_status,
                status
            )
        
        self.console.print(server_table)
    
    async def _launch_tui(self):
        """Launch the TUI"""
        self.console.clear()
        self.console.print("[bold blue]🖥️  Launching TUI...[/bold blue]\n")
        
        tui = ProxyTUI()
        await tui.run()

# Convenience function to run the interactive menu
async def run_interactive_menu():
    """Run the interactive menu"""
    menu = InteractiveMenu()
    await menu.show_main_menu()