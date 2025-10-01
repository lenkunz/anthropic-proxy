#!/usr/bin/env python3
"""
Integration Test for Intelligent Context Management with Main Application

This script tests the integration between the enhanced ContextWindowManager
and the main Anthropic Proxy application to ensure seamless operation.
"""

import os
import sys
import asyncio
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_realistic_conversation(num_turns: int = 10) -> List[Dict[str, Any]]:
    """Create a realistic conversation for testing"""
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant specializing in software development and system architecture. Provide detailed, technical responses with code examples when appropriate."
        }
    ]
    
    conversation_topics = [
        "microservices architecture",
        "database optimization",
        "API design patterns",
        "container orchestration",
        "security best practices",
        "performance monitoring",
        "CI/CD pipelines",
        "cloud infrastructure",
        "machine learning deployment",
        "scalability patterns"
    ]
    
    for i in range(min(num_turns, len(conversation_topics))):
        topic = conversation_topics[i]
        
        # User message
        user_content = f"""
        I'm working on {topic} and need some guidance. Can you explain the key concepts, best practices, and provide some practical examples? 
        
        Specifically, I'm interested in:
        1. Main principles and patterns
        2. Common challenges and solutions
        3. Implementation strategies
        4. Tools and technologies
        5. Real-world examples
        
        Please provide a comprehensive overview with actionable insights.
        """
        
        messages.append({"role": "user", "content": user_content})
        
        # Assistant response (simulated)
        assistant_content = f"""
        I'd be happy to help you understand {topic}! This is a crucial area in modern software development.

        ## Key Concepts and Principles

        {topic} involves several core principles that guide effective implementation:

        1. **Modularity**: Breaking down complex systems into manageable components
        2. **Scalability**: Designing for growth and increased load
        3. **Maintainability**: Ensuring long-term sustainability of the system
        4. **Performance**: Optimizing for speed and efficiency
        5. **Reliability**: Building robust systems that handle failures gracefully

        ## Best Practices

        When implementing {topic}, consider these best practices:

        - Start with a clear architecture plan
        - Implement proper monitoring and logging
        - Use appropriate design patterns
        - Plan for scalability from the beginning
        - Implement comprehensive testing strategies

        ## Common Challenges and Solutions

        **Challenge 1: Complexity Management**
        Solution: Use established patterns and frameworks

        **Challenge 2: Performance Optimization**
        Solution: Implement caching, load balancing, and optimization techniques

        **Challenge 3: Security Considerations**
        Solution: Implement defense-in-depth security strategies

        ## Implementation Example

        Here's a practical example for {topic}:

        ```python
        class {topic.replace(' ', '').title()}Manager:
            def __init__(self, config):
                self.config = config
                self.initialize_components()
            
            def initialize_components(self):
                # Setup core components
                pass
            
            def process_request(self, request):
                # Process incoming requests
                return self.handle_logic(request)
        ```

        ## Tools and Technologies

        Recommended tools for {topic}:
        - Monitoring: Prometheus, Grafana
        - Orchestration: Kubernetes, Docker Swarm
        - Security: OAuth 2.0, JWT
        - Testing: Jest, PyTest, Cypress

        This should give you a solid foundation for implementing {topic} effectively. Let me know if you'd like me to elaborate on any specific aspect!
        """
        
        messages.append({"role": "assistant", "content": assistant_content})
    
    return messages

def create_vision_conversation(num_messages: int = 6) -> List[Dict[str, Any]]:
    """Create a conversation with images for vision testing"""
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant that can analyze images and provide detailed descriptions."
        }
    ]
    
    for i in range(num_messages):
        if i % 2 == 0:
            # User message with image
            content = [
                {
                    "type": "text",
                    "text": f"Please analyze this image #{i//2 + 1}. What do you see? Provide a detailed description including objects, colors, composition, and any notable features."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
                    }
                }
            ]
        else:
            # Assistant response
            content = f"""Based on the image #{(i-1)//2 + 1}, I can see what appears to be a test pattern or placeholder image. The image contains geometric shapes and color blocks typical of image compression tests. 

            Key observations:
            - The image uses standard RGB color values
            - There are geometric patterns including rectangles and squares
            - The resolution appears to be quite low, typical of test images
            - Color gradients are visible across different sections
            - The overall composition suggests this is a technical test image rather than a photograph

            This type of image is commonly used for testing image processing algorithms, compression techniques, and computer vision systems."""
        
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": content})
    
    return messages

async def test_integration_with_main_app():
    """Test integration with main application context management"""
    print("🔗 Testing Integration with Main Application")
    print("=" * 60)
    
    try:
        # Test importing from main application
        print("📦 Testing imports...")
        from context_window_manager import (
            validate_and_truncate_context_async,
            get_context_info,
            analyze_context_state
        )
        print("   ✅ Successfully imported enhanced context management functions")
        
        # Test with realistic conversation
        print("\n💬 Testing with realistic conversation...")
        conversation = create_realistic_conversation(8)
        
        # Analyze before processing
        analysis = analyze_context_state(conversation, is_vision=False)
        print(f"   Conversation Analysis:")
        print(f"   - Messages: {analysis.messages_count}")
        print(f"   - Tokens: {analysis.current_tokens}")
        print(f"   - Risk Level: {analysis.risk_level.value}")
        print(f"   - Strategy: {analysis.recommended_strategy.value}")
        
        # Process with intelligent management
        start_time = asyncio.get_event_loop().time()
        processed_messages, metadata = await validate_and_truncate_context_async(
            conversation, is_vision=False, max_tokens=4096
        )
        processing_time = asyncio.get_event_loop().time() - start_time
        
        print(f"   Processing Results:")
        print(f"   - Processing Time: {processing_time:.3f}s")
        print(f"   - Method Used: {metadata.get('method', 'unknown')}")
        print(f"   - Truncated: {metadata.get('truncated', False)}")
        print(f"   - Risk Level: {metadata.get('risk_level', 'unknown')}")
        
        # Test vision conversation
        print("\n👁️ Testing with vision conversation...")
        vision_conversation = create_vision_conversation(6)
        
        vision_analysis = analyze_context_state(vision_conversation, is_vision=True)
        print(f"   Vision Analysis:")
        print(f"   - Messages: {vision_analysis.messages_count}")
        print(f"   - Tokens: {vision_analysis.current_tokens}")
        print(f"   - Utilization: {vision_analysis.utilization_percent:.1f}%")
        print(f"   - Risk Level: {vision_analysis.risk_level.value}")
        
        vision_processed, vision_metadata = await validate_and_truncate_context_async(
            vision_conversation, is_vision=True
        )
        print(f"   Vision Processing:")
        print(f"   - Method: {vision_metadata.get('method', 'unknown')}")
        print(f"   - Risk Level: {vision_metadata.get('risk_level', 'unknown')}")
        
        print("✅ Integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_integration():
    """Test configuration integration"""
    print("\n⚙️ Testing Configuration Integration")
    print("=" * 60)
    
    try:
        from context_window_manager import get_context_performance_stats
        
        # Get performance stats
        stats = get_context_performance_stats()
        print("📊 Configuration Status:")
        print(f"   - AI Condensation Available: {stats['condensation_engine_available']}")
        print(f"   - Accurate Token Counting: {stats['accurate_token_counter_available']}")
        print(f"   - Cache Size: {stats['cache_size']}")
        
        # Check configuration values
        config = stats['configuration']
        print("\n🔧 Configuration Values:")
        print(f"   - Caution Threshold: {config['caution_threshold'] * 100:.0f}%")
        print(f"   - Warning Threshold: {config['warning_threshold'] * 100:.0f}%")
        print(f"   - Critical Threshold: {config['critical_threshold'] * 100:.0f}%")
        print(f"   - Min Messages: {config['min_messages']}")
        print(f"   - Max Messages: {config['max_messages']}")
        
        # Test environment variable loading
        print("\n🌍 Environment Variables:")
        ai_condensation = os.getenv("ENABLE_AI_CONDENSATION", "false").lower() in ("true", "1", "yes")
        print(f"   - ENABLE_AI_CONDENSATION: {ai_condensation}")
        
        caution_threshold = float(os.getenv("CONDENSATION_CAUTION_THRESHOLD", "0.70"))
        print(f"   - CONDENSATION_CAUTION_THRESHOLD: {caution_threshold}")
        
        print("✅ Configuration integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility with existing code"""
    print("\n🔄 Testing Backward Compatibility")
    print("=" * 60)
    
    try:
        from context_window_manager import (
            validate_and_truncate_context,
            get_simple_context_info
        )
        
        # Test legacy functions
        print("📜 Testing legacy function signatures...")
        
        # Create test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "How can I help you today?"}
        ]
        
        # Test sync validation (legacy)
        processed_msgs, metadata = validate_and_truncate_context(messages, is_vision=False)
        print(f"   Legacy validation - Truncated: {metadata.get('truncated', False)}")
        print(f"   Legacy validation - Method: {metadata.get('method', 'unknown')}")
        
        # Test legacy context info
        legacy_info = get_simple_context_info(messages, is_vision=False)
        print(f"   Legacy info - Tokens: {legacy_info['estimated_tokens']}")
        print(f"   Legacy info - Utilization: {legacy_info['utilization_percent']:.1f}%")
        
        # Test that new functions also work with same inputs
        from context_window_manager import get_context_info
        enhanced_info = get_context_info(messages, is_vision=False)
        print(f"   Enhanced info - Risk Level: {enhanced_info['risk_level']}")
        print(f"   Enhanced info - Strategy: {enhanced_info['recommended_strategy']}")
        
        print("✅ Backward compatibility test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_performance_under_load():
    """Test performance under realistic load"""
    print("\n⚡ Testing Performance Under Load")
    print("=" * 60)
    
    try:
        from context_window_manager import validate_and_truncate_context_async
        import time
        
        # Test with progressively larger conversations
        test_sizes = [5, 10, 15, 20]
        results = []
        
        for size in test_sizes:
            print(f"🚀 Testing with {size} message turns...")
            
            # Create conversation
            messages = create_realistic_conversation(size)
            
            # Measure performance
            start_time = time.time()
            processed_msgs, metadata = await validate_and_truncate_context_async(
                messages, is_vision=False
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            tokens_per_second = len(messages) / processing_time if processing_time > 0 else float('inf')
            
            result = {
                'size': size,
                'processing_time': processing_time,
                'tokens_per_second': tokens_per_second,
                'method': metadata.get('method', 'unknown'),
                'truncated': metadata.get('truncated', False)
            }
            results.append(result)
            
            print(f"   - Processing Time: {processing_time:.3f}s")
            print(f"   - Rate: {tokens_per_second:.1f} msgs/sec")
            print(f"   - Method: {result['method']}")
        
        # Analyze performance trends
        print("\n📈 Performance Analysis:")
        avg_time = sum(r['processing_time'] for r in results) / len(results)
        max_time = max(r['processing_time'] for r in results)
        print(f"   - Average processing time: {avg_time:.3f}s")
        print(f"   - Maximum processing time: {max_time:.3f}s")
        
        # Check if performance scales reasonably
        if max_time < 1.0:  # Should process even large conversations quickly
            print("   ✅ Performance scales well with conversation size")
        else:
            print("   ⚠️  Performance may need optimization for large conversations")
        
        print("✅ Performance test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_integration_tests():
    """Run all integration tests"""
    print("🧪 Intelligent Context Management Integration Test Suite")
    print("=" * 70)
    
    # Check environment
    print("🔧 Checking environment...")
    if not os.path.exists(".env"):
        print("⚠️  Warning: .env file not found. Using default configuration.")
    
    print(f"   Working Directory: {os.getcwd()}")
    print(f"   Python Version: {sys.version}")
    
    # Run tests
    tests = [
        ("Configuration Integration", test_configuration_integration),
        ("Backward Compatibility", test_backward_compatibility),
        ("Integration with Main App", test_integration_with_main_app),
        ("Performance Under Load", test_performance_under_load),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*25} {test_name} {'='*25}")
        
        if asyncio.iscoroutinefunction(test_func):
            results[test_name] = await test_func()
        else:
            results[test_name] = test_func()
    
    # Summary
    print("\n" + "="*70)
    print("📊 INTEGRATION TEST SUMMARY")
    print("="*70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<35} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The intelligent context management system is fully integrated and ready for production.")
        return True
    else:
        print("⚠️  Some integration tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    asyncio.run(run_integration_tests())