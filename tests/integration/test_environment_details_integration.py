#!/usr/bin/env python3
"""
Integration tests for Environment Details Deduplication with ContextWindowManager

This test suite covers the integration between environment details deduplication
and the existing context management system.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.context_window_manager import ContextWindowManager, ContextManagementResult
from src.environment_details_manager import DeduplicationStrategy
from src.accurate_token_counter import AccurateTokenCounter


class TestEnvironmentDetailsIntegration(unittest.TestCase):
    """Test integration of environment details deduplication with context management."""
    
    def setUp(self):
        """Set up test environment."""
        # Enable environment details deduplication
        self.test_env_vars = {
            'ENABLE_ENV_DEDUPLICATION': 'true',
            'ENV_DEDUPLICATION_STRATEGY': 'keep_latest',
            'ENV_DETAILS_MAX_AGE_MINUTES': '30',
            'ENV_DEDUPLICATION_LOGGING': 'false',
            'ENV_DEDUPLICATION_STATS': 'true',
            'ENABLE_AI_CONDENSATION': 'false',  # Disable for simpler testing
            'REAL_TEXT_MODEL_TOKENS': '200000',
            'REAL_VISION_MODEL_TOKENS': '65536'
        }
        
        self.env_patcher = patch.dict(os.environ, self.test_env_vars)
        self.env_patcher.start()
        
        # Create context manager
        self.context_manager = ContextWindowManager()
    
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
    
    def test_context_manager_initialization_with_env_deduplication(self):
        """Test that ContextWindowManager properly initializes environment details manager."""
        self.assertIsNotNone(self.context_manager.env_details_manager)
        self.assertTrue(self.context_manager.env_details_manager.enabled)
        self.assertEqual(self.context_manager.env_details_manager.strategy, DeduplicationStrategy.KEEP_LATEST)
    
    def test_context_manager_without_env_deduplication(self):
        """Test ContextWindowManager when environment details deduplication is disabled."""
        with patch.dict(os.environ, {'ENABLE_ENV_DEDUPLICATION': 'false'}):
            # Create new context manager with disabled env deduplication
            context_manager = ContextWindowManager()
            
            # Should still have env_details_manager but it might be disabled
            self.assertIsNotNone(context_manager.env_details_manager)
    
    def test_intelligent_context_management_with_env_deduplication(self):
        """Test intelligent context management with environment details deduplication."""
        # Create messages with environment details
        messages = [
            {
                "role": "user",
                "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\"]}\n</environment_details>\nFirst message"
            },
            {
                "role": "assistant", 
                "content": "Response to first message"
            },
            {
                "role": "user",
                "content": "<environment_details>\n{\"workspace\": \"/home/user/project\", \"files\": [\"main.py\", \"test.py\"]}\n</environment_details>\nSecond message with updated context"
            }
        ]
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.context_manager.apply_intelligent_context_management(
                    messages=messages,
                    is_vision=False,
                    max_tokens=1000
                )
            )
        finally:
            loop.close()
        
        # Verify result
        self.assertIsInstance(result, ContextManagementResult)
        self.assertEqual(len(result.original_messages), 3)
        self.assertEqual(len(result.processed_messages), 3)
        
        # Should have saved some tokens from environment details deduplication
        self.assertGreaterEqual(result.tokens_saved, 0)
        
        # Check metadata contains environment tokens saved
        self.assertIsInstance(result.metadata, dict)
        self.assertIn('env_tokens_saved', result.metadata)
        self.assertGreaterEqual(result.metadata['env_tokens_saved'], 0)
    
    def test_intelligent_context_management_safe_level_with_deduplication(self):
        """Test context management at SAFE risk level with environment details deduplication."""
        messages = [
            {
                "role": "user",
                "content": "<environment_details>Simple context</environment_details> Short message"
            }
        ]
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.context_manager.apply_intelligent_context_management(
                    messages=messages,
                    is_vision=False,
                    max_tokens=10000  # Large limit to ensure SAFE level
                )
            )
        finally:
            loop.close()
        
        # At SAFE level, should still apply environment details deduplication
        self.assertIsInstance(result, ContextManagementResult)
        self.assertEqual(len(result.processed_messages), 1)
        
        # Should have environment tokens saved in metadata
        self.assertIn('env_tokens_saved', result.metadata)
        self.assertGreaterEqual(result.metadata['env_tokens_saved'], 0)
    
    def test_intelligent_context_management_no_environment_details(self):
        """Test context management when no environment details are present."""
        messages = [
            {"role": "user", "content": "Regular message without environment details"},
            {"role": "assistant", "content": "Response to regular message"}
        ]
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.context_manager.apply_intelligent_context_management(
                    messages=messages,
                    is_vision=False,
                    max_tokens=1000
                )
            )
        finally:
            loop.close()
        
        # Should process normally without environment deduplication
        self.assertIsInstance(result, ContextManagementResult)
        self.assertEqual(len(result.original_messages), 2)
        self.assertEqual(len(result.processed_messages), 2)
        
        # Environment tokens saved should be 0
        self.assertIn('env_tokens_saved', result.metadata)
        self.assertEqual(result.metadata['env_tokens_saved'], 0)
    
    def test_intelligent_context_management_with_vision_requests(self):
        """Test environment details deduplication with vision requests."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "<environment_details>Context with image</environment_details>"},
                    {"type": "image_url", "url": "http://example.com/image.jpg"}
                ]
            }
        ]
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.context_manager.apply_intelligent_context_management(
                    messages=messages,
                    is_vision=True,
                    max_tokens=1000
                )
            )
        finally:
            loop.close()
        
        # Should handle vision requests with environment deduplication
        self.assertIsInstance(result, ContextManagementResult)
        self.assertEqual(len(result.processed_messages), 1)
        
        # Should have environment tokens saved in metadata
        self.assertIn('env_tokens_saved', result.metadata)
    
    def test_environment_details_deduplication_error_handling(self):
        """Test error handling in environment details deduplication."""
        # Mock env_details_manager to raise an exception
        self.context_manager.env_details_manager.deduplicate_environment_details = Mock(
            side_effect=Exception("Deduplication failed")
        )
        
        messages = [
            {"role": "user", "content": "<environment_details>Test</environment_details> Message"}
        ]
        
        # Run async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.context_manager.apply_intelligent_context_management(
                    messages=messages,
                    is_vision=False,
                    max_tokens=1000
                )
            )
        finally:
            loop.close()
        
        # Should handle the error gracefully and continue processing
        self.assertIsInstance(result, ContextManagementResult)
        self.assertEqual(len(result.processed_messages), 1)
        
        # Environment tokens saved should be 0 due to error
        self.assertIn('env_tokens_saved', result.metadata)
        self.assertEqual(result.metadata['env_tokens_saved'], 0)
    
    def test_different_deduplication_strategies(self):
        """Test different deduplication strategies in context management."""
        strategies = [
            DeduplicationStrategy.KEEP_LATEST,
            DeduplicationStrategy.KEEP_MOST_RELEVANT,
            DeduplicationStrategy.MERGE_STRATEGY,
            DeduplicationStrategy.SELECTIVE_REMOVAL
        ]
        
        messages = [
            {"role": "user", "content": "<environment_details>Old context</environment_details> Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "<environment_details>New context</environment_details> Message 2"}
        ]
        
        for strategy in strategies:
            with self.subTest(strategy=strategy):
                # Set the strategy
                self.context_manager.env_details_manager.strategy = strategy
                
                # Run async test
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self.context_manager.apply_intelligent_context_management(
                            messages=messages,
                            is_vision=False,
                            max_tokens=1000
                        )
                    )
                finally:
                    loop.close()
                
                # Should process successfully with any strategy
                self.assertIsInstance(result, ContextManagementResult)
                self.assertEqual(len(result.processed_messages), 3)
                self.assertIn('env_tokens_saved', result.metadata)
    
    def test_environment_details_with_condensation(self):
        """Test environment details deduplication combined with AI condensation."""
        # Enable AI condensation
        with patch.dict(os.environ, {'ENABLE_AI_CONDENSATION': 'true'}):
            # Create context manager with condensation enabled
            context_manager = ContextWindowManager()
            
            # Mock condensation engine to avoid actual API calls
            mock_condensation_result = Mock()
            mock_condensation_result.metadata = {"condensed": True}
            context_manager.condensation_engine = Mock()
            context_manager.condensation_engine.condense_messages = Mock(
                return_value=mock_condensation_result
            )
            
            # Create messages that would trigger condensation
            long_messages = []
            for i in range(20):  # Create many messages to exceed context limit
                long_messages.append({
                    "role": "user" if i % 2 == 0 else "assistant",
                    "content": f"<environment_details>Context {i}</environment_details> " + "x" * 1000
                })
            
            # Run async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    context_manager.apply_intelligent_context_management(
                        messages=long_messages,
                        is_vision=False,
                        max_tokens=1000  # Small limit to trigger condensation
                    )
                )
            finally:
                loop.close()
            
            # Should apply both environment deduplication and condensation
            self.assertIsInstance(result, ContextManagementResult)
            self.assertIn('env_tokens_saved', result.metadata)
            
            # Total tokens saved should include both environment and condensation savings
            self.assertGreaterEqual(result.tokens_saved, result.metadata['env_tokens_saved'])


class TestAccurateTokenCounterIntegration(unittest.TestCase):
    """Test integration of environment details deduplication with accurate token counting."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_env_vars = {
            'ENABLE_ENV_DEDUPLICATION': 'true',
            'ENV_DEDUPLICATION_STRATEGY': 'keep_latest'
        }
        self.env_patcher = patch.dict(os.environ, self.test_env_vars)
        self.env_patcher.start()
        
        # Create token counter
        self.token_counter = AccurateTokenCounter()
    
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
    
    def test_count_messages_tokens_with_env_deduplication(self):
        """Test token counting with environment details deduplication."""
        messages = [
            {"role": "user", "content": "<environment_details>Old context</environment_details> First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "<environment_details>New context</environment_details> Second message"}
        ]
        
        token_count, env_tokens_saved = self.token_counter.count_messages_tokens_with_env_deduplication(
            messages=messages,
            endpoint_type="openai"
        )
        
        # Should return token count and environment tokens saved
        self.assertIsNotNone(token_count)
        self.assertIsInstance(env_tokens_saved, int)
        self.assertGreaterEqual(env_tokens_saved, 0)
    
    def test_count_messages_tokens_with_env_deduplication_no_env_details(self):
        """Test token counting with no environment details."""
        messages = [
            {"role": "user", "content": "Regular message"},
            {"role": "assistant", "content": "Response"}
        ]
        
        token_count, env_tokens_saved = self.token_counter.count_messages_tokens_with_env_deduplication(
            messages=messages,
            endpoint_type="openai"
        )
        
        # Should return token count with 0 environment tokens saved
        self.assertIsNotNone(token_count)
        self.assertEqual(env_tokens_saved, 0)
    
    def test_count_messages_tokens_with_env_deduplication_error_fallback(self):
        """Test fallback behavior when environment deduplication fails."""
        # Mock environment details manager to raise an exception
        with patch('src.accurate_token_counter.get_environment_details_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.enabled = True
            mock_manager.deduplicate_environment_details = Mock(
                side_effect=Exception("Deduplication failed")
            )
            mock_get_manager.return_value = mock_manager
            
            messages = [
                {"role": "user", "content": "<environment_details>Test</environment_details> Message"}
            ]
            
            token_count, env_tokens_saved = self.token_counter.count_messages_tokens_with_env_deduplication(
                messages=messages,
                endpoint_type="openai"
            )
            
            # Should fallback to regular counting
            self.assertIsNotNone(token_count)
            self.assertEqual(env_tokens_saved, 0)


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance of environment details deduplication integration."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_env_vars = {
            'ENABLE_ENV_DEDUPLICATION': 'true',
            'ENV_DEDUPLICATION_STRATEGY': 'keep_latest'
        }
        self.env_patcher = patch.dict(os.environ, self.test_env_vars)
        self.env_patcher.start()
        
        self.context_manager = ContextWindowManager()
    
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
    
    def test_performance_with_large_message_set(self):
        """Test performance with a large set of messages."""
        import time
        
        # Create many messages with environment details
        messages = []
        for i in range(100):
            messages.append({
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"<environment_details>Context {i}: {{'workspace': '/home/user/project', 'files': ['file{i}.py']}}</environment_details> Message {i}"
            })
        
        # Measure processing time
        start_time = time.time()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.context_manager.apply_intelligent_context_management(
                    messages=messages,
                    is_vision=False,
                    max_tokens=50000
                )
            )
        finally:
            loop.close()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (less than 5 seconds for 100 messages)
        self.assertLess(processing_time, 5.0)
        
        # Should have saved significant tokens from deduplication
        self.assertGreater(result.tokens_saved, 0)
        self.assertIn('env_tokens_saved', result.metadata)
        self.assertGreater(result.metadata['env_tokens_saved'], 0)
    
    def test_memory_usage_with_deduplication(self):
        """Test that deduplication doesn't cause excessive memory usage."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create messages with many environment details
        messages = []
        for i in range(50):
            large_env = f"<environment_details>{'x' * 1000}</environment_details>"
            messages.append({
                "role": "user",
                "content": f"{large_env} Message {i}"
            })
        
        # Process messages
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.context_manager.apply_intelligent_context_management(
                    messages=messages,
                    is_vision=False,
                    max_tokens=50000
                )
            )
        finally:
            loop.close()
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        self.assertLess(memory_increase, 50 * 1024 * 1024)
        
        # Should still save tokens from deduplication
        self.assertGreater(result.tokens_saved, 0)


if __name__ == '__main__':
    unittest.main()