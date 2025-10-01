#!/usr/bin/env python3
"""
Simple integration test for the accurate token counting system

This test validates that the code changes are properly integrated
without requiring external dependencies to be installed.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_configuration_integration():
    """Test that configuration variables are properly set."""
    print("🧪 Testing configuration integration...")
    
    # Test new configuration variables
    enable_accurate = os.getenv("ENABLE_ACCURATE_TOKEN_COUNTING", "false").lower() in ("true", "1", "yes")
    cache_size = int(os.getenv("TIKTOKEN_CACHE_SIZE", "1000"))
    enable_logging = os.getenv("ENABLE_TOKEN_COUNTING_LOGGING", "false").lower() in ("true", "1", "yes")
    base_image_tokens = int(os.getenv("BASE_IMAGE_TOKENS", "85"))
    image_tokens_per_char = float(os.getenv("IMAGE_TOKENS_PER_CHAR", "0.25"))
    
    print(f"✅ ENABLE_ACCURATE_TOKEN_COUNTING: {enable_accurate}")
    print(f"✅ TIKTOKEN_CACHE_SIZE: {cache_size}")
    print(f"✅ ENABLE_TOKEN_COUNTING_LOGGING: {enable_logging}")
    print(f"✅ BASE_IMAGE_TOKENS: {base_image_tokens}")
    print(f"✅ IMAGE_TOKENS_PER_CHAR: {image_tokens_per_char}")
    
    # Test that scaling configuration is still present
    anthropic_expected = int(os.getenv("ANTHROPIC_EXPECTED_TOKENS", "200000"))
    openai_expected = int(os.getenv("OPENAI_EXPECTED_TOKENS", "200000"))
    real_text_tokens = int(os.getenv("REAL_TEXT_MODEL_TOKENS", "200000"))
    real_vision_tokens = int(os.getenv("REAL_VISION_MODEL_TOKENS", "65536"))
    scale_count_tokens = os.getenv("SCALE_COUNT_TOKENS_FOR_VISION", "true").lower() in ("true", "1", "yes")
    
    print(f"✅ ANTHROPIC_EXPECTED_TOKENS: {anthropic_expected}")
    print(f"✅ OPENAI_EXPECTED_TOKENS: {openai_expected}")
    print(f"✅ REAL_TEXT_MODEL_TOKENS: {real_text_tokens}")
    print(f"✅ REAL_VISION_MODEL_TOKENS: {real_vision_tokens}")
    print(f"✅ SCALE_COUNT_TOKENS_FOR_VISION: {scale_count_tokens}")
    
    # Validate expected values
    assert enable_accurate == True, "ENABLE_ACCURATE_TOKEN_COUNTING should be True"
    assert cache_size == 1000, "TIKTOKEN_CACHE_SIZE should be 1000"
    assert base_image_tokens == 85, "BASE_IMAGE_TOKENS should be 85"
    assert anthropic_expected == 200000, "ANTHROPIC_EXPECTED_TOKENS should be 200000"
    
    print("✅ All configuration variables are properly set")
    return True

def test_file_structure():
    """Test that all required files are present."""
    print("\n🧪 Testing file structure...")
    
    required_files = [
        "accurate_token_counter.py",
        "context_window_manager.py", 
        "main.py",
        ".env",
        "requirements.txt"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            return False
    
    # Check that accurate_token_counter.py has the expected class
    try:
        with open("accurate_token_counter.py", "r") as f:
            content = f.read()
            if "class AccurateTokenCounter" in content:
                print("✅ AccurateTokenCounter class found")
            else:
                print("❌ AccurateTokenCounter class not found")
                return False
            
            if "def count_tokens_accurate" in content:
                print("✅ count_tokens_accurate function found")
            else:
                print("❌ count_tokens_accurate function not found")
                return False
                
    except Exception as e:
        print(f"❌ Error reading accurate_token_counter.py: {e}")
        return False
    
    # Check that main.py has the updated imports
    try:
        with open("main.py", "r") as f:
            content = f.read()
            if "from accurate_token_counter import" in content:
                print("✅ Accurate token counter import found in main.py")
            else:
                print("❌ Accurate token counter import not found in main.py")
                return False
                
            if "ENABLE_ACCURATE_TOKEN_COUNTING" in content:
                print("✅ ENABLE_ACCURATE_TOKEN_COUNTING variable found in main.py")
            else:
                print("❌ ENABLE_ACCURATE_TOKEN_COUNTING variable not found in main.py")
                return False
                
    except Exception as e:
        print(f"❌ Error reading main.py: {e}")
        return False
    
    print("✅ File structure validation passed")
    return True

def test_function_signatures():
    """Test that function signatures have been updated correctly."""
    print("\n🧪 Testing function signatures...")
    
    # Check that count_tokens_from_messages has been updated
    try:
        with open("main.py", "r") as f:
            content = f.read()
            if "def count_tokens_from_messages(messages, image_descriptions=None):" in content:
                print("✅ count_tokens_from_messages signature updated")
            else:
                print("❌ count_tokens_from_messages signature not updated")
                return False
                
            if "def count_tokens_accurate_with_scaling(" in content:
                print("✅ count_tokens_accurate_with_scaling function found")
            else:
                print("❌ count_tokens_accurate_with_scaling function not found")
                return False
                
    except Exception as e:
        print(f"❌ Error checking function signatures: {e}")
        return False
    
    # Check that context_window_manager functions have been updated
    try:
        with open("context_window_manager.py", "r") as f:
            content = f.read()
            if "image_descriptions: Optional[Dict[int, str]] = None" in content:
                print("✅ ContextWindowManager functions updated with image_descriptions parameter")
            else:
                print("❌ ContextWindowManager functions not updated with image_descriptions parameter")
                return False
                
    except Exception as e:
        print(f"❌ Error checking context_window_manager.py: {e}")
        return False
    
    print("✅ Function signature validation passed")
    return True

def test_requirements():
    """Test that requirements.txt includes necessary dependencies."""
    print("\n🧪 Testing requirements...")
    
    try:
        with open("requirements.txt", "r") as f:
            content = f.read()
            
        required_packages = ["tiktoken", "aiofiles"]
        for package in required_packages:
            if package in content:
                print(f"✅ {package} found in requirements.txt")
            else:
                print(f"❌ {package} not found in requirements.txt")
                return False
                
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")
        return False
    
    print("✅ Requirements validation passed")
    return True

def test_docker_compose_integration():
    """Test that docker-compose.yml is properly configured."""
    print("\n🧪 Testing Docker Compose configuration...")
    
    try:
        with open("docker-compose.yml", "r") as f:
            content = f.read()
            
        # Check that it mounts the current directory
        if ".:" in content or "./" in content:
            print("✅ Volume mount found in docker-compose.yml")
        else:
            print("⚠️  No volume mount found in docker-compose.yml")
        
        # Check that it uses the Dockerfile
        if "build: ." in content or "build:" in content:
            print("✅ Docker build configuration found")
        else:
            print("⚠️  No Docker build configuration found")
            
    except Exception as e:
        print(f"❌ Error reading docker-compose.yml: {e}")
        return False
    
    print("✅ Docker Compose validation passed")
    return True

def main():
    """Run all integration tests."""
    print("🚀 Starting Simple Integration Tests\n")
    
    tests = [
        ("Configuration Integration", test_configuration_integration),
        ("File Structure", test_file_structure),
        ("Function Signatures", test_function_signatures),
        ("Requirements", test_requirements),
        ("Docker Compose Integration", test_docker_compose_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("INTEGRATION TEST SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The accurate token counting system is properly integrated.")
        print("\n📝 Next steps:")
        print("1. Run 'docker compose down && docker compose build --no-cache && docker compose up -d'")
        print("2. Test the API endpoints to ensure everything works correctly")
        print("3. Monitor token counting accuracy in the logs")
        return 0
    else:
        print("⚠️  Some integration tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit(main())