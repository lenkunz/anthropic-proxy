"""
Proxy server management and control for the Anthropic Proxy CLI

Provides functionality to start, stop, restart, and monitor the proxy server.
"""

import asyncio
import aiofiles
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import subprocess
import psutil
import httpx
from urllib.parse import urlparse
import logging

from cli.config import Config
from cli.stats import StatsCollector

class ProxyManager:
    """Manages the proxy server lifecycle and monitoring"""
    
    def __init__(self, config: Config):
        self.config = config
        self.stats = StatsCollector(config)
        self.process = None
        self._server_stats = {}  # Cache server performance stats
        self._discovered_endpoints = {}  # Cache discovered endpoints from check-host.net
        self._performance_history = {}  # Track performance over time
        
    async def start(self) -> bool:
        """Start the proxy server"""
        try:
            # Check if already running
            if await self.is_running():
                print("ℹ️  Proxy is already running")
                return True
            
            # Start using docker compose
            cmd = ["docker", "compose", "up", "-d", "--force-recreate"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ Proxy started successfully")
                # Initialize stats collector
                await self.stats.initialize()
                return True
            else:
                print(f"❌ Failed to start proxy: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting proxy: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the proxy server"""
        try:
            # Check if running
            if not await self.is_running():
                print("ℹ️  Proxy is not running")
                return True
            
            # Stop using docker compose
            cmd = ["docker", "compose", "down"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ Proxy stopped successfully")
                return True
            else:
                print(f"❌ Failed to stop proxy: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error stopping proxy: {e}")
            return False
    
    async def restart(self) -> bool:
        """Restart the proxy server"""
        print("🔄 Restarting proxy...")
        stopped = await self.stop()
        if stopped:
            await asyncio.sleep(2)  # Brief pause
            return await self.start()
        return False
    
    async def is_running(self) -> bool:
        """Check if the proxy server is running"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{self.config.host}:{self.config.port}/health")
                return response.status_code == 200
        except:
            return False
    
    async def get_status(self) -> Dict:
        """Get detailed proxy status"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://{self.config.host}:{self.config.port}/health")
                if response.status_code == 200:
                    health_data = response.json()
                    
                    # Get current stats
                    current_stats = await self.stats.get_current_stats()
                    
                    return {
                        'running': True,
                        'host': self.config.host,
                        'port': self.config.port,
                        'uptime': current_stats.get('uptime', 0),
                        'total_requests': current_stats.get('total_requests', 0),
                        'active_connections': current_stats.get('active_connections', 0),
                        'health': health_data
                    }
                else:
                    return {'running': False, 'error': f"HTTP {response.status_code}"}
        except Exception as e:
            return {'running': False, 'error': str(e)}
    
    async def get_logs(self, lines: int = 50) -> List[str]:
        """Get recent proxy logs"""
        try:
            cmd = ["docker", "compose", "logs", "--tail", str(lines), "anthropic-proxy"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logs = stdout.decode().strip().split('\n')
                # Filter out empty lines and return last 'lines' entries
                return [log for log in logs if log.strip()][-lines:]
            else:
                return [f"Error getting logs: {stderr.decode()}"]
                
        except Exception as e:
            return [f"Error getting logs: {e}"]
    
    async def switch_server(self, server_name: str) -> bool:
        """Switch to a different server"""
        try:
            if server_name not in self.config.get_all_servers():
                print(f"❌ Unknown server: {server_name}")
                return False
            
            current_server = self.config.get_current_server()
            if server_name == current_server:
                print(f"ℹ️  Already using server: {server_name}")
                return True
            
            # Update configuration
            self.config.set_current_server(server_name)
            
            # Restart proxy with new server
            print(f"🔄 Switching to server: {server_name}")
            return await self.restart()
            
        except Exception as e:
            print(f"❌ Error switching server: {e}")
            return False
    
    async def measure_server_performance(self, server_name: str) -> Dict:
        """Measure performance of a specific server"""
        if server_name not in self.config.get_all_servers():
            return {'error': f'Unknown server: {server_name}'}
        
        server_info = self.config.get_server_info(server_name)
        
        # Check cache first (cache for 30 seconds)
        cache_key = f"{server_name}_performance"
        current_time = time.time()
        if cache_key in self._server_stats:
            cached_data = self._server_stats[cache_key]
            if current_time - cached_data['timestamp'] < 30:
                return cached_data['data']
        
        try:
            # Test connectivity and latency
            start_time = time.time()
            
            # Check if we're using an IP override and disable SSL verification if so
            effective_endpoints = self.config.get_effective_server_endpoints(server_name)
            using_ip_override = False
            if effective_endpoints:
                endpoint_url = effective_endpoints.get('openai', server_info.endpoint)
                # Check if the endpoint URL contains an IP address instead of a domain
                import re
                ip_pattern = r'^(?:https?://)?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
                if re.match(ip_pattern, endpoint_url):
                    using_ip_override = True
            else:
                endpoint_url = server_info.endpoints.get('openai', server_info.endpoint)
            
            # Configure client with SSL verification settings
            verify_ssl = not using_ip_override
            async with httpx.AsyncClient(timeout=10.0, verify=verify_ssl) as client:
                # Get effective endpoints (with IP overrides applied)
                effective_endpoints = self.config.get_effective_server_endpoints(server_name)
                if effective_endpoints:
                    endpoint_url = effective_endpoints.get('openai', server_info.endpoint)
                else:
                    endpoint_url = server_info.endpoints.get('openai', server_info.endpoint)
                test_url = f"{endpoint_url}/v1/models"
                # Get API key from server config or environment
                api_key = server_info.api_key
                if not api_key:
                    api_key = os.getenv("SERVER_API_KEY", "")
                
                # Skip test if no API key is available
                if not api_key:
                    error_data = {
                        'server': server_name,
                        'endpoint': endpoint_url,
                        'latency_ms': 9999,
                        'status_code': None,
                        'success': False,
                        'timestamp': current_time,
                        'region': server_info.region,
                        'error': 'No API key configured'
                    }
                    self._server_stats[cache_key] = {'data': error_data, 'timestamp': current_time}
                    return error_data
                
                headers = {"Authorization": f"Bearer {api_key}"}
                
                # Add Host header when using IP override for SSL compatibility
                if using_ip_override:
                    original_endpoints = server_info.endpoints.get('openai', server_info.endpoint)
                    from urllib.parse import urlparse
                    parsed_original = urlparse(original_endpoints)
                    headers["Host"] = parsed_original.netloc
                
                response = await client.get(test_url, headers=headers)
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                
                performance_data = {
                    'server': server_name,
                    'endpoint': endpoint_url,
                    'latency_ms': latency_ms,
                    'status_code': response.status_code,
                    'success': response.status_code == 200,
                    'timestamp': current_time,
                    'region': server_info.region,
                    'error': None
                }
                
                # Cache the result
                self._server_stats[cache_key] = {
                    'data': performance_data,
                    'timestamp': current_time
                }
                
                return performance_data
                
        except httpx.TimeoutException:
            # Get effective endpoints (with IP overrides applied)
            effective_endpoints = self.config.get_effective_server_endpoints(server_name)
            if effective_endpoints:
                endpoint_url = effective_endpoints.get('openai', server_info.endpoint)
            else:
                endpoint_url = server_info.endpoints.get('openai', server_info.endpoint)
            error_data = {
                'server': server_name,
                'endpoint': endpoint_url,
                'latency_ms': 9999,
                'status_code': None,
                'success': False,
                'timestamp': current_time,
                'region': server_info.region,
                'error': 'Timeout'
            }
            self._server_stats[cache_key] = {'data': error_data, 'timestamp': current_time}
            return error_data
            
        except Exception as e:
            # Get effective endpoints (with IP overrides applied)
            effective_endpoints = self.config.get_effective_server_endpoints(server_name)
            if effective_endpoints:
                endpoint_url = effective_endpoints.get('openai', server_info.endpoint)
            else:
                endpoint_url = server_info.endpoints.get('openai', server_info.endpoint)
            error_data = {
                'server': server_name,
                'endpoint': endpoint_url,
                'latency_ms': 9999,
                'status_code': None,
                'success': False,
                'timestamp': current_time,
                'region': server_info.region,
                'error': str(e)
            }
            self._server_stats[cache_key] = {'data': error_data, 'timestamp': current_time}
            return error_data
    
    async def measure_all_servers(self) -> List[Dict]:
        """Measure performance of all configured servers"""
        servers = self.config.get_all_servers()
        tasks = []
        
        for server_name in servers.keys():
            task = asyncio.create_task(self.measure_server_performance(server_name))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for result in results:
            if isinstance(result, dict) and 'server' in result:
                valid_results.append(result)
        
        return valid_results
    
    async def get_best_server(self) -> Optional[Dict]:
        """Get the best performing server based on latency and availability"""
        server_performances = await self.measure_all_servers()
        
        # Filter to only successful servers
        successful_servers = [s for s in server_performances if s['success']]
        
        if not successful_servers:
            return None
        
        # Sort by latency (lower is better)
        best_server = min(successful_servers, key=lambda x: x['latency_ms'])
        return best_server
    
    
    async def discover_endpoints_with_check_host(self, domain: str, max_nodes: int = 3) -> List[Dict]:
        """
        Discover multiple IP endpoints for a domain using check-host.net API
        
        Args:
            domain: Domain to discover endpoints for
            max_nodes: Maximum number of nodes to query
            
        Returns:
            List of discovered endpoints with IP addresses and locations
        """
        cache_key = f"check_host_{domain}_{max_nodes}"
        current_time = time.time()
        
        # Cache for 5 minutes
        if cache_key in self._discovered_endpoints:
            cached = self._discovered_endpoints[cache_key]
            if current_time - cached['timestamp'] < 300:
                return cached['endpoints']
        
        try:
            print(f"🔍 Discovering endpoints for {domain} using check-host.net...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Submit DNS check request
                check_url = f"https://check-host.net/check-dns"
                check_params = {
                    'host': domain,
                    'max_nodes': max_nodes
                }
                
                check_response = await client.get(check_url, params=check_params)
                if check_response.status_code != 200:
                    print(f"❌ Failed to submit DNS check: {check_response.status_code}")
                    return []
                
                check_data = check_response.json()
                check_id = check_data.get('request_id')
                if not check_id:
                    print("❌ No check ID received from check-host.net")
                    return []
                
                print(f"📋 DNS check submitted with ID: {check_id}")
                
                # Step 2: Poll for results
                results_url = f"https://check-host.net/check-result/{check_id}"
                
                for attempt in range(30):  # Poll for up to 30 seconds
                    await asyncio.sleep(1)
                    
                    results_response = await client.get(results_url)
                    if results_response.status_code != 200:
                        continue
                    
                    results_data = results_response.json()
                    
                    # Check if we have results from all nodes
                    if len(results_data) >= max_nodes:
                        print(f"✅ Received results from {len(results_data)} nodes")
                        break
                else:
                    print("⚠️  Timeout waiting for DNS check results")
                    results_data = []
                
                # Step 3: Parse results and extract endpoints
                endpoints = []
                for result in results_data:
                    if isinstance(result, list) and len(result) > 0:
                        node_info = result[0]
                        if isinstance(node_info, dict):
                            ip_address = node_info.get('address')
                            node_info_data = node_info.get('node', {})
                            node_country = node_info_data.get('country', 'Unknown')
                            node_city = node_info_data.get('city', 'Unknown')
                            
                            if ip_address:
                                endpoints.append({
                                    'ip': ip_address,
                                    'country': node_country,
                                    'city': node_city,
                                    'domain': domain
                                })
                
                # Cache the results
                self._discovered_endpoints[cache_key] = {
                    'endpoints': endpoints,
                    'timestamp': current_time
                }
                
                print(f"🌍 Discovered {len(endpoints)} endpoints for {domain}:")
                for endpoint in endpoints:
                    print(f"   {endpoint['ip']} ({endpoint['city']}, {endpoint['country']})")
                
                return endpoints
                
        except Exception as e:
            print(f"❌ Error discovering endpoints with check-host.net: {e}")
            return []
    
    async def test_endpoint_with_thinking(self, endpoint_ip: str, domain: str, api_key: str) -> Dict:
        """
        Test a specific endpoint IP with a simple prompt including thinking parameter
        
        Args:
            endpoint_ip: IP address to test
            domain: Original domain for SSL verification
            api_key: API key for authentication
            
        Returns:
            Performance metrics for the endpoint
        """
        try:
            # Construct endpoint URL with IP
            server_info = self.config.get_server_info('inter')
            # Get effective endpoints (with IP overrides applied)
            effective_endpoints = self.config.get_effective_server_endpoints('inter')
            if effective_endpoints:
                openai_endpoint = effective_endpoints.get('openai', server_info.endpoint)
            else:
                openai_endpoint = server_info.endpoints.get('openai', server_info.endpoint)
            parsed_url = urlparse(openai_endpoint)
            endpoint_url = f"{parsed_url.scheme}://{endpoint_ip}{parsed_url.path}"
            
            print(f"🧪 Testing endpoint {endpoint_ip} with thinking prompt...")
            
            # Always disable SSL verification when testing with specific IP addresses
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                # Use the exact same request format that works
                # Get API key from server config or environment
                if not api_key:
                    api_key = os.getenv("SERVER_API_KEY", "")
                
                # Skip test if no API key is available
                if not api_key:
                    print(f"⚠️  No API key configured for endpoint testing")
                    return {
                        'ip': endpoint_ip,
                        'domain': domain,
                        'endpoint_url': endpoint_url,
                        'latency_ms': 9999,
                        'success': False,
                        'error': 'No API key configured',
                        'timestamp': time.time()
                    }
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Add Host header for SSL compatibility when using IP address
                from urllib.parse import urlparse
                parsed_original = urlparse(openai_endpoint)
                headers["Host"] = parsed_original.netloc
                
                # Simple test payload with thinking parameter
                test_payload = {
                    "model": "glm-4.6",
                    "messages": [
                        {
                            "role": "user", 
                            "content": "Respond with just 'OK'"
                        }
                    ],
                    "max_tokens": 10,
                    "thinking": True
                }
                
                start_time = time.time()
                response = await client.post(
                    f"{endpoint_url}/v1/chat/completions",
                    headers=headers,
                    json=test_payload
                )
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                
                success = response.status_code == 200
                error_message = None
                
                if success:
                    try:
                        result = response.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        if 'OK' in content:
                            print(f"✅ Endpoint {endpoint_ip} responsive: {content}")
                        else:
                            print(f"⚠️  Unexpected response from {endpoint_ip}: {content}")
                    except:
                        print(f"⚠️  Invalid JSON response from {endpoint_ip}")
                else:
                    error_message = f"HTTP {response.status_code}"
                    if response.status_code == 401:
                        error_message += " (Unauthorized - check API key)"
                    elif response.status_code == 400:
                        try:
                            error_detail = response.json().get('error', {}).get('message', 'Bad Request')
                            error_message += f" - {error_detail}"
                        except:
                            pass
                    
                    # Print response text for debugging
                    try:
                        response_text = response.text[:200]
                        if response_text:
                            error_message += f" - Response: {response_text}"
                    except:
                        pass
                    
                    print(f"❌ Endpoint {endpoint_ip} failed: {error_message}")
                
                return {
                    'ip': endpoint_ip,
                    'domain': domain,
                    'endpoint_url': endpoint_url,
                    'latency_ms': latency_ms,
                    'success': success,
                    'error': error_message,
                    'timestamp': time.time()
                }
                
        except httpx.TimeoutException:
            print(f"⏱️  Timeout testing endpoint {endpoint_ip}")
            return {
                'ip': endpoint_ip,
                'domain': domain,
                'endpoint_url': f"https://{endpoint_ip}",
                'latency_ms': 9999,
                'success': False,
                'error': 'Timeout',
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"❌ Error testing endpoint {endpoint_ip}: {e}")
            return {
                'ip': endpoint_ip,
                'domain': domain,
                'endpoint_url': f"https://{endpoint_ip}",
                'latency_ms': 9999,
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    

class ProxyHealthChecker:
    """Health checking for proxy endpoints"""
    
    def __init__(self, proxy_manager: ProxyManager):
        self.proxy_manager = proxy_manager
    
    async def check_all_endpoints(self) -> Dict[str, Dict]:
        """Check health of all proxy endpoints"""
        results = {}
        
        # Check main proxy health
        proxy_status = await self.proxy_manager.get_status()
        results['proxy'] = proxy_status
        
        # Check upstream servers
        server_performances = await self.proxy_manager.measure_all_servers()
        results['upstream_servers'] = {
            perf['server']: perf for perf in server_performances
        }
        
        return results
    
    async def run_health_check_loop(self, interval: int = 30):
        """Run continuous health checks"""
        print(f"🏥 Starting health check loop with {interval}s intervals...")
        
        while True:
            try:
                health_results = await self.check_all_endpoints()
                
                # Print summary
                proxy_running = health_results['proxy'].get('running', False)
                print(f"\n📊 Health Check - {datetime.now().strftime('%H:%M:%S')}")
                print(f"   Proxy: {'🟢 Running' if proxy_running else '🔴 Down'}")
                
                for server_name, perf in health_results['upstream_servers'].items():
                    status = '🟢' if perf['success'] else '🔴'
                    latency = f"{perf['latency_ms']:.0f}ms" if perf['success'] else 'Timeout'
                    print(f"   {server_name}: {status} {latency}")
                
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n⏹️  Health checking stopped")
                break
            except Exception as e:
                print(f"❌ Health check error: {e}")
                await asyncio.sleep(interval)
    async def discover_endpoints_with_check_host(self, domain: str, max_nodes: int = 3) -> List[Dict]:
        """
        Discover multiple IP endpoints for a domain using check-host.net API
        
        Args:
            domain: Domain to discover endpoints for
            max_nodes: Maximum number of nodes to query
            
        Returns:
            List of discovered endpoints with IP addresses and locations
        """
        cache_key = f"check_host_{domain}_{max_nodes}"
        current_time = time.time()
        
        # Cache for 5 minutes
        if cache_key in self._discovered_endpoints:
            cached = self._discovered_endpoints[cache_key]
            if current_time - cached['timestamp'] < 300:
                return cached['endpoints']
        
        try:
            print(f"🔍 Discovering endpoints for {domain} using check-host.net...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Submit DNS check request
                check_url = f"https://check-host.net/check-dns"
                check_params = {
                    'host': domain,
                    'max_nodes': max_nodes
                }
                
                check_response = await client.get(check_url, params=check_params)
                if check_response.status_code != 200:
                    print(f"❌ Failed to submit DNS check: {check_response.status_code}")
                    return []
                
                check_data = check_response.json()
                check_id = check_data.get('request_id')
                if not check_id:
                    print("❌ No check ID received from check-host.net")
                    return []
                
                print(f"📋 DNS check submitted with ID: {check_id}")
                
                # Step 2: Poll for results
                results_url = f"https://check-host.net/check-result/{check_id}"
                
                for attempt in range(30):  # Poll for up to 30 seconds
                    await asyncio.sleep(1)
                    
                    results_response = await client.get(results_url)
                    if results_response.status_code != 200:
                        continue
                    
                    results_data = results_response.json()
                    
                    # Check if we have results from all nodes
                    if len(results_data) >= max_nodes:
                        print(f"✅ Received results from {len(results_data)} nodes")
                        break
                else:
                    print("⚠️  Timeout waiting for DNS check results")
                    results_data = []
                
                # Step 3: Parse results and extract endpoints
                endpoints = []
                for result in results_data:
                    if isinstance(result, list) and len(result) > 0:
                        node_info = result[0]
                        if isinstance(node_info, dict):
                            ip_address = node_info.get('address')
                            node_info_data = node_info.get('node', {})
                            node_country = node_info_data.get('country', 'Unknown')
                            node_city = node_info_data.get('city', 'Unknown')
                            
                            if ip_address:
                                endpoints.append({
                                    'ip': ip_address,
                                    'country': node_country,
                                    'city': node_city,
                                    'domain': domain
                                })
                
                # Cache the results
                self._discovered_endpoints[cache_key] = {
                    'endpoints': endpoints,
                    'timestamp': current_time
                }
                
                print(f"🌍 Discovered {len(endpoints)} endpoints for {domain}:")
                for endpoint in endpoints:
                    print(f"   {endpoint['ip']} ({endpoint['city']}, {endpoint['country']})")
                
                return endpoints
                
        except Exception as e:
            print(f"❌ Error discovering endpoints with check-host.net: {e}")
            return []
    
    async def test_endpoint_with_thinking(self, endpoint_ip: str, domain: str, api_key: str) -> Dict:
        """
        Test a specific endpoint IP with a simple prompt including thinking parameter
        
        Args:
            endpoint_ip: IP address to test
            domain: Original domain for SSL verification
            api_key: API key for authentication
            
        Returns:
            Performance metrics for the endpoint
        """
        try:
            # Construct endpoint URL with IP
            server_info = self.config.get_server_info('inter')
            # Get effective endpoints (with IP overrides applied)
            effective_endpoints = self.config.get_effective_server_endpoints('inter')
            if effective_endpoints:
                openai_endpoint = effective_endpoints.get('openai', server_info.endpoint)
            else:
                openai_endpoint = server_info.endpoints.get('openai', server_info.endpoint)
            parsed_url = urlparse(openai_endpoint)
            endpoint_url = f"{parsed_url.scheme}://{endpoint_ip}{parsed_url.path}"
            
            print(f"🧪 Testing endpoint {endpoint_ip} with thinking prompt...")
            
            # Always disable SSL verification when testing with specific IP addresses
            async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
                # Use the exact same request format that works
                # Get API key from server config or environment
                if not api_key:
                    api_key = os.getenv("SERVER_API_KEY", "")
                
                # Skip test if no API key is available
                if not api_key:
                    print(f"⚠️  No API key configured for endpoint testing")
                    return {
                        'ip': endpoint_ip,
                        'domain': domain,
                        'endpoint_url': endpoint_url,
                        'latency_ms': 9999,
                        'success': False,
                        'error': 'No API key configured',
                        'timestamp': time.time()
                    }
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                # Add Host header for SSL compatibility when using IP address
                from urllib.parse import urlparse
                parsed_original = urlparse(openai_endpoint)
                headers["Host"] = parsed_original.netloc
                
                # Simple test payload with thinking parameter
                test_payload = {
                    "model": "glm-4.6",
                    "messages": [
                        {
                            "role": "user", 
                            "content": "Respond with just 'OK'"
                        }
                    ],
                    "max_tokens": 10,
                    "thinking": True
                }
                
                start_time = time.time()
                response = await client.post(
                    f"{endpoint_url}/v1/chat/completions",
                    headers=headers,
                    json=test_payload
                )
                end_time = time.time()
                
                latency_ms = (end_time - start_time) * 1000
                
                success = response.status_code == 200
                error_message = None
                
                if success:
                    try:
                        result = response.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        if 'OK' in content:
                            print(f"✅ Endpoint {endpoint_ip} responsive: {content}")
                        else:
                            print(f"⚠️  Unexpected response from {endpoint_ip}: {content}")
                    except:
                        print(f"⚠️  Invalid JSON response from {endpoint_ip}")
                else:
                    error_message = f"HTTP {response.status_code}"
                    if response.status_code == 401:
                        error_message += " (Unauthorized - check API key)"
                    elif response.status_code == 400:
                        try:
                            error_detail = response.json().get('error', {}).get('message', 'Bad Request')
                            error_message += f" - {error_detail}"
                        except:
                            pass
                    
                    # Print response text for debugging
                    try:
                        response_text = response.text[:200]
                        if response_text:
                            error_message += f" - Response: {response_text}"
                    except:
                        pass
                    
                    print(f"❌ Endpoint {endpoint_ip} failed: {error_message}")
                
                return {
                    'ip': endpoint_ip,
                    'domain': domain,
                    'endpoint_url': endpoint_url,
                    'latency_ms': latency_ms,
                    'success': success,
                    'error': error_message,
                    'timestamp': time.time()
                }
                
        except httpx.TimeoutException:
            print(f"⏱️  Timeout testing endpoint {endpoint_ip}")
            return {
                'ip': endpoint_ip,
                'domain': domain,
                'endpoint_url': f"https://{endpoint_ip}",
                'latency_ms': 9999,
                'success': False,
                'error': 'Timeout',
                'timestamp': time.time()
            }
        except Exception as e:
            print(f"❌ Error testing endpoint {endpoint_ip}: {e}")
            return {
                'ip': endpoint_ip,
                'domain': domain,
                'endpoint_url': f"https://{endpoint_ip}",
                'latency_ms': 9999,
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def intelligent_auto_switch_with_discovery(self) -> bool:
        """
        Intelligent auto-switching using check-host.net endpoint discovery
        and thinking-based testing
        """
        current_server = self.config.get_current_server()
        
        # Get current server performance
        current_stats = await self.stats.get_current_stats()
        current_performance = await self.measure_server_performance(current_server)
        
        # Calculate current server load (requests per second)
        requests_per_second = current_stats.get('requests_per_second', 0)
        avg_response_time = current_stats.get('avg_response_time', 0)
        
        print(f"📊 Current server {current_server}:")
        print(f"   Latency: {current_performance['latency_ms']:.0f}ms")
        print(f"   Load: {requests_per_second:.1f} req/s")
        print(f"   Avg Response: {avg_response_time:.0f}ms")
        
        # Check if we need to search for better endpoints
        need_search = (
            not current_performance['success'] or  # Current server failing
            current_performance['latency_ms'] > 800 or  # High latency
            requests_per_second > 50 or  # High load
            avg_response_time > 2000  # Slow responses
        )
        
        if not need_search:
            print("✅ Current server performance is acceptable")
            return True
        
        print(f"🔍 Performance issues detected, searching for better endpoints...")
        
        # Get international server info for domain extraction
        international_server = self.config.get_server_info('inter')
        if not international_server:
            print("❌ No international server configured")
            return False
        
        # Extract domain from endpoint
        openai_endpoint = international_server.endpoints.get('openai', international_server.endpoint)
        parsed_url = urlparse(openai_endpoint)
        domain = parsed_url.netloc
        
        # Discover endpoints using check-host.net
        discovered_endpoints = await self.discover_endpoints_with_check_host(domain, max_nodes=5)
        
        if not discovered_endpoints:
            print("❌ No alternative endpoints discovered")
            return False
        
        # Test discovered endpoints with thinking parameter
        print(f"🧪 Testing {len(discovered_endpoints)} discovered endpoints...")
        test_tasks = []
        
        for endpoint in discovered_endpoints:
            # Get API key from server config or environment
            api_key = international_server.api_key
            if not api_key:
                api_key = os.getenv("SERVER_API_KEY", "")
            
            task = asyncio.create_task(
                self.test_endpoint_with_thinking(
                    endpoint['ip'], 
                    domain, 
                    api_key
                )
            )
            test_tasks.append(task)
        
        test_results = await asyncio.gather(*test_tasks, return_exceptions=True)
        
        # Filter successful tests
        successful_endpoints = []
        for result in test_results:
            if isinstance(result, dict) and result['success']:
                successful_endpoints.append(result)
        
        if not successful_endpoints:
            print("❌ No alternative endpoints passed the thinking test")
            return False
        
        # Find best performing endpoint
        best_endpoint = min(successful_endpoints, key=lambda x: x['latency_ms'])
        
        print(f"🏆 Best alternative endpoint found:")
        print(f"   IP: {best_endpoint['ip']} ({best_endpoint['ip']})")
        print(f"   Latency: {best_endpoint['latency_ms']:.0f}ms")
        
        # Compare with current server
        improvement_needed = 0.8  # Need at least 20% improvement
        
        should_switch = (
            not current_performance['success'] or
            best_endpoint['latency_ms'] < current_performance['latency_ms'] * improvement_needed
        )
        
        if should_switch:
            print(f"🔄 Switching to better endpoint: {best_endpoint['ip']}")
            
            # Update international server configuration with new IP
            new_endpoint_url = f"{parsed_url.scheme}://{best_endpoint['ip']}{parsed_url.path}"
            self.config.update_server_endpoint('inter', new_endpoint_url)
            
            # Restart proxy with new endpoint
            return await self.restart()
        else:
            print(f"✅ Current server is still better ({current_performance['latency_ms']:.0f}ms vs {best_endpoint['latency_ms']:.0f}ms)")
            return True
    
    async def monitor_with_intelligent_switching(self, interval: int = 120):
        """
        Continuous monitoring with intelligent auto-switching using endpoint discovery
        """
        print(f"🧠 Starting intelligent auto-monitoring with {interval}s intervals...")
        print("💡 Uses check-host.net for endpoint discovery and thinking-based testing")
        print("⚡ Switches automatically when performance degrades")
        
        while True:
            try:
                await self.intelligent_auto_switch_with_discovery()
                await asyncio.sleep(interval)
            except KeyboardInterrupt:
                print("\n⏹️  Intelligent monitoring stopped")
                break
            except Exception as e:
                print(f"❌ Error in intelligent monitoring: {e}")
                await asyncio.sleep(interval)