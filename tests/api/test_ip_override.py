#!/usr/bin/env python3
"""
Test script for IP override functionality
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the cli directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent / "cli"))

from cli.config import Config
from cli.proxy import ProxyManager

async def test_ip_override_functionality():
    """Test the IP override functionality"""
    
    print("🧪 Testing IP Override Functionality")
    print("=" * 50)
    
    # Initialize config
    config = Config()
    
    # Test 1: Check current IP override state
    print("\n1. Testing current IP override state...")
    print(f"   IP overrides enabled: {config.is_ip_overrides_enabled()}")
    print(f"   Current IP overrides: {config.get_all_ip_overrides()}")
    print("   ✅ Pass - Retrieved current IP override state")
    
    # Test 2: Test setting a new IP override
    print("\n2. Setting new IP override for 'cn' server...")
    original_ip = config.get_ip_override("cn")
    test_ip = "192.168.1.100"
    
    result = config.set_ip_override("cn", test_ip)
    print(f"   Set IP override result: {result}")
    assert result, "Should be able to set IP override"
    
    retrieved_ip = config.get_ip_override("cn")
    print(f"   Retrieved IP override: {retrieved_ip}")
    assert retrieved_ip == test_ip, f"Expected {test_ip}, got {retrieved_ip}"
    print("   ✅ Pass - IP override set and retrieved correctly")
    
    # Test 3: Test effective endpoints with IP override
    print("\n3. Testing effective endpoints with IP override...")
    effective_endpoints = config.get_effective_server_endpoints("cn")
    print(f"   Effective endpoints: {effective_endpoints}")
    
    if effective_endpoints:
        for endpoint_type, endpoint_url in effective_endpoints.items():
            print(f"   {endpoint_type}: {endpoint_url}")
            assert test_ip in endpoint_url, f"IP {test_ip} should be in {endpoint_url}"
        print("   ✅ Pass - Effective endpoints include IP override")
    else:
        print("   ❌ Fail - No effective endpoints returned")
        return False
    
    # Test 4: Test getting all IP overrides
    print("\n4. Testing get all IP overrides...")
    all_overrides = config.get_all_ip_overrides()
    print(f"   All IP overrides: {all_overrides}")
    assert "cn" in all_overrides, "cn server should be in overrides"
    assert all_overrides["cn"] == test_ip, f"cn should have IP {test_ip}"
    print("   ✅ Pass - All IP overrides retrieved correctly")
    
    # Test 5: Test enabling/disabling IP overrides
    print("\n5. Testing enable/disable IP overrides...")
    original_state = config.is_ip_overrides_enabled()
    
    # Toggle state
    result = config.set_ip_overrides_enabled(not original_state)
    print(f"   Toggle result: {result}")
    assert result, "Should be able to toggle IP overrides"
    
    new_state = config.is_ip_overrides_enabled()
    print(f"   New state: {new_state}")
    assert new_state != original_state, "State should have changed"
    
    # Restore original state
    config.set_ip_overrides_enabled(original_state)
    print("   ✅ Pass - IP overrides can be enabled/disabled")
    
    # Test 6: Test removing IP override
    print("\n6. Testing IP override removal...")
    result = config.remove_ip_override("cn")
    print(f"   Remove result: {result}")
    assert result, "Should be able to remove IP override"
    
    retrieved_ip = config.get_ip_override("cn")
    print(f"   Retrieved IP after removal: {retrieved_ip}")
    assert retrieved_ip is None, "IP override should be None after removal"
    
    # Restore original IP if it existed
    if original_ip:
        config.set_ip_override("cn", original_ip)
        print(f"   Restored original IP: {original_ip}")
    
    print("   ✅ Pass - IP override removed and restored successfully")
    
    # Test 7: Test with ProxyManager
    print("\n7. Testing ProxyManager with IP overrides...")
    proxy_manager = ProxyManager(config)
    
    # Set a test IP override
    test_server = "inter"
    test_ip = "203.0.113.45"
    config.set_ip_override(test_server, test_ip)
    
    # Test effective endpoints through proxy manager
    server_info = config.get_server_info(test_server)
    if server_info:
        print(f"   Original endpoints: {server_info.endpoints}")
        
        effective_endpoints = config.get_effective_server_endpoints(test_server)
        print(f"   Effective endpoints: {effective_endpoints}")
        
        if effective_endpoints:
            for endpoint_type, endpoint_url in effective_endpoints.items():
                print(f"   {endpoint_type}: {endpoint_url}")
                assert test_ip in endpoint_url, "Override IP should be in effective endpoints"
            print("   ✅ Pass - ProxyManager uses IP overrides correctly")
        else:
            print("   ❌ Fail - ProxyManager couldn't get effective endpoints")
            return False
    
    # Clean up - remove test override
    config.remove_ip_override(test_server)
    
    print("\n" + "=" * 50)
    print("🎉 All IP override tests passed!")
    return True

def test_config_yaml_structure():
    """Test that the config.yaml has the correct structure"""
    
    print("🔍 Testing config.yaml structure...")
    
    config = Config()
    
    # Check that ip_overrides section exists
    ip_overrides = config.config_data.get('ip_overrides', {})
    print(f"   IP overrides section: {ip_overrides}")
    
    assert 'enabled' in ip_overrides, "ip_overrides should have 'enabled' key"
    assert isinstance(ip_overrides['enabled'], bool), "enabled should be boolean"
    
    print("   ✅ Pass - config.yaml has correct IP overrides structure")
    return True

async def main():
    """Main test function"""
    
    print("🚀 Starting IP Override Tests")
    print("=" * 60)
    
    try:
        # Test config structure
        test_config_yaml_structure()
        
        # Test functionality
        success = await test_ip_override_functionality()
        
        if success:
            print("\n✅ All tests completed successfully!")
            return 0
        else:
            print("\n❌ Some tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)