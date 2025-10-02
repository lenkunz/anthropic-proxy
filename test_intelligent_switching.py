#!/usr/bin/env python3
"""
Test script for intelligent auto-switching functionality

Tests the check-host.net API integration and intelligent endpoint discovery.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cli.config import Config
from cli.proxy import ProxyManager

async def test_endpoint_discovery():
    """Test endpoint discovery using check-host.net API"""
    print("🔍 Testing endpoint discovery...")
    
    config = Config()
    proxy_manager = ProxyManager(config)
    
    # Test with a known domain
    domain = "open.bigmodel.cn"
    endpoints = await proxy_manager.discover_endpoints_with_check_host(domain, max_nodes=3)
    
    if endpoints:
        print(f"✅ Successfully discovered {len(endpoints)} endpoints for {domain}")
        for endpoint in endpoints:
            print(f"   • {endpoint['ip']} ({endpoint['city']}, {endpoint['country']})")
        return True
    else:
        print(f"❌ Failed to discover endpoints for {domain}")
        return False

async def test_endpoint_testing():
    """Test endpoint connectivity with thinking parameter"""
    print("\n🧪 Testing endpoint connectivity...")
    
    config = Config()
    proxy_manager = ProxyManager(config)
    
    # Get international server config
    international_server = config.get_server_info('inter')
    if not international_server:
        print("❌ No international server configured")
        return False
    
    # Test with a sample IP (this would normally come from discovery)
    test_ip = "open.bigmodel.cn"  # Using domain for initial test
    
    result = await proxy_manager.test_endpoint_with_thinking(
        test_ip, 
        "open.bigmodel.cn", 
        international_server.api_key
    )
    
    if result['success']:
        print(f"✅ Endpoint test successful: {result['latency_ms']:.0f}ms")
        return True
    else:
        print(f"❌ Endpoint test failed: {result.get('error', 'Unknown error')}")
        return False

async def test_intelligent_auto_switch():
    """Test intelligent auto-switching logic"""
    print("\n🧠 Testing intelligent auto-switching...")
    
    config = Config()
    proxy_manager = ProxyManager(config)
    
    # Run the intelligent auto-switching check once
    result = await proxy_manager.intelligent_auto_switch_with_discovery()
    
    if result:
        print("✅ Intelligent auto-switching test completed successfully")
        return True
    else:
        print("❌ Intelligent auto-switching test failed")
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Intelligent Auto-Switching Features\n")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if API key is available
    api_key = os.getenv("SERVER_API_KEY")
    if not api_key:
        print("❌ SERVER_API_KEY not found in .env file")
        print("Please ensure your .env file contains a valid API key")
        return False
    
    tests = [
        ("Endpoint Discovery", test_endpoint_discovery),
        ("Endpoint Testing", test_endpoint_testing),
        ("Intelligent Auto-Switch", test_intelligent_auto_switch),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Testing: {test_name}")
        print('='*50)
        
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("🏁 Test Results Summary")
    print('='*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Intelligent auto-switching is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration and API key.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)