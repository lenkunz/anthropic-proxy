"""
Configuration management for the Anthropic Proxy CLI

Handles loading and managing configuration for servers, CLI settings, and API keys.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urlparse

@dataclass
class ServerInfo:
    """Information about a server configuration"""
    endpoints: Dict[str, str]  # anthropic and openai endpoints
    api_key: str
    region: str
    latency_ms: float = 0.0
    
    def __post_init__(self):
        # Handle both old and new configuration formats
        if isinstance(self.endpoints, str):
            # Old format - single endpoint, convert to dual endpoints
            endpoint_url = self.endpoints
            self.endpoints = {
                'anthropic': endpoint_url,
                'openai': endpoint_url
            }
        elif isinstance(self.endpoints, dict):
            # New format - ensure both endpoints exist
            if 'anthropic' not in self.endpoints:
                self.endpoints['anthropic'] = list(self.endpoints.values())[0]
            if 'openai' not in self.endpoints:
                self.endpoints['openai'] = list(self.endpoints.values())[0]
        
        # Ensure endpoints have proper format
        for endpoint_type, endpoint_url in self.endpoints.items():
            if not endpoint_url.startswith(('http://', 'https://')):
                self.endpoints[endpoint_type] = f'https://{endpoint_url}'
    
    @property
    def endpoint(self) -> str:
        """Get the primary endpoint (for backward compatibility)"""
        return self.endpoints.get('anthropic', '')

class Config:
    """Configuration manager for the CLI"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = Path(config_file)
        self.config_data = {}
        self._load_config()
        
        # Proxy server settings
        self.host = os.getenv("PROXY_HOST", "0.0.0.0")
        self.port = int(os.getenv("PROXY_PORT", "5000"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_stats = os.getenv("ENABLE_STATS", "true").lower() in ("true", "1", "yes")
    
    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self.config_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")
                self.config_data = {}
        else:
            # Create default config
            self._create_default_config()
    
    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            'servers': {
                'inter': {
                    'endpoints': {
                        'anthropic': 'https://api.z.ai/api/anthropic',
                        'openai': 'https://api.z.ai/api/coding/paas/v4'
                    },
                    'api_key': '',
                    'region': 'International'
                },
                'cn': {
                    'endpoints': {
                        'anthropic': 'https://open.bigmodel.cn/api/anthropic',
                        'openai': 'https://open.bigmodel.cn/api/paas/v4'
                    },
                    'api_key': '',
                    'region': 'China'
                }
            },
            'current_server': 'cn',
            'cli': {
                'refresh_interval': 2,
                'auto_switch_enabled': False,
                'auto_switch_interval': 60
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False)
            self.config_data = default_config
        except Exception as e:
            print(f"Warning: Failed to create config file: {e}")
            self.config_data = default_config
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
        except Exception as e:
            print(f"Error: Failed to save config file: {e}")
            return False
        return True
    
    def get_all_servers(self) -> Dict[str, ServerInfo]:
        """Get all configured servers"""
        servers = {}
        servers_config = self.config_data.get('servers', {})
        
        for name, config in servers_config.items():
            # Handle new dual endpoint format
            endpoints = config.get('endpoints', config.get('endpoint', ''))
            
            servers[name] = ServerInfo(
                endpoints=endpoints,
                api_key=config.get('api_key', ''),
                region=config.get('region', 'Unknown'),
                latency_ms=config.get('latency_ms', 0.0)
            )
        
        return servers
    
    def get_server_info(self, server_name: str) -> Optional[ServerInfo]:
        """Get information about a specific server"""
        servers = self.get_all_servers()
        return servers.get(server_name)
    
    def get_current_server(self) -> str:
        """Get the currently selected server name"""
        return self.config_data.get('current_server', 'cn')
    
    def set_current_server(self, server_name: str) -> bool:
        """Set the current server (for no-restart switching)"""
        if server_name not in self.get_all_servers():
            return False
        
        self.config_data['current_server'] = server_name
        return self._save_config()
    
    def add_server(self, name: str, endpoints: Dict[str, str], api_key: str, region: str = "Unknown") -> bool:
        """Add a new server configuration"""
        if 'servers' not in self.config_data:
            self.config_data['servers'] = {}
        
        self.config_data['servers'][name] = {
            'endpoints': endpoints,
            'api_key': api_key,
            'region': region,
            'latency_ms': 0.0
        }
        
        return self._save_config()
    
    def remove_server(self, name: str) -> bool:
        """Remove a server configuration"""
        if name not in self.config_data.get('servers', {}):
            return False
        
        # Don't allow removing the current server
        if self.get_current_server() == name:
            return False
        
        del self.config_data['servers'][name]
        return self._save_config()
    
    def update_server_latency(self, server_name: str, latency_ms: float):
        """Update the recorded latency for a server"""
        if server_name in self.config_data.get('servers', {}):
            self.config_data['servers'][server_name]['latency_ms'] = latency_ms
            # Save in background (fire and forget)
            try:
                import asyncio
                asyncio.create_task(asyncio.to_thread(self._save_config))
            except:
                pass  # Don't let this break anything
    
    def update_server_endpoint(self, server_name: str, new_endpoint: str) -> bool:
        """Update the endpoint URL for a server"""
        if server_name not in self.config_data.get('servers', {}):
            return False
        
        server_config = self.config_data['servers'][server_name]
        
        # Handle both old and new configuration formats
        if 'endpoints' in server_config:
            # New format - update both endpoints with the new IP
            old_endpoints = server_config['endpoints']
            new_endpoints = {}
            
            for endpoint_type, old_endpoint in old_endpoints.items():
                parsed_old = urlparse(old_endpoint)
                parsed_new = urlparse(new_endpoint)
                # Replace the IP/hostname but keep the path
                new_endpoint_url = f"{parsed_new.scheme}://{parsed_new.netloc}{parsed_old.path}"
                new_endpoints[endpoint_type] = new_endpoint_url
            
            server_config['endpoints'] = new_endpoints
        else:
            # Old format - update single endpoint
            server_config['endpoint'] = new_endpoint
        
        return self._save_config()
    
    def get_cli_setting(self, key: str, default=None):
        """Get a CLI configuration setting"""
        return self.config_data.get('cli', {}).get(key, default)
    
    def set_cli_setting(self, key: str, value) -> bool:
        """Set a CLI configuration setting"""
        if 'cli' not in self.config_data:
            self.config_data['cli'] = {}
        
        self.config_data['cli'][key] = value
        return self._save_config()
    
    def get_refresh_interval(self) -> int:
        """Get the status refresh interval"""
        return self.get_cli_setting('refresh_interval', 2)
    
    def set_refresh_interval(self, interval: int) -> bool:
        """Set the status refresh interval"""
        return self.set_cli_setting('refresh_interval', interval)
    
    def is_auto_switch_enabled(self) -> bool:
        """Check if auto-switching is enabled"""
        return self.get_cli_setting('auto_switch_enabled', False)
    
    def set_auto_switch_enabled(self, enabled: bool) -> bool:
        """Enable or disable auto-switching"""
        return self.set_cli_setting('auto_switch_enabled', enabled)
    
    def get_auto_switch_interval(self) -> int:
        """Get the auto-switching interval in seconds"""
        return self.get_cli_setting('auto_switch_interval', 60)
    
    def set_auto_switch_interval(self, interval: int) -> bool:
        """Set the auto-switching interval in seconds"""
        return self.set_cli_setting('auto_switch_interval', interval)
    
    def export_config(self, filename: str) -> bool:
        """Export configuration to a file"""
        try:
            export_data = {
                'config': self.config_data,
                'proxy_settings': {
                    'host': self.host,
                    'port': self.port,
                    'log_level': self.log_level,
                    'enable_stats': self.enable_stats
                }
            }
            
            with open(filename, 'w') as f:
                if filename.endswith('.json'):
                    json.dump(export_data, f, indent=2)
                else:
                    yaml.dump(export_data, f, default_flow_style=False)
            
            return True
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False
    
    def import_config(self, filename: str) -> bool:
        """Import configuration from a file"""
        try:
            with open(filename, 'r') as f:
                if filename.endswith('.json'):
                    import_data = json.load(f)
                else:
                    import_data = yaml.safe_load(f)
            
            if 'config' in import_data:
                self.config_data = import_data['config']
                self._save_config()
            
            if 'proxy_settings' in import_data:
                proxy_settings = import_data['proxy_settings']
                # Update environment variables or other settings as needed
                # This would require additional implementation based on how proxy settings are used
            
            return True
        except Exception as e:
            print(f"Error importing config: {e}")
            return False
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate the configuration and return any issues"""
        issues = []
        
        # Check servers
        servers = self.get_all_servers()
        if not servers:
            issues.append("No servers configured")
        
        for name, server in servers.items():
            if not server.endpoint:
                issues.append(f"Server '{name}' has no endpoint")
            if not server.api_key:
                issues.append(f"Server '{name}' has no API key")
        
        # Check current server
        current = self.get_current_server()
        if current not in servers:
            issues.append(f"Current server '{current}' is not configured")
        
        # Check CLI settings
        refresh_interval = self.get_refresh_interval()
        if refresh_interval < 1:
            issues.append("Refresh interval must be at least 1 second")
        
        auto_switch_interval = self.get_auto_switch_interval()
        if auto_switch_interval < 10:
            issues.append("Auto-switch interval must be at least 10 seconds")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'servers_count': len(servers),
            'current_server': current
        }
    
    def get_config_summary(self) -> str:
        """Get a human-readable summary of the configuration"""
        servers = self.get_all_servers()
        current = self.get_current_server()
        validation = self.validate_config()
        
        summary = f"Configuration Summary:\n"
        summary += f"  Current Server: {current}\n"
        summary += f"  Total Servers: {len(servers)}\n"
        summary += f"  Auto-Switch: {'Enabled' if self.is_auto_switch_enabled() else 'Disabled'}\n"
        summary += f"  Refresh Interval: {self.get_refresh_interval()}s\n"
        
        if not validation['valid']:
            summary += f"  Issues: {len(validation['issues'])}\n"
        
        return summary