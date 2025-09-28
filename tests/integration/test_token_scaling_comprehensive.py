#!/usr/bin/env python3
"""
Comprehensive token scaling test for all model variants.
Tests the core token scaling functionality to ensure proper scaling between endpoints.
"""

import pytest
import requests
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

API_KEY = os.getenv("SERVER_API_KEY")
BASE_URL = "http://localhost:5000"

class TestTokenScaling:
    """Test suite for token scaling functionality"""
    
    @classmethod
    def setup_class(cls):
        """Set up test class"""
        if not API_KEY:
            pytest.skip("SERVER_API_KEY not found in .env")
        
        # Check if proxy is running
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code != 200:
                pytest.skip("Proxy not running")
        except Exception:
            pytest.skip("Cannot connect to proxy")
    
    def test_model_variant_routing(self):
        """Test that different model variants route correctly"""
        
        # Create test message (long enough to see token differences)
        test_message = """
        Please provide a detailed analysis of quantum computing principles, including 
        superposition, entanglement, quantum gates, and their applications in cryptography,
        optimization, and scientific computing. Also discuss the current challenges in
        quantum error correction and the timeline for practical quantum advantage.
        """ * 20
        
        models_to_test = ["glm-4.5", "glm-4.5-anthropic", "glm-4.5-openai"]
        results = {}
        
        for model in models_to_test:
            response = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": test_message}],
                    "max_tokens": 100,
                    "stream": False
                }
            )
            
            assert response.status_code == 200, f"Request failed for {model}: {response.text}"
            
            data = response.json()
            usage = data.get("usage", {})
            results[model] = usage.get("total_tokens", 0)
        
        # Verify scaling behavior
        glm_4_5_tokens = results["glm-4.5"]
        glm_4_5_anthropic_tokens = results["glm-4.5-anthropic"] 
        glm_4_5_openai_tokens = results["glm-4.5-openai"]
        
        # Both glm-4.5 and glm-4.5-anthropic should route to Anthropic endpoint
        # and have their tokens scaled down from 200k context to 131k context
        # So they should have similar token counts (both scaled)
        assert abs(glm_4_5_tokens - glm_4_5_anthropic_tokens) < 50, \
            f"glm-4.5 ({glm_4_5_tokens}) and glm-4.5-anthropic ({glm_4_5_anthropic_tokens}) should have similar token counts"
        
        # glm-4.5-openai should route to OpenAI endpoint directly
        # It should have different token counts (no scaling, direct from OpenAI endpoint)
        token_difference = abs(glm_4_5_anthropic_tokens - glm_4_5_openai_tokens)
        assert token_difference > 100, \
            f"glm-4.5-anthropic ({glm_4_5_anthropic_tokens}) and glm-4.5-openai ({glm_4_5_openai_tokens}) should have different token counts due to different endpoints"
    
    def test_scaling_factor_calculation(self):
        """Test that the scaling factor is calculated correctly"""
        
        # Expected scaling factor: 128000 / 200000 = 0.64
        expected_factor = 128000 / 200000
        assert abs(expected_factor - 0.65536) < 0.00001, "Scaling factor calculation is incorrect"
        
        # Test the scaling math
        original_tokens = 10000  # Simulated Anthropic tokens (200k context)
        scaled_tokens = int(original_tokens * expected_factor)  # Should be ~6553
        
        assert scaled_tokens == 6553, f"Scaling calculation incorrect: {scaled_tokens} != 6553"
    
    def test_token_scaling_with_images(self):
        """Test token scaling behavior with image requests"""
        
        # Create a simple test image (1x1 pixel PNG in base64)
        test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        
        models_to_test = ["glm-4.5", "glm-4.5-anthropic", "glm-4.5-openai"]
        
        for model in models_to_test:
            response = requests.post(
                f"{BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "What do you see in this image?"},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{test_image_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 50
                }
            )
            
            # All image requests should route to OpenAI endpoint regardless of model variant
            assert response.status_code == 200, f"Image request failed for {model}: {response.text}"
            
            data = response.json()
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            
            # Image requests should have reasonable token counts (not zero)
            assert tokens > 0, f"Image request for {model} returned zero tokens"

if __name__ == "__main__":
    # Run tests directly if executed as script
    test_instance = TestTokenScaling()
    test_instance.setup_class()
    
    print("🧪 Running Token Scaling Tests")
    print("=" * 50)
    
    try:
        print("📊 Testing model variant routing...")
        test_instance.test_model_variant_routing()
        print("✅ Model variant routing test passed")
        
        print("🧮 Testing scaling factor calculation...")
        test_instance.test_scaling_factor_calculation()
        print("✅ Scaling factor calculation test passed")
        
        print("🖼️  Testing image request token scaling...")
        test_instance.test_token_scaling_with_images()
        print("✅ Image token scaling test passed")
        
        print("\n🎉 All token scaling tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)