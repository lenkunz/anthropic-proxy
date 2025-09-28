#!/usr/bin/env python3
"""
Updated test runner for organized test structure.
Runs tests from the new organized directory structure.
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Load environment from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

def check_environment():
    """Check if the environment is properly configured."""
    api_key = os.getenv("SERVER_API_KEY")
    if not api_key:
        print("❌ ERROR: SERVER_API_KEY not found in .env file")
        print("   Please ensure .env file exists in project root with:")
        print("   SERVER_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ Environment configured (API key: {api_key[:10]}...)")
    return True

def run_python_script(script_path):
    """Run a Python script and return success status."""
    try:
        print(f"\n🧪 Running {script_path}...")
        result = subprocess.run([
            sys.executable, str(script_path)
        ], cwd=project_root, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ {script_path.name} - PASSED")
            if result.stdout.strip():
                # Show last few lines of output
                lines = result.stdout.strip().split('\n')
                for line in lines[-3:]:
                    print(f"   {line}")
            return True
        else:
            print(f"❌ {script_path.name} - FAILED")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {script_path.name} - TIMEOUT")
        return False
    except Exception as e:
        print(f"💥 {script_path.name} - EXCEPTION: {e}")
        return False

def main():
    """Main test runner."""
    print("🚀 ANTHROPIC PROXY TEST RUNNER")
    print("=" * 60)
    
    # Check environment
    if not check_environment():
        return False
    
    # Check if proxy is running
    print("\n🔍 Checking proxy status...")
    try:
        import httpx
        import asyncio
        
        async def check_proxy():
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:5000/v1/models")
                return response.status_code == 200
        
        if asyncio.run(check_proxy()):
            print("✅ Proxy is running")
        else:
            print("❌ Proxy is not responding properly")
            print("   Try: docker compose up -d")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to proxy: {e}")
        print("   Try: docker compose up -d")
        return False
    
    # Define test categories and files
    test_categories = {
        "Unit Tests": [
            "tests/unit/test_model_variants.py",
        ],
        "Integration Tests": [
            "tests/integration/test_messages_endpoint.py",
            "tests/integration/test_api.py",
        ],
        "Performance Benchmarks": [
            "tests/benchmarks/quick_benchmark.py",
        ]
    }
    
    # Run tests by category
    total_tests = 0
    passed_tests = 0
    
    for category, test_files in test_categories.items():
        print(f"\n📂 {category}")
        print("-" * 40)
        
        for test_file in test_files:
            test_path = project_root / test_file
            if test_path.exists():
                total_tests += 1
                if run_python_script(test_path):
                    passed_tests += 1
            else:
                print(f"⚠️  {test_file} - FILE NOT FOUND")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)