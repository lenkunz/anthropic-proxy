#!/usr/bin/env python3
"""
Simple test to verify the benchmark functionality works correctly
"""

import sys
import os
sys.path.insert(0, '.')

from cli.config import Config
import tiktoken

def test_benchmark_content_generation():
    """Test the content generation logic used in benchmark"""
    print("🧪 Testing benchmark content generation...")
    
    # Create test content of exact token count
    def create_test_content(target_tokens: int) -> str:
        """Create content targeting exactly N tokens using tiktoken"""
        encoding = tiktoken.get_encoding("cl100k_base")
        
        sections = [
            "Machine learning is a transformative technology that enables computers to learn from data without explicit programming. It encompasses various algorithms and approaches that allow systems to improve their performance through experience.",
            "Deep learning, a subset of machine learning, uses neural networks with multiple layers to model complex patterns in data. These networks can automatically learn hierarchical representations of features.",
            "Natural language processing (NLP) enables machines to understand, interpret, and generate human language. Modern NLP systems use transformer architectures and attention mechanisms.",
            "Computer vision allows machines to interpret and understand visual information from the world. Applications include image classification, object detection, and semantic segmentation.",
            "Reinforcement learning involves training agents to make sequential decisions in an environment to maximize cumulative rewards through trial and error.",
        ]
        
        base_content = " ".join(sections)
        content = base_content
        
        while len(encoding.encode(content)) < target_tokens:
            content += " " + base_content
        
        tokens = encoding.encode(content)
        if len(tokens) > target_tokens:
            tokens = tokens[:target_tokens]
            content = encoding.decode(tokens)
        
        return content
    
    # Test content generation
    test_tokens = [100, 500, 1000, 2000]
    
    for tokens in test_tokens:
        content = create_test_content(tokens)
        actual_tokens = len(tiktoken.get_encoding("cl100k_base").encode(content))
        print(f"   Target: {tokens:,}, Actual: {actual_tokens:,}, Accuracy: {(actual_tokens/tokens)*100:.1f}%")
        
        # Verify token count is accurate (within 1% tolerance)
        if abs(actual_tokens - tokens) / tokens <= 0.01:
            print(f"   ✅ Token count accurate for {tokens} tokens")
        else:
            print(f"   ❌ Token count inaccurate for {tokens} tokens")
            return False
    
    print("✅ Content generation test passed")
    return True

def test_config_loading():
    """Test configuration loading"""
    print("🧪 Testing configuration loading...")
    
    try:
        config = Config()
        
        # Test basic config methods
        current_server = config.get_current_server()
        print(f"   Current server: {current_server}")
        
        servers = config.get_all_servers()
        print(f"   Available servers: {list(servers.keys())}")
        
        current_model = config.get_current_model()
        print(f"   Current model: {current_model}")
        
        models = config.get_all_models()
        print(f"   Available models: {list(models.keys())}")
        
        # Test IP overrides
        ip_overrides_enabled = config.is_ip_overrides_enabled()
        print(f"   IP overrides enabled: {ip_overrides_enabled}")
        
        print("✅ Configuration loading test passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Configuration loading failed: {e}")
        return False

def main():
    print("🚀 Running Benchmark Functionality Tests")
    print("=" * 50)
    
    # Test 1: Configuration loading
    config_ok = test_config_loading()
    print()
    
    # Test 2: Content generation
    content_ok = test_benchmark_content_generation()
    print()
    
    # Summary
    if config_ok and content_ok:
        print("🎉 All benchmark functionality tests passed!")
        print("\n📝 To run the actual benchmark:")
        print("   1. Start the proxy server: python -m cli start")
        print("   2. Run benchmark: python -m cli benchmark --tokens 1000 --runs 5")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    exit(main())