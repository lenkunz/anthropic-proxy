"""
Utility functions for the Anthropic Proxy CLI

Common helper functions for formatting, validation, and other operations.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"

def format_bytes(bytes_count: int) -> str:
    """Format bytes in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"

def format_number(number: Union[int, float]) -> str:
    """Format number with thousands separator"""
    if isinstance(number, int):
        return f"{number:,}"
    else:
        return f"{number:,.2f}"

def format_timestamp(timestamp: float, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format timestamp to readable string"""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime(format)

def format_time_ago(timestamp: float) -> str:
    """Format timestamp as 'time ago'"""
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return f"{int(diff)} seconds ago"
    elif diff < 3600:
        return f"{int(diff // 60)} minutes ago"
    elif diff < 86400:
        return f"{int(diff // 3600)} hours ago"
    else:
        return f"{int(diff // 86400)} days ago"

def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate string to specified length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe filesystem usage"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    # Ensure it's not empty
    if not filename:
        filename = "unnamed"
    return filename

def validate_api_key(api_key: str) -> bool:
    """Validate API key format"""
    if not api_key:
        return False
    
    # Basic validation - should be a reasonable length
    if len(api_key) < 10:
        return False
    
    # Check for common patterns (this is basic validation)
    # API keys are typically alphanumeric with some special characters
    import re
    if not re.match(r'^[a-zA-Z0-9\-_\.]+$', api_key):
        return False
    
    return True

def validate_url(url: str) -> bool:
    """Validate URL format"""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def validate_port(port: Union[str, int]) -> bool:
    """Validate port number"""
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False

def calculate_percent_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100

def get_trend_indicator(current: float, previous: float, higher_is_better: bool = True) -> str:
    """Get trend indicator with arrow and color"""
    if previous == 0:
        return "—"
    
    change = current - previous
    percent_change = calculate_percent_change(previous, current)
    
    if abs(percent_change) < 0.1:  # Less than 0.1% change
        return "—"
    
    arrow = "↑" if change > 0 else "↓"
    
    if higher_is_better:
        color = "green" if change > 0 else "red"
    else:
        color = "red" if change > 0 else "green"
    
    return f"[{color}]{arrow} {abs(percent_change):.1f}%[/{color}]"

def print_banner(console: Console, title: str = "Anthropic Proxy CLI"):
    """Print application banner"""
    banner_text = Text.from_markup(
        f"[bold blue]🚀 {title}[/bold blue]\n"
        f"[dim]Manage your proxy server and monitor usage statistics[/dim]"
    )
    
    panel = Panel(
        banner_text,
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(panel)
    console.print()  # Add spacing

def print_success(console: Console, message: str):
    """Print success message"""
    console.print(f"[green]✅ {message}[/green]")

def print_error(console: Console, message: str):
    """Print error message"""
    console.print(f"[red]❌ {message}[/red]")

def print_warning(console: Console, message: str):
    """Print warning message"""
    console.print(f"[yellow]⚠️  {message}[/yellow]")

def print_info(console: Console, message: str):
    """Print info message"""
    console.print(f"[blue]ℹ️  {message}[/blue]")

def confirm_action(console: Console, message: str, default: bool = False) -> bool:
    """Ask for user confirmation"""
    prompt = f"{message} [{'Y/n' if default else 'y/N'}]: "
    response = console.input(prompt).strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes', 'ye', 'Y']

def parse_time_string(time_str: str) -> Optional[float]:
    """Parse time string like '1h', '30m', '5s' to seconds"""
    import re
    
    pattern = r'^(\d+)([hms])$'
    match = re.match(pattern, time_str.strip().lower())
    
    if not match:
        return None
    
    amount, unit = match.groups()
    amount = int(amount)
    
    multipliers = {
        'h': 3600,
        'm': 60,
        's': 1
    }
    
    return amount * multipliers.get(unit, 1)

def format_table_data(data: dict, title: str = None) -> Table:
    """Format data into a Rich table"""
    table = Table(title=title, show_header=True, header_style="bold blue")
    table.add_column("Key", style="cyan", width=20)
    table.add_column("Value", style="white")
    
    for key, value in data.items():
        formatted_value = format_value(value)
        table.add_row(key, formatted_value)
    
    return table

def format_value(value) -> str:
    """Format a value for display"""
    if isinstance(value, bool):
        return "✅ Yes" if value else "❌ No"
    elif isinstance(value, (int, float)):
        if isinstance(value, float) and value < 1:
            return f"{value:.3f}"
        return format_number(value)
    elif isinstance(value, list):
        return f"[{len(value)} items]"
    elif isinstance(value, dict):
        return f"[{len(value)} keys]"
    elif value is None:
        return "—"
    else:
        return str(value)

def create_progress_tracker(total: int, description: str = "Processing"):
    """Create a Rich progress tracker"""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    )
    
    task_id = progress.add_task(description, total=total)
    return progress, task_id

def safe_filename(prefix: str = "", extension: str = "") -> str:
    """Generate a safe filename with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    parts = []
    if prefix:
        parts.append(sanitize_filename(prefix))
    parts.append(timestamp)
    
    filename = "_".join(parts)
    
    if extension:
        if not extension.startswith('.'):
            extension = f".{extension}"
        filename += extension
    
    return filename

def calculate_request_rate(timestamps: list, window_seconds: int = 60) -> float:
    """Calculate request rate from timestamps"""
    if not timestamps:
        return 0.0
    
    now = time.time()
    cutoff = now - window_seconds
    
    recent_requests = [ts for ts in timestamps if ts > cutoff]
    return len(recent_requests) / (window_seconds / 60)  # Requests per minute

def get_memory_usage() -> dict:
    """Get current memory usage statistics"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss": memory_info.rss,  # Resident Set Size
            "vms": memory_info.vms,  # Virtual Memory Size
            "percent": process.memory_percent(),
            "available": psutil.virtual_memory().available
        }
    except ImportError:
        # psutil not available
        return {}

def check_dependencies() -> dict:
    """Check if required dependencies are available"""
    dependencies = {
        "httpx": False,
        "yaml": False,
        "rich": False,
        "dotenv": False,
        "psutil": False  # Optional
    }
    
    for dep in dependencies:
        try:
            __import__(dep)
            dependencies[dep] = True
        except ImportError:
            pass
    
    return dependencies

def get_system_info() -> dict:
    """Get system information"""
    import platform
    
    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.architecture()[0],
        "processor": platform.processor(),
        "hostname": platform.node()
    }
    
    # Add memory info if available
    memory_usage = get_memory_usage()
    if memory_usage:
        info["memory_rss_mb"] = memory_usage["rss"] / (1024 * 1024)
        info["memory_percent"] = memory_usage["percent"]
    
    return info

def create_spinner_task(console: Console, description: str):
    """Create a spinner task for long-running operations"""
    from rich.progress import Progress, SpinnerColumn, TextColumn
    
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    )
    
    task_id = progress.add_task(description)
    return progress, task_id

async def run_with_spinner(coro, description: str):
    """Run a coroutine with a spinner"""
    progress, task_id = create_spinner_task(console, description)
    
    try:
        with progress:
            result = await coro
            return result
    except Exception as e:
        console.print(f"[red]Error during {description}: {e}[/red]")
        raise

def merge_dicts(*dicts):
    """Merge multiple dictionaries recursively"""
    result = {}
    
    for d in dicts:
        for key, value in d.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
    
    return result

def deep_get(dictionary: dict, keys: str, default=None):
    """Get value from nested dictionary using dot notation"""
    keys_list = keys.split('.')
    current = dictionary
    
    try:
        for key in keys_list:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default

def deep_set(dictionary: dict, keys: str, value):
    """Set value in nested dictionary using dot notation"""
    keys_list = keys.split('.')
    current = dictionary
    
    for key in keys_list[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys_list[-1]] = value