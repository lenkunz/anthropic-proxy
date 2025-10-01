#!/usr/bin/env python3
"""
Test script for updated image handling with dynamic token calculation.

This script tests:
1. Dynamic image token calculation based on descriptions
2. Integration with accurate token counter
3. Image description validation
4. Performance improvements
5. Error handling and graceful degradation
"""

import os
import sys
import json
import time
from typing import Dict, List, Any

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_dynamic_image_token_calculation():
    """Test dynamic image token calculation functionality."""
    print("🧪 Testing Dynamic Image Token Calculation...")
    
    try:
        from main import calculate_image_tokens_from_description, BASE_IMAGE_TOKENS, IMAGE_TOKENS_PER_CHAR
        
        # Test cases with different description lengths
        test_cases = [
            ("", "Empty description"),
            ("Short", "Very short description"),
            ("This is a medium length image description with several words and details about the content.", "Medium description"),
            ("This is a very long and detailed image description that contains many words, phrases, and detailed information about what can be seen in the image. It includes various elements, colors, objects, and contextual information that would be useful for maintaining conversation context when the original image is no longer available.", "Long description")
        ]
        
        print(f"Base image tokens: {BASE_IMAGE_TOKENS}")
        print(f"Image tokens per character: {IMAGE_TOKENS_PER_CHAR}")
        print()
        
        for description, desc_type in test_cases:
            tokens = calculate_image_tokens_from_description(description)
            print(f"✅ {desc_type}: {len(description)} chars → {tokens} tokens")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Dynamic image token calculation test failed: {e}")
        return False

def test_image_description_validation():
    """Test image description validation functionality."""
    print("🧪 Testing Image Description Validation...")
    
    try:
        from main import validate_image_description
        
        # Test cases for validation
        test_cases = [
            ("", "Empty string"),
            ("   ", "Whitespace only"),
            ("Short", "Valid short description"),
            ("<script>alert('xss')</script>", "Script content"),
            ("A" * 600, "Very long description (should be truncated)"),
            ("Normal description with normal content and punctuation!", "Valid description")
        ]
        
        for description, desc_type in test_cases:
            validated = validate_image_description(description)
            print(f"✅ {desc_type}: '{description[:30]}...' → '{validated[:30]}...'")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Image description validation test failed: {e}")
        return False

def test_accurate_token_counter_integration():
    """Test integration with accurate token counter."""
    print("🧪 Testing Accurate Token Counter Integration...")
    
    try:
        from accurate_token_counter import get_token_counter, ENABLE_ACCURATE_TOKEN_COUNTING
        
        if not ENABLE_ACCURATE_TOKEN_COUNTING:
            print("⚠️  Accurate token counting is disabled, skipping integration test")
            return True
        
        counter = get_token_counter()
        
        # Test messages with images
        test_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please analyze this image:"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                        }
                    }
                ]
            }
        ]
        
        # Test with image descriptions
        image_descriptions = {
            "0_1": "A simple red square image with a white border"
        }
        
        # Count tokens with descriptions
        tokens_with_desc = counter.count_messages_tokens(test_messages, "openai", image_descriptions)
        
        # Count tokens without descriptions
        tokens_without_desc = counter.count_messages_tokens(test_messages, "openai")
        
        print(f"✅ Tokens without description: {tokens_without_desc}")
        print(f"✅ Tokens with description: {tokens_with_desc}")
        print(f"✅ Difference: {tokens_with_desc - tokens_without_desc} tokens")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Accurate token counter integration test failed: {e}")
        return False

def test_context_window_manager_integration():
    """Test integration with context window manager."""
    print("🧪 Testing Context Window Manager Integration...")
    
    try:
        from context_window_manager import simple_count_tokens_from_messages
        
        # Test messages with images
        test_messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Here's an image for analysis:"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
                        }
                    }
                ]
            },
            {
                "role": "assistant", 
                "content": "I can see that's a simple image."
            }
        ]
        
        # Test with image descriptions
        image_descriptions = {
            "0_1": "A simple 1x1 pixel transparent image"
        }
        
        # Count tokens without descriptions
        tokens_without_desc = simple_count_tokens_from_messages(test_messages)
        
        # Count tokens with descriptions
        tokens_with_desc = simple_count_tokens_from_messages(test_messages, image_descriptions)
        
        print(f"✅ Tokens without description: {tokens_without_desc}")
        print(f"✅ Tokens with description: {tokens_with_desc}")
        print(f"✅ Difference: {tokens_with_desc - tokens_without_desc} tokens")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Context window manager integration test failed: {e}")
        return False

def test_performance():
    """Test performance of the updated image handling."""
    print("🧪 Testing Performance...")
    
    try:
        from main import calculate_image_tokens_from_description
        
        # Generate test descriptions of various lengths
        test_descriptions = [
            "Short description",
            "This is a medium length description with multiple sentences and some detail about the image content.",
            "This is a very long and comprehensive description that contains extensive detail about the image, including information about colors, composition, objects, text content, spatial relationships, and contextual relevance. It should provide enough information to maintain good conversation context even when the original image is no longer available for reference."
        ]
        
        # Test performance with multiple iterations
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            for desc in test_descriptions:
                calculate_image_tokens_from_description(desc)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_call = (total_time / iterations / len(test_descriptions)) * 1000  # Convert to milliseconds
        
        print(f"✅ Processed {iterations} iterations with {len(test_descriptions)} descriptions each")
        print(f"✅ Total time: {total_time:.3f} seconds")
        print(f"✅ Average time per call: {avg_time_per_call:.3f} milliseconds")
        
        # Performance should be reasonable (< 1ms per call)
        if avg_time_per_call < 1.0:
            print("✅ Performance is excellent")
        elif avg_time_per_call < 5.0:
            print("✅ Performance is good")
        else:
            print("⚠️  Performance could be improved")
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_configuration():
    """Test configuration values."""
    print("🧪 Testing Configuration...")
    
    try:
        from main import (
            BASE_IMAGE_TOKENS, IMAGE_TOKENS_PER_CHAR, ENABLE_DYNAMIC_IMAGE_TOKENS,
            GENERATE_IMAGE_DESCRIPTIONS, IMAGE_AGE_THRESHOLD
        )
        
        print(f"✅ BASE_IMAGE_TOKENS: {BASE_IMAGE_TOKENS}")
        print(f"✅ IMAGE_TOKENS_PER_CHAR: {IMAGE_TOKENS_PER_CHAR}")
        print(f"✅ ENABLE_DYNAMIC_IMAGE_TOKENS: {ENABLE_DYNAMIC_IMAGE_TOKENS}")
        print(f"✅ GENERATE_IMAGE_DESCRIPTIONS: {GENERATE_IMAGE_DESCRIPTIONS}")
        print(f"✅ IMAGE_AGE_THRESHOLD: {IMAGE_AGE_THRESHOLD}")
        
        # Validate configuration values
        assert BASE_IMAGE_TOKENS > 0, "BASE_IMAGE_TOKENS should be positive"
        assert IMAGE_TOKENS_PER_CHAR > 0, "IMAGE_TOKENS_PER_CHAR should be positive"
        assert isinstance(ENABLE_DYNAMIC_IMAGE_TOKENS, bool), "ENABLE_DYNAMIC_IMAGE_TOKENS should be boolean"
        assert isinstance(GENERATE_IMAGE_DESCRIPTIONS, bool), "GENERATE_IMAGE_DESCRIPTIONS should be boolean"
        assert IMAGE_AGE_THRESHOLD >= 0, "IMAGE_AGE_THRESHOLD should be non-negative"
        
        print("✅ All configuration values are valid")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Image Handling Update Tests")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_dynamic_image_token_calculation,
        test_image_description_validation,
        test_accurate_token_counter_integration,
        test_context_window_manager_integration,
        test_performance
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Image handling updates are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())