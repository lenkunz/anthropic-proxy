"""
Comprehensive tests for intelligent auto-switching features
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from cli.config import Config, ServerInfo
from cli.proxy import ProxyManager
from cli.stats import StatsCollector


class TestConfig:
    """Test configuration management for intelligent switching"""
    
    def test_dual_endpoint_configuration(self):
        """Test dual endpoint configuration loading"""
        config_data = {
            'servers': {
                'cn': {
                    'endpoints': {
                        'anthropic': 'https://open.bigmodel.cn/api/anthropic',
                        'openai': 'https://open.bigmodel.cn/api/paas/v4'
                    },
                    'api_key': '',
                    'region': 'China'
                },
                'inter': {
                    'endpoints': {
                        'anthropic': 'https://api.z.ai/api/anthropic',
                        'openai': 'https://api.z.ai/api/coding/paas/v4'
                    },
                    'api_key': '',
                    'region': 'International'
                }
            },
            'current_server': 'cn'
        }
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('yaml.safe_load', return_value=config_data):
                with patch('pathlib.Path.exists', return_value=True):
                    config = Config('test_config.yaml')
                    
                    servers = config.get_all_servers()
                    
                    # Test CN server endpoints
                    cn_server = servers['cn']
                    assert cn_server.endpoints['anthropic'] == 'https://open.bigmodel.cn/api/anthropic'
                    assert cn_server.endpoints['openai'] == 'https://open.bigmodel.cn/api/paas/v4'
                    assert cn_server.region == 'China'
                    
                    # Test International server endpoints
                    inter_server = servers['inter']
                    assert inter_server.endpoints['anthropic'] == 'https://api.z.ai/api/anthropic'
                    assert inter_server.endpoints['openai'] == 'https://api.z.ai/api/coding/paas/v4'
                    assert inter_server.region == 'International'
    
    def test_backward_compatibility_single_endpoint(self):
        """Test backward compatibility with single endpoint configuration"""
        config_data = {
            'servers': {
                'cn': {
                    'endpoint': 'https://open.bigmodel.cn/api/paas/v4',
                    'api_key': 'test-key',
                    'region': 'China'
                }
            },
            'current_server': 'cn'
        }
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('yaml.safe_load', return_value=config_data):
                with patch('pathlib.Path.exists', return_value=True):
                    config = Config('test_config.yaml')
                    
                    servers = config.get_all_servers()
                    cn_server = servers['cn']
                    
                    # Should convert single endpoint to dual endpoints
                    assert cn_server.endpoints['anthropic'] == 'https://open.bigmodel.cn/api/paas/v4'
                    assert cn_server.endpoints['openai'] == 'https://open.bigmodel.cn/api/paas/v4'
                    assert cn_server.endpoint == 'https://open.bigmodel.cn/api/paas/v4'
    
    def test_update_server_endpoint_with_dual_endpoints(self):
        """Test updating server endpoints with dual endpoint configuration"""
        config_data = {
            'servers': {
                'inter': {
                    'endpoints': {
                        'anthropic': 'https://api.z.ai/api/anthropic',
                        'openai': 'https://api.z.ai/api/coding/paas/v4'
                    },
                    'api_key': '',
                    'region': 'International'
                }
            },
            'current_server': 'cn'
        }
        
        with patch('builtins.open', create=True) as mock_open:
            with patch('yaml.safe_load', return_value=config_data):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch.object(Config, '_save_config', return_value=True):
                        config = Config('test_config.yaml')
                        
                        # Update with new IP
                        new_endpoint = 'https://123.45.67.89/api/anthropic'
                        result = config.update_server_endpoint('inter', new_endpoint)
                        
                        assert result is True
                        
                        # Check both endpoints were updated with new IP
                        servers = config.get_all_servers()
                        inter_server = servers['inter']
                        assert inter_server.endpoints['anthropic'] == 'https://123.45.67.89/api/anthropic'
                        assert inter_server.endpoints['openai'] == 'https://123.45.67.89/api/coding/paas/v4'


class TestProxyManager:
    """Test proxy manager intelligent switching features"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration"""
        config = MagicMock(spec=Config)
        config.get_all_servers.return_value = {
            'cn': ServerInfo(
                endpoints={
                    'anthropic': 'https://open.bigmodel.cn/api/anthropic',
                    'openai': 'https://open.bigmodel.cn/api/paas/v4'
                },
                api_key='test-key',
                region='China'
            ),
            'inter': ServerInfo(
                endpoints={
                    'anthropic': 'https://api.z.ai/api/anthropic',
                    'openai': 'https://api.z.ai/api/coding/paas/v4'
                },
                api_key='test-key',
                region='International'
            )
        }
        config.get_current_server.return_value = 'cn'
        config.get_server_info.side_effect = lambda name: config.get_all_servers.return_value.get(name)
        return config
    
    @pytest.fixture
    def proxy_manager(self, mock_config):
        """Create a proxy manager with mock configuration"""
        with patch('cli.stats.StatsCollector'):
            return ProxyManager(mock_config)
    
    @pytest.mark.asyncio
    async def test_measure_server_performance_with_dual_endpoints(self, proxy_manager):
        """Test measuring server performance with dual endpoints"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient.get', return_value=mock_response):
            performance = await proxy_manager.measure_server_performance('cn')
            
            assert performance['server'] == 'cn'
            assert performance['success'] is True
            assert 'latency_ms' in performance
            assert performance['endpoint'] == 'https://open.bigmodel.cn/api/paas/v4'  # OpenAI endpoint
    
    @pytest.mark.asyncio
    async def test_discover_endpoints_with_check_host(self, proxy_manager):
        """Test endpoint discovery using check-host.net API"""
        mock_check_response = MagicMock()
        mock_check_response.status_code = 200
        mock_check_response.json.return_value = {'request_id': 'test-id'}
        
        mock_results_response = MagicMock()
        mock_results_response.status_code = 200
        mock_results_response.json.return_value = [
            [
                {
                    'address': '123.45.67.89',
                    'node': {'country': 'US', 'city': 'New York'}
                }
            ],
            [
                {
                    'address': '234.56.78.90',
                    'node': {'country': 'DE', 'city': 'Frankfurt'}
                }
            ]
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Mock the check-host.net API responses
            mock_client_instance.get.side_effect = [
                mock_check_response,  # First call to submit check
                mock_results_response  # Second call to get results
            ]
            
            endpoints = await proxy_manager.discover_endpoints_with_check_host('api.z.ai')
            
            assert len(endpoints) == 2
            assert endpoints[0]['ip'] == '123.45.67.89'
            assert endpoints[0]['country'] == 'US'
            assert endpoints[0]['city'] == 'New York'
            assert endpoints[1]['ip'] == '234.56.78.90'
            assert endpoints[1]['country'] == 'DE'
            assert endpoints[1]['city'] == 'Frankfurt'
    
    @pytest.mark.asyncio
    async def test_test_endpoint_with_thinking(self, proxy_manager):
        """Test endpoint testing with thinking parameter"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': 'OK'
                    }
                }
            ]
        }
        
        with patch('httpx.AsyncClient.post', return_value=mock_response):
            result = await proxy_manager.test_endpoint_with_thinking(
                '123.45.67.89',
                'api.z.ai',
                'test-key'
            )
            
            assert result['ip'] == '123.45.67.89'
            assert result['domain'] == 'api.z.ai'
            assert result['success'] is True
            assert 'latency_ms' in result
    
    @pytest.mark.asyncio
    async def test_intelligent_auto_switch_with_discovery(self, proxy_manager):
        """Test intelligent auto-switching with endpoint discovery"""
        # Mock current server performance (poor)
        with patch.object(proxy_manager, 'measure_server_performance') as mock_measure:
            mock_measure.return_value = {
                'server': 'cn',
                'success': True,
                'latency_ms': 1000,  # High latency
                'endpoint': 'https://open.bigmodel.cn/api/paas/v4'
            }
            
            # Mock stats
            with patch.object(proxy_manager.stats, 'get_current_stats') as mock_stats:
                mock_stats.return_value = {
                    'requests_per_second': 60,  # High load
                    'avg_response_time': 2500  # Slow responses
                }
                
                # Mock endpoint discovery
                with patch.object(proxy_manager, 'discover_endpoints_with_check_host') as mock_discover:
                    mock_discover.return_value = [
                        {'ip': '123.45.67.89', 'country': 'US', 'city': 'New York'},
                        {'ip': '234.56.78.90', 'country': 'DE', 'city': 'Frankfurt'}
                    ]
                    
                    # Mock endpoint testing
                    with patch.object(proxy_manager, 'test_endpoint_with_thinking') as mock_test:
                        mock_test.side_effect = [
                            {
                                'ip': '123.45.67.89',
                                'success': True,
                                'latency_ms': 200  # Much better latency
                            },
                            {
                                'ip': '234.56.78.90',
                                'success': True,
                                'latency_ms': 300
                            }
                        ]
                        
                        # Mock restart
                        with patch.object(proxy_manager, 'restart', return_value=True):
                            result = await proxy_manager.intelligent_auto_switch_with_discovery()
                            
                            assert result is True
                            # Should have called update_server_endpoint with the best IP
                            proxy_manager.config.update_server_endpoint.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_with_intelligent_switching(self, proxy_manager):
        """Test continuous monitoring with intelligent switching"""
        call_count = 0
        
        async def mock_intelligent_switch():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:  # Stop after 2 calls
                raise KeyboardInterrupt()
            return True
        
        with patch.object(proxy_manager, 'intelligent_auto_switch_with_discovery', side_effect=mock_intelligent_switch):
            with patch('asyncio.sleep', side_effect=KeyboardInterrupt()):
                # Should run for 2 iterations then stop
                await proxy_manager.monitor_with_intelligent_switching(interval=1)
                assert call_count == 2


class TestIntegration:
    """Integration tests for intelligent switching"""
    
    @pytest.mark.asyncio
    async def test_full_intelligent_switching_workflow(self):
        """Test the complete intelligent switching workflow"""
        # Create test configuration
        config_data = {
            'servers': {
                'cn': {
                    'endpoints': {
                        'anthropic': 'https://open.bigmodel.cn/api/anthropic',
                        'openai': 'https://open.bigmodel.cn/api/paas/v4'
                    },
                    'api_key': '',
                    'region': 'China'
                },
                'inter': {
                    'endpoints': {
                        'anthropic': 'https://api.z.ai/api/anthropic',
                        'openai': 'https://api.z.ai/api/coding/paas/v4'
                    },
                    'api_key': '',
                    'region': 'International'
                }
            },
            'current_server': 'cn',
            'cli': {
                'auto_switch_enabled': True,
                'auto_switch_interval': 60
            }
        }
        
        with patch('builtins.open', create=True):
            with patch('yaml.safe_load', return_value=config_data):
                with patch('pathlib.Path.exists', return_value=True):
                    with patch.object(Config, '_save_config', return_value=True):
                        config = Config('test_config.yaml')
                        
                        # Create proxy manager
                        with patch('cli.stats.StatsCollector'):
                            proxy_manager = ProxyManager(config)
                            
                            # Mock poor performance for current server
                            with patch.object(proxy_manager, 'measure_server_performance') as mock_measure:
                                mock_measure.return_value = {
                                    'server': 'cn',
                                    'success': True,
                                    'latency_ms': 1000,  # High latency
                                    'endpoint': 'https://open.bigmodel.cn/api/paas/v4'
                                }
                                
                                # Mock stats
                                with patch.object(proxy_manager.stats, 'get_current_stats') as mock_stats:
                                    mock_stats.return_value = {
                                        'requests_per_second': 60,  # High load
                                        'avg_response_time': 2500  # Slow responses
                                    }
                                    
                                    # Mock endpoint discovery
                                    with patch.object(proxy_manager, 'discover_endpoints_with_check_host') as mock_discover:
                                        mock_discover.return_value = [
                                            {'ip': '123.45.67.89', 'country': 'US', 'city': 'New York'}
                                        ]
                                        
                                        # Mock endpoint testing
                                        with patch.object(proxy_manager, 'test_endpoint_with_thinking') as mock_test:
                                            mock_test.return_value = {
                                                'ip': '123.45.67.89',
                                                'success': True,
                                                'latency_ms': 200  # Much better latency
                                            }
                                            
                                            # Mock restart
                                            with patch.object(proxy_manager, 'restart', return_value=True):
                                                # Run intelligent auto-switching
                                                result = await proxy_manager.intelligent_auto_switch_with_discovery()
                                                
                                                # Verify the workflow completed successfully
                                                assert result is True
                                                
                                                # Verify endpoint discovery was called
                                                mock_discover.assert_called_once()
                                                
                                                # Verify endpoint testing was called
                                                mock_test.assert_called_once()
                                                
                                                # Verify server endpoint was updated
                                                assert config.update_server_endpoint.called


if __name__ == "__main__":
    pytest.main([__file__])