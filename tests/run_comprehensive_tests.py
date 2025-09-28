#!/usr/bin/env python3
"""
Comprehensive Test Runner for Anthropic Proxy

This script runs all organized tests in the proper categories:
- Unit Tests: Fast, isolated component tests
- Integration Tests: API endpoint and feature tests
- Benchmarks: Performance and optimization tests

Usage:
  python tests/run_comprehensive_tests.py [unit|integration|benchmarks|all]
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test categories
TEST_CATEGORIES = {
    'unit': {
        'description': 'Unit Tests - Fast isolated component tests',
        'path': 'tests/unit',
        'files': [
            'test_conversion.py',
            'test_detection_detailed.py', 
            'test_image_detection.py',
            'test_model_variants.py'
        ]
    },
    'integration': {
        'description': 'Integration Tests - API endpoints and features',
        'path': 'tests/integration',
        'files': [
            'test_api.py',
            'test_text_api.py',
            'test_image_api.py',
            'test_enhanced_logging.py',
            'test_error_logging.py',
            'test_upstream_logging.py',
            'test_connection_simple.py',
            'test_direct_model.py'
        ]
    },
    'benchmarks': {
        'description': 'Performance Tests - Benchmarks and optimization',
        'path': 'tests/benchmarks',
        'files': [
            'test_performance_logging.py',
            'quick_benchmark.py',
            'comprehensive_benchmark.py'
        ]
    }
}

def check_environment():
    """Check if required environment is set up"""
    print("🔍 Checking Environment")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv("SERVER_API_KEY")
    if not api_key:
        print("❌ SERVER_API_KEY not found in .env file")
        print("   Please ensure .env file exists with SERVER_API_KEY")
        return False
    print(f"✅ API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
    
    # Check if container is running
    try:
        result = subprocess.run(['docker', 'compose', 'ps', '--format', 'json'], 
                              capture_output=True, text=True, check=True)
        if 'anthropic-proxy' in result.stdout:
            print("✅ Container: anthropic-proxy running")
        else:
            print("❌ Container: anthropic-proxy not running")
            print("   Run: docker compose up -d")
            return False
    except subprocess.CalledProcessError:
        print("❌ Docker Compose: Not available")
        return False
    
    # Test connectivity
    try:
        import requests
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Connectivity: http://localhost:5000 accessible")
        else:
            print(f"❌ Connectivity: Health check failed ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Connectivity: Cannot reach http://localhost:5000 ({e})")
        return False
    
    print()
    return True

def run_test_file(test_file, category_path):
    """Run a single test file"""
    full_path = Path(category_path) / test_file
    
    if not full_path.exists():
        return False, f"File not found: {full_path}"
    
    try:
        print(f"  📋 Running {test_file}...")
        start_time = time.time()
        
        result = subprocess.run(
            [sys.executable, str(full_path)],
            capture_output=True, 
            text=True,
            timeout=60
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"     ✅ PASSED ({duration:.1f}s)")
            return True, f"PASSED in {duration:.1f}s"
        else:
            print(f"     ❌ FAILED ({duration:.1f}s)")
            if result.stderr:
                print(f"     Error: {result.stderr.strip()}")
            return False, f"FAILED: {result.stderr.strip()[:100]}"
            
    except subprocess.TimeoutExpired:
        print(f"     ⏰ TIMEOUT (60s)")
        return False, "TIMEOUT after 60s"
    except Exception as e:
        print(f"     💥 ERROR: {e}")
        return False, f"ERROR: {e}"

def run_category_tests(category_name):
    """Run all tests in a category"""
    category = TEST_CATEGORIES[category_name]
    
    print(f"🧪 {category['description']}")
    print("=" * 60)
    
    results = []
    total_tests = 0
    passed_tests = 0
    
    for test_file in category['files']:
        total_tests += 1
        success, details = run_test_file(test_file, category['path'])
        results.append((test_file, success, details))
        if success:
            passed_tests += 1
    
    # Category Summary
    print(f"\n📊 {category_name.upper()} RESULTS: {passed_tests}/{total_tests} passed")
    if passed_tests < total_tests:
        print("   Failed tests:")
        for test_file, success, details in results:
            if not success:
                print(f"   - {test_file}: {details}")
    
    print()
    return passed_tests, total_tests, results

def main():
    """Main test runner"""
    import sys
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        requested = sys.argv[1].lower()
        if requested not in ['unit', 'integration', 'benchmarks', 'all']:
            print(f"❌ Invalid category: {requested}")
            print("   Valid options: unit, integration, benchmarks, all")
            sys.exit(1)
    else:
        requested = 'all'
    
    print("🚀 Comprehensive Test Runner for Anthropic Proxy")
    print("=" * 60)
    print(f"Target: {requested}")
    print()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed. Cannot run tests.")
        sys.exit(1)
    
    # Run tests
    total_passed = 0
    total_tests = 0
    
    if requested == 'all':
        categories = ['unit', 'integration', 'benchmarks']
    else:
        categories = [requested]
    
    for category in categories:
        passed, tests, _ = run_category_tests(category)
        total_passed += passed
        total_tests += tests
    
    # Final summary
    print("🎯 FINAL RESULTS")
    print("=" * 40)
    print(f"Total Passed: {total_passed}/{total_tests}")
    print(f"Success Rate: {(total_passed/total_tests*100):.1f}%")
    
    if total_passed == total_tests:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"❌ {total_tests - total_passed} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()