#!/usr/bin/env python3
"""
Comprehensive test suite for AI-powered message condensation system

This test suite validates:
1. Condensation strategy selection and execution
2. Message importance scoring
3. Token counting and limit management
4. Caching functionality
5. Error handling and fallbacks
6. Integration with context window management
"""

import os
import asyncio
import json
import time
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import condensation system
from message_condenser import (
    AICondensationEngine, 
    CondensationStrategy,
    CondensationResult,
    condense_messages_if_needed,
    condensation_engine
)

# Import context management
from context_window_manager import (
    validate_and_truncate_context_async,
    get_context_info
)

class TestMessageCondensation:
    """Test suite for message condensation functionality"""
    
    def __init__(self):
        self.test_results = []
        self.api_key = os.getenv("SERVER_API_KEY")
        
        if not self.api_key:
            print("❌ SERVER_API_KEY not found in .env file")
            exit(1)
        
        print("✅ Message Condensation Test Suite Initialized")
        print(f"📋 API Key: {self.api_key[:10]}...")
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": time.time()
        })
    
    def create_test_messages(self, count: int = 15, with_images: bool = False) -> List[Dict[str, Any]]:
        """Create test messages for condensation testing"""
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": "You are a helpful AI assistant. Please provide detailed and accurate responses."
        })
        
        # Add conversation messages
        sample_texts = [
            "Can you help me understand how machine learning models work?",
            "I'd like to learn about neural networks and deep learning.",
            "What are the key differences between supervised and unsupervised learning?",
            "Can you explain the concept of backpropagation in neural networks?",
            "How do convolutional neural networks (CNNs) process images?",
            "What is the role of activation functions in neural networks?",
            "Can you explain how reinforcement learning works?",
            "What are some common optimization algorithms used in machine learning?",
            "How do you prevent overfitting in machine learning models?",
            "What is the difference between batch gradient descent and stochastic gradient descent?",
            "Can you explain the concept of transfer learning?",
            "How do transformers work in natural language processing?",
            "What are attention mechanisms in neural networks?",
            "Can you explain how GPT models generate text?"
        ]
        
        for i in range(min(count - 1, len(sample_texts))):
            role = "user" if i % 2 == 0 else "assistant"
            content = sample_texts[i]
            
            if with_images and i % 4 == 0 and role == "user":
                # Add image content every 4th user message
                content = [
                    {"type": "text", "text": content},
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="}}
                ]
            
            messages.append({
                "role": role,
                "content": content
            })
        
        return messages
    
    async def test_condensation_engine_initialization(self):
        """Test condensation engine initialization"""
        try:
            engine = AICondensationEngine()
            
            # Check strategies are loaded
            expected_strategies = [
                CondensationStrategy.CONVERSATION_SUMMARY,
                CondensationStrategy.KEY_POINT_EXTRACTION,
                CondensationStrategy.PROGRESSIVE_SUMMARIZATION,
                CondensationStrategy.SMART_TRUNCATION
            ]
            
            strategies_loaded = all(strategy in engine.strategies for strategy in expected_strategies)
            
            self.log_test_result(
                "Condensation Engine Initialization",
                strategies_loaded,
                f"Loaded {len(engine.strategies)} strategies"
            )
            
            return strategies_loaded
            
        except Exception as e:
            self.log_test_result("Condensation Engine Initialization", False, str(e))
            return False
    
    async def test_message_importance_scoring(self):
        """Test message importance scoring"""
        try:
            engine = AICondensationEngine()
            messages = self.create_test_messages(10)
            
            # Test conversation summary strategy importance scoring
            strategy = engine.strategies[CondensationStrategy.CONVERSATION_SUMMARY]
            importance_scores = strategy._calculate_message_importance(messages)
            
            # Validate scoring
            valid_scores = len(importance_scores) == len(messages)
            system_preserved = any(imp.should_preserve and messages[imp.index].get('role') == 'system' 
                                  for imp in importance_scores)
            
            self.log_test_result(
                "Message Importance Scoring",
                valid_scores and system_preserved,
                f"Scored {len(importance_scores)} messages, system preserved: {system_preserved}"
            )
            
            return valid_scores and system_preserved
            
        except Exception as e:
            self.log_test_result("Message Importance Scoring", False, str(e))
            return False
    
    async def test_condensation_thresholds(self):
        """Test condensation threshold logic"""
        try:
            engine = AICondensationEngine()
            
            # Test with small conversation (should not condense)
            small_messages = self.create_test_messages(3)
            small_tokens = 1000
            max_tokens = 10000
            
            should_condense, reason = engine.should_condense(small_messages, small_tokens, max_tokens)
            
            # Test with large conversation (should condense)
            large_messages = self.create_test_messages(20)
            large_tokens = 8000
            
            should_condense_large, reason_large = engine.should_condense(large_messages, large_tokens, max_tokens)
            
            threshold_logic_correct = not should_condense and should_condense_large
            
            self.log_test_result(
                "Condensation Thresholds",
                threshold_logic_correct,
                f"Small: {should_condense} ({reason}), Large: {should_condense_large} ({reason_large})"
            )
            
            return threshold_logic_correct
            
        except Exception as e:
            self.log_test_result("Condensation Thresholds", False, str(e))
            return False
    
    async def test_smart_truncation_fallback(self):
        """Test smart truncation fallback strategy"""
        try:
            engine = AICondensationEngine()
            messages = self.create_test_messages(15)
            target_tokens = 1000
            
            strategy = engine.strategies[CondensationStrategy.SMART_TRUNCATION]
            
            # Test smart truncation (this doesn't require API calls)
            result = await strategy.condense(messages, target_tokens, None)
            
            fallback_works = (
                result.success and
                len(result.condensed_messages) > 0 and
                result.strategy_used == "smart_truncation"
            )
            
            self.log_test_result(
                "Smart Truncation Fallback",
                fallback_works,
                f"Truncated {len(messages)} → {len(result.condensed_messages)} messages, "
                f"saved {result.tokens_saved} tokens in {result.processing_time:.2f}s"
            )
            
            return fallback_works
            
        except Exception as e:
            self.log_test_result("Smart Truncation Fallback", False, str(e))
            return False
    
    async def test_condensation_caching(self):
        """Test condensation result caching"""
        try:
            engine = AICondensationEngine()
            messages = self.create_test_messages(10)
            
            # Generate cache key
            cache_key = engine._generate_cache_key(messages, CondensationStrategy.SMART_TRUNCATION, 5000)
            
            # Cache should be empty initially
            initial_cache_size = len(engine.cache)
            
            # Cache a result
            mock_result = CondensationResult(
                success=True,
                condensed_messages=messages[:5],
                original_tokens=5000,
                condensed_tokens=2000,
                tokens_saved=3000,
                strategy_used="smart_truncation",
                processing_time=0.1
            )
            
            engine._cache_result(cache_key, mock_result)
            
            # Retrieve from cache
            cached_result = engine._get_cached_result(cache_key)
            
            caching_works = (
                len(engine.cache) == initial_cache_size + 1 and
                cached_result is not None and
                cached_result.tokens_saved == 3000
            )
            
            self.log_test_result(
                "Condensation Caching",
                caching_works,
                f"Cache size: {initial_cache_size} → {len(engine.cache)}, retrieval works: {cached_result is not None}"
            )
            
            return caching_works
            
        except Exception as e:
            self.log_test_result("Condensation Caching", False, str(e))
            return False
    
    async def test_context_window_integration(self):
        """Test integration with context window management"""
        try:
            # Create messages that would exceed vision model limit
            messages = self.create_test_messages(25, with_images=True)
            
            # Get context info
            context_info = get_context_info(messages, is_vision=True)
            
            # Test async context validation with condensation
            processed_messages, metadata = await validate_and_truncate_context_async(
                messages, is_vision=True, max_tokens=1000
            )
            
            integration_works = (
                isinstance(processed_messages, list) and
                len(processed_messages) > 0 and
                isinstance(metadata, dict) and
                'truncated' in metadata
            )
            
            self.log_test_result(
                "Context Window Integration",
                integration_works,
                f"Original: {len(messages)} messages, Processed: {len(processed_messages)} messages, "
                f"Truncated: {metadata.get('truncated', False)}"
            )
            
            return integration_works
            
        except Exception as e:
            self.log_test_result("Context Window Integration", False, str(e))
            return False
    
    async def test_condensation_strategies(self):
        """Test different condensation strategies"""
        try:
            messages = self.create_test_messages(12)
            current_tokens = 6000
            max_tokens = 4000
            
            # Test conversation summary strategy
            result_summary = await condensation_engine.condense_messages(
                messages, current_tokens, max_tokens, "conversation_summary"
            )
            
            # Test key point extraction strategy
            result_key_points = await condensation_engine.condense_messages(
                messages, current_tokens, max_tokens, "key_point_extraction"
            )
            
            # Test progressive summarization strategy
            result_progressive = await condensation_engine.condense_messages(
                messages, current_tokens, max_tokens, "progressive_summarization"
            )
            
            strategies_work = (
                result_summary.success or
                result_key_points.success or
                result_progressive.success
            )
            
            self.log_test_result(
                "Condensation Strategies",
                strategies_work,
                f"Summary: {result_summary.success}, "
                f"Key Points: {result_key_points.success}, "
                f"Progressive: {result_progressive.success}"
            )
            
            return strategies_work
            
        except Exception as e:
            self.log_test_result("Condensation Strategies", False, str(e))
            return False
    
    async def test_error_handling(self):
        """Test error handling and graceful degradation"""
        try:
            engine = AICondensationEngine()
            
            # Test with invalid messages
            invalid_messages = [{"invalid": "structure"}]
            
            result = await engine.condense_messages(
                invalid_messages, 1000, 500
            )
            
            # Should handle gracefully and return original messages
            error_handling_works = (
                not result.success and
                len(result.condensed_messages) == len(invalid_messages) and
                result.error_message is not None
            )
            
            self.log_test_result(
                "Error Handling",
                error_handling_works,
                f"Error message: {result.error_message}"
            )
            
            return error_handling_works
            
        except Exception as e:
            self.log_test_result("Error Handling", False, str(e))
            return False
    
    async def test_performance_metrics(self):
        """Test performance and metrics collection"""
        try:
            messages = self.create_test_messages(15)
            start_time = time.time()
            
            result = await condense_messages_if_needed(
                messages, 7000, 4000, "smart_truncation"
            )
            
            end_time = time.time()
            total_time = end_time - start_time
            
            performance_acceptable = total_time < 5.0  # Should complete within 5 seconds
            
            self.log_test_result(
                "Performance Metrics",
                performance_acceptable,
                f"Total time: {total_time:.2f}s, "
                f"Tokens saved: {result[1].get('tokens_saved', 0)}, "
                f"Strategy: {result[1].get('strategy_used', 'unknown')}"
            )
            
            return performance_acceptable
            
        except Exception as e:
            self.log_test_result("Performance Metrics", False, str(e))
            return False
    
    async def run_all_tests(self):
        """Run all test cases"""
        print("\n🧪 Starting Message Condensation Tests...\n")
        
        tests = [
            self.test_condensation_engine_initialization,
            self.test_message_importance_scoring,
            self.test_condensation_thresholds,
            self.test_smart_truncation_fallback,
            self.test_condensation_caching,
            self.test_context_window_integration,
            self.test_condensation_strategies,
            self.test_error_handling,
            self.test_performance_metrics
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
                self.log_test_result(test.__name__, False, f"Exception: {e}")
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 Test Summary:")
        print(f"   Total: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"   - {result['test_name']}: {result['details']}")
        
        return failed_tests == 0

async def main():
    """Main test runner"""
    print("🤖 AI-Powered Message Condensation Test Suite")
    print("=" * 50)
    
    # Check environment
    if not os.getenv("SERVER_API_KEY"):
        print("❌ SERVER_API_KEY not found in .env file")
        print("Please set up your .env file with a valid z.ai API key")
        return False
    
    # Run tests
    test_suite = TestMessageCondensation()
    success = await test_suite.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Message condensation system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the implementation.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())