#!/usr/bin/env python3
"""
Comprehensive tests for Environment Details Manager

This test suite covers all aspects of environment details deduplication including:
- Pattern detection and matching
- Content analysis and comparison
- Deduplication strategies
- Integration with existing systems
- Performance and edge cases
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import tempfile
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.environment_details_manager import (
    EnvironmentDetailsManager,
    EnvironmentDetailsBlock,
    DeduplicationResult,
    DeduplicationStrategy,
    get_environment_details_manager,
    deduplicate_environment_details,
    detect_environment_details,
    get_deduplication_stats
)


class TestEnvironmentDetailsBlock(unittest.TestCase):
    """Test the EnvironmentDetailsBlock dataclass."""
    
    def test_block_creation(self):
        """Test creating an environment details block."""
        content = "<environment_details>Test content</environment_details>"
        block = EnvironmentDetailsBlock(
            content=content,
            start_index=0,
            end_index=len(content),
            pattern_used="<environment_details>.*?</environment_details>",
            message_index=1
        )
        
        self.assertEqual(block.content, content)
        self.assertEqual(block.start_index, 0)
        self.assertEqual(block.end_index, len(content))
        self.assertEqual(block.pattern_used, "<environment_details>.*?</environment_details>")
        self.assertEqual(block.message_index, 1)
        self.assertIsNotNone(block.timestamp)
        self.assertIsNotNone(block.unique_id)
        self.assertEqual(len(block.unique_id), 16)  # MD5 hash prefix
    
    def test_block_auto_unique_id(self):
        """Test that unique ID is automatically generated."""
        content = "Test content"
        block1 = EnvironmentDetailsBlock(content, 0, len(content), "test", 0)
        block2 = EnvironmentDetailsBlock(content, 0, len(content), "test", 0)
        
        # Same content should generate same ID
        self.assertEqual(block1.unique_id, block2.unique_id)
        
        # Different content should generate different ID
        block3 = EnvironmentDetailsBlock("Different content", 0, len("Different content"), "test", 0)
        self.assertNotEqual(block1.unique_id, block3.unique_id)


class TestEnvironmentDetailsManager(unittest.TestCase):
    """Test the EnvironmentDetailsManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary environment for testing
        self.test_env_vars = {
            'ENABLE_ENV_DEDUPLICATION': 'true',
            'ENV_DEDUPLICATION_STRATEGY': 'keep_latest',
            'ENV_DETAILS_MAX_AGE_MINUTES': '30',
            'ENV_DEDUPLICATION_LOGGING': 'false',
            'ENV_DEDUPLICATION_STATS': 'true'
        }
        
        # Patch environment variables
        self.env_patcher = patch.dict(os.environ, self.test_env_vars)
        self.env_patcher.start()
        
        # Create manager instance
        self.manager = EnvironmentDetailsManager()
    
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
    
    def test_manager_initialization(self):
        """Test manager initialization with default settings."""
        self.assertTrue(self.manager.enabled)
        self.assertEqual(self.manager.strategy, DeduplicationStrategy.KEEP_LATEST)
        self.assertEqual(self.manager.max_age_minutes, 30)
        self.assertIsInstance(self.manager.compiled_patterns, list)
        self.assertGreater(len(self.manager.compiled_patterns), 0)
        self.assertIsInstance(self.manager.stats, dict)
    
    def test_manager_initialization_disabled(self):
        """Test manager initialization when disabled."""
        with patch.dict(os.environ, {'ENABLE_ENV_DEDUPLICATION': 'false'}):
            manager = EnvironmentDetailsManager()
            self.assertFalse(manager.enabled)
    
    def test_detect_environment_details_xml_format(self):
        """Test detecting environment details in XML format."""
        content = """
        Some text here
        <environment_details>
        {
            "workspace": "/home/user/project",
            "files": ["main.py", "test.py"],
            "git_branch": "main"
        }
        </environment_details>
        More text here
        """
        
        blocks = self.manager.detect_environment_details(content, 0)
        
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertIn("<environment_details>", block.content)
        self.assertIn("</environment_details>", block.content)
        self.assertEqual(block.message_index, 0)
        self.assertGreater(block.start_index, 0)
        self.assertGreater(block.end_index, block.start_index)
    
    def test_detect_environment_details_code_block_format(self):
        """Test detecting environment details in code block format."""
        content = """
        Some text here
        ```environment
        Workspace: /home/user/project
        Files: main.py, test.py
        Git Branch: main
        ```
        More text here
        """
        
        blocks = self.manager.detect_environment_details(content, 1)
        
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertIn("```environment", block.content)
        self.assertIn("Workspace:", block.content)
        self.assertEqual(block.message_index, 1)
    
    def test_detect_environment_details_multiple_formats(self):
        """Test detecting multiple environment details formats in one content."""
        content = """
        <environment_details>
        {"workspace": "/home/user/project"}
        </environment_details>
        
        Some other text
        
        ```environment
        Workspace: /home/user/project
        Files: main.py
        ```
        
        Environment: Additional context here
        
        More text
        """
        
        blocks = self.manager.detect_environment_details(content, 0)
        
        # Should detect multiple blocks
        self.assertGreater(len(blocks), 1)
        
        # Check that blocks have different patterns
        patterns_used = [block.pattern_used for block in blocks]
        self.assertTrue(any("environment_details" in pattern for pattern in patterns_used))
        self.assertTrue(any("```environment" in pattern for pattern in patterns_used))
    
    def test_detect_environment_details_no_matches(self):
        """Test detecting environment details when none are present."""
        content = """
        This is just regular text without any environment details.
        No special formatting or blocks here.
        Just plain conversation content.
        """
        
        blocks = self.manager.detect_environment_details(content, 0)
        
        self.assertEqual(len(blocks), 0)
    
    def test_remove_overlapping_blocks(self):
        """Test removing overlapping environment details blocks."""
        # Create overlapping blocks
        block1 = EnvironmentDetailsBlock(
            content="<environment_details>Content 1</environment_details>",
            start_index=10,
            end_index=50,
            pattern_used="pattern1",
            message_index=0
        )
        
        block2 = EnvironmentDetailsBlock(
            content="<environment_details>Longer content 2</environment_details>",
            start_index=30,
            end_index=70,  # Overlaps with block1
            pattern_used="pattern2",
            message_index=0
        )
        
        block3 = EnvironmentDetailsBlock(
            content="```environment\nContent 3\n```",
            start_index=80,
            end_index=110,  # No overlap
            pattern_used="pattern3",
            message_index=0
        )
        
        blocks = [block1, block2, block3]
        result = self.manager._remove_overlapping_blocks(blocks)
        
        # Should keep the longer overlapping block and the non-overlapping block
        self.assertEqual(len(result), 2)
        self.assertIn(block2, result)  # Longer block should be kept
        self.assertIn(block3, result)  # Non-overlapping block should be kept
        self.assertNotIn(block1, result)  # Shorter overlapping block should be removed
    
    def test_calculate_content_similarity_identical(self):
        """Test content similarity calculation with identical content."""
        content = "Workspace: /home/user/project\nFiles: main.py, test.py"
        
        similarity = self.manager._calculate_content_similarity(content, content)
        
        self.assertEqual(similarity, 1.0)
    
    def test_calculate_content_similarity_completely_different(self):
        """Test content similarity calculation with completely different content."""
        content1 = "Workspace: /home/user/project"
        content2 = "Completely different text about something else"
        
        similarity = self.manager._calculate_content_similarity(content1, content2)
        
        self.assertLess(similarity, 0.5)
    
    def test_calculate_content_similarity_similar(self):
        """Test content similarity calculation with similar content."""
        content1 = "Workspace: /home/user/project\nFiles: main.py, test.py"
        content2 = "Workspace: /home/user/project\nFiles: main.py, test.py, utils.py"
        
        similarity = self.manager._calculate_content_similarity(content1, content2)
        
        self.assertGreater(similarity, 0.7)
        self.assertLess(similarity, 1.0)
    
    def test_normalize_content(self):
        """Test content normalization for comparison."""
        content = "<environment_details>\nWorkspace: /home/user/project\nFiles: main.py\n</environment_details>"
        
        normalized = self.manager._normalize_content(content)
        
        # Should remove XML tags and normalize whitespace
        self.assertNotIn("<environment_details>", normalized)
        self.assertNotIn("</environment_details>", normalized)
        self.assertIn("Workspace:", normalized)
        self.assertIn("/home/user/project", normalized)
    
    def test_compare_environment_details(self):
        """Test comparing environment details blocks."""
        # Create blocks with different similarities
        block1 = EnvironmentDetailsBlock("Workspace: /home/user/project\nFiles: main.py", 0, 50, "pattern1", 0)
        block2 = EnvironmentDetailsBlock("Workspace: /home/user/project\nFiles: main.py, test.py", 60, 120, "pattern2", 1)
        block3 = EnvironmentDetailsBlock("Completely different content", 130, 160, "pattern3", 2)
        block4 = EnvironmentDetailsBlock("Workspace: /home/user/project\nFiles: main.py", 170, 220, "pattern4", 3)  # Duplicate of block1
        
        blocks = [block1, block2, block3, block4]
        comparison = self.manager.compare_environment_details(blocks)
        
        self.assertIn('duplicates', comparison)
        self.assertIn('similar', comparison)
        self.assertIn('unique', comparison)
        
        # Should find duplicates (block1 and block4)
        self.assertGreater(len(comparison['duplicates']), 0)
        
        # Should find similar blocks (block1 and block2)
        self.assertGreater(len(comparison['similar']), 0)
        
        # Should have unique blocks
        self.assertGreater(len(comparison['unique']), 0)
    
    def test_keep_latest_strategy(self):
        """Test the keep latest deduplication strategy."""
        messages = [
            {"role": "user", "content": "<environment_details>Old details</environment_details> First message"},
            {"role": "assistant", "content": "Response to first message"},
            {"role": "user", "content": "<environment_details>New details</environment_details> Second message"}
        ]
        
        result = self.manager._keep_latest_strategy(messages, self.manager.detect_environment_details(
            messages[0]['content'] + messages[2]['content'], 0))
        
        self.assertIsInstance(result, DeduplicationResult)
        self.assertEqual(len(result.removed_blocks), 1)  # Should remove the old block
        self.assertEqual(len(result.kept_blocks), 1)    # Should keep the new block
        self.assertGreater(result.tokens_saved, 0)
        self.assertEqual(result.strategy_used, DeduplicationStrategy.KEEP_LATEST)
    
    def test_keep_most_relevant_strategy(self):
        """Test the keep most relevant deduplication strategy."""
        # Create blocks with different relevance scores
        old_block = EnvironmentDetailsBlock("Old details", 0, 20, "pattern1", 0)
        old_block.timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
        
        new_block = EnvironmentDetailsBlock("New details with more information and structure", 0, 60, "pattern2", 1)
        new_block.timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        blocks = [old_block, new_block]
        
        with patch.object(self.manager, '_calculate_relevance_score') as mock_relevance:
            mock_relevance.side_effect = [0.3, 0.9]  # Old block less relevant, new block more relevant
            
            result = self.manager._keep_most_relevant_strategy([], blocks)
            
            self.assertEqual(len(result.removed_blocks), 1)
            self.assertEqual(len(result.kept_blocks), 1)
            self.assertEqual(result.strategy_used, DeduplicationStrategy.KEEP_MOST_RELEVANT)
            # Should keep the more relevant block
            self.assertIn(new_block, result.kept_blocks)
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation."""
        # Recent block with good structure
        recent_block = EnvironmentDetailsBlock(
            "Workspace: /home/user/project\nFiles: main.py, test.py\nURL: https://example.com",
            0, 80, "pattern", 0
        )
        recent_block.timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        # Old block with minimal structure
        old_block = EnvironmentDetailsBlock("old info", 0, 20, "pattern", 1)
        old_block.timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
        
        recent_score = self.manager._calculate_relevance_score(recent_block)
        old_score = self.manager._calculate_relevance_score(old_block)
        
        self.assertGreater(recent_score, old_score)
        self.assertGreaterEqual(recent_score, 0.0)
        self.assertLessEqual(recent_score, 1.0)
    
    def test_calculate_structure_score(self):
        """Test structure score calculation."""
        # Well-structured content
        structured_content = """
        Workspace: /home/user/project
        Files: main.py, test.py
        URL: https://example.com
        Config: {"key": "value"}
        """
        
        # Simple content
        simple_content = "Just some text"
        
        structured_score = self.manager._calculate_structure_score(structured_content)
        simple_score = self.manager._calculate_structure_score(simple_content)
        
        self.assertGreater(structured_score, simple_score)
        self.assertGreaterEqual(structured_score, 0.0)
        self.assertLessEqual(structured_score, 1.0)
    
    def test_merge_strategy(self):
        """Test the merge deduplication strategy."""
        block1 = EnvironmentDetailsBlock("Workspace: /home/user/project", 0, 30, "pattern1", 0)
        block2 = EnvironmentDetailsBlock("Files: main.py, test.py", 40, 70, "pattern2", 1)
        
        blocks = [block1, block2]
        
        result = self.manager._merge_strategy([], blocks)
        
        self.assertEqual(len(result.removed_blocks), 2)  # Both original blocks removed
        self.assertEqual(len(result.kept_blocks), 1)    # One merged block created
        self.assertEqual(result.strategy_used, DeduplicationStrategy.MERGE_STRATEGY)
        
        # Check that merged content contains information from both blocks
        merged_content = result.kept_blocks[0].content
        self.assertIn("Workspace:", merged_content)
        self.assertIn("Files:", merged_content)
    
    def test_selective_removal_strategy(self):
        """Test the selective removal deduplication strategy."""
        # Create blocks with duplicates
        block1 = EnvironmentDetailsBlock("Workspace: /home/user/project", 0, 30, "pattern1", 0)
        block2 = EnvironmentDetailsBlock("Workspace: /home/user/project", 40, 70, "pattern2", 1)  # Duplicate
        block3 = EnvironmentDetailsBlock("Files: main.py", 80, 100, "pattern3", 2)  # Unique
        
        blocks = [block1, block2, block3]
        
        with patch.object(self.manager, 'compare_environment_details') as mock_compare:
            mock_compare.return_value = {
                'duplicates': [[block1, block2]],  # block1 and block2 are duplicates
                'similar': [],
                'unique': [block3]
            }
            
            result = self.manager._selective_removal_strategy([], blocks)
            
            self.assertEqual(len(result.removed_blocks), 1)  # One duplicate removed
            self.assertEqual(len(result.kept_blocks), 2)    # One duplicate kept + unique block
            self.assertEqual(result.strategy_used, DeduplicationStrategy.SELECTIVE_REMOVAL)
    
    def test_deduplicate_environment_details_integration(self):
        """Test the main deduplication method integration."""
        messages = [
            {"role": "user", "content": "<environment_details>Old context</environment_details> First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "<environment_details>New context with more details</environment_details> Second message"}
        ]
        
        result = self.manager.deduplicate_environment_details(messages)
        
        self.assertIsInstance(result, DeduplicationResult)
        self.assertEqual(len(result.original_messages), 3)
        self.assertEqual(len(result.deduplicated_messages), 3)  # Messages preserved, just content modified
        self.assertGreaterEqual(result.tokens_saved, 0)
        self.assertIsInstance(result.processing_time, float)
        self.assertGreater(result.processing_time, 0)
    
    def test_deduplicate_environment_details_disabled(self):
        """Test deduplication when the manager is disabled."""
        self.manager.enabled = False
        
        messages = [
            {"role": "user", "content": "<environment_details>Some context</environment_details> Message"}
        ]
        
        result = self.manager.deduplicate_environment_details(messages)
        
        # Should return original messages unchanged
        self.assertEqual(len(result.original_messages), 1)
        self.assertEqual(len(result.deduplicated_messages), 1)
        self.assertEqual(result.tokens_saved, 0)
        self.assertEqual(len(result.removed_blocks), 0)
        self.assertEqual(len(result.kept_blocks), 0)
    
    def test_deduplicate_environment_details_empty_messages(self):
        """Test deduplication with empty message list."""
        result = self.manager.deduplicate_environment_details([])
        
        self.assertEqual(len(result.original_messages), 0)
        self.assertEqual(len(result.deduplicated_messages), 0)
        self.assertEqual(result.tokens_saved, 0)
        self.assertEqual(len(result.removed_blocks), 0)
        self.assertEqual(len(result.kept_blocks), 0)
    
    def test_extract_message_content_string(self):
        """Test extracting content from string message."""
        message = {"role": "user", "content": "Simple message content"}
        
        content = self.manager._extract_message_content(message)
        
        self.assertEqual(content, "Simple message content")
    
    def test_extract_message_content_list(self):
        """Test extracting content from list message format."""
        message = {
            "role": "user", 
            "content": [
                {"type": "text", "text": "Text part"},
                {"type": "image_url", "url": "http://example.com/image.jpg"}
            ]
        }
        
        content = self.manager._extract_message_content(message)
        
        self.assertEqual(content, "Text part")
    
    def test_should_keep_details_recent(self):
        """Test should_keep_details with recent block."""
        recent_block = EnvironmentDetailsBlock("Recent content", 0, 20, "pattern", 0)
        recent_block.timestamp = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        self.assertTrue(self.manager.should_keep_details(recent_block))
    
    def test_should_keep_details_old(self):
        """Test should_keep_details with old block."""
        old_block = EnvironmentDetailsBlock("Old content", 0, 20, "pattern", 0)
        old_block.timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
        
        self.assertFalse(self.manager.should_keep_details(old_block))
    
    def test_should_keep_details_important_content(self):
        """Test should_keep_details with important content."""
        important_block = EnvironmentDetailsBlock("Error: Something went wrong", 0, 30, "pattern", 0)
        important_block.timestamp = datetime.now(timezone.utc) - timedelta(hours=2)  # Old but important
        
        # Should keep because of important keyword
        self.assertTrue(self.manager.should_keep_details(important_block))
    
    def test_get_stats(self):
        """Test getting deduplication statistics."""
        # Process some messages to generate stats
        messages = [
            {"role": "user", "content": "<environment_details>Test</environment_details> Message"}
        ]
        
        self.manager.deduplicate_environment_details(messages)
        
        stats = self.manager.get_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_processed', stats)
        self.assertIn('total_blocks_found', stats)
        self.assertIn('total_blocks_removed', stats)
        self.assertIn('total_tokens_saved', stats)
        self.assertIn('total_processing_time', stats)
        self.assertIn('strategy_usage', stats)
        self.assertIn('average_processing_time', stats)
        self.assertIn('removal_rate', stats)
        
        self.assertGreaterEqual(stats['total_processed'], 1)
        self.assertGreaterEqual(stats['total_blocks_found'], 1)
    
    def test_clear_stats(self):
        """Test clearing statistics."""
        # Generate some stats first
        messages = [{"role": "user", "content": "<environment_details>Test</environment_details>"}]
        self.manager.deduplicate_environment_details(messages)
        
        # Verify stats exist
        stats_before = self.manager.get_stats()
        self.assertGreater(stats_before['total_processed'], 0)
        
        # Clear stats
        self.manager.clear_stats()
        
        # Verify stats are reset
        stats_after = self.manager.get_stats()
        self.assertEqual(stats_after['total_processed'], 0)
        self.assertEqual(stats_after['total_blocks_found'], 0)
        self.assertEqual(stats_after['total_blocks_removed'], 0)
        self.assertEqual(stats_after['total_tokens_saved'], 0)


class TestGlobalFunctions(unittest.TestCase):
    """Test global convenience functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_env_vars = {
            'ENABLE_ENV_DEDUPLICATION': 'true',
            'ENV_DEDUPLICATION_STRATEGY': 'keep_latest',
            'ENV_DETAILS_MAX_AGE_MINUTES': '30'
        }
        self.env_patcher = patch.dict(os.environ, self.test_env_vars)
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
    
    def test_get_environment_details_manager(self):
        """Test getting the global environment details manager."""
        manager = get_environment_details_manager()
        
        self.assertIsInstance(manager, EnvironmentDetailsManager)
        
        # Should return same instance on subsequent calls
        manager2 = get_environment_details_manager()
        self.assertIs(manager, manager2)
    
    def test_deduplicate_environment_details_function(self):
        """Test the global deduplicate_environment_details function."""
        messages = [
            {"role": "user", "content": "<environment_details>Test</environment_details> Message"}
        ]
        
        result = deduplicate_environment_details(messages)
        
        self.assertIsInstance(result, DeduplicationResult)
        self.assertEqual(len(result.original_messages), 1)
        self.assertEqual(len(result.deduplicated_messages), 1)
    
    def test_detect_environment_details_function(self):
        """Test the global detect_environment_details function."""
        content = "<environment_details>Test content</environment_details>"
        
        blocks = detect_environment_details(content, 0)
        
        self.assertIsInstance(blocks, list)
        self.assertEqual(len(blocks), 1)
        self.assertIsInstance(blocks[0], EnvironmentDetailsBlock)
    
    def test_get_deduplication_stats_function(self):
        """Test the global get_deduplication_stats function."""
        stats = get_deduplication_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_processed', stats)
        self.assertIn('total_blocks_found', stats)


class TestEnvironmentDetailsManagerEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_env_vars = {
            'ENABLE_ENV_DEDUPLICATION': 'true',
            'ENV_DEDUPLICATION_STRATEGY': 'keep_latest'
        }
        self.env_patcher = patch.dict(os.environ, self.test_env_vars)
        self.env_patcher.start()
        self.manager = EnvironmentDetailsManager()
    
    def tearDown(self):
        """Clean up test environment."""
        self.env_patcher.stop()
    
    def test_malformed_environment_details(self):
        """Test handling malformed environment details."""
        content = """
        <environment_details
        Missing closing tag and malformed structure
        """
        
        blocks = self.manager.detect_environment_details(content, 0)
        
        # Should not detect malformed blocks
        self.assertEqual(len(blocks), 0)
    
    def test_nested_environment_details(self):
        """Test handling nested environment details."""
        content = """
        <environment_details>
        Outer details
        <environment_details>
        Inner details
        </environment_details>
        More outer details
        </environment_details>
        """
        
        blocks = self.manager.detect_environment_details(content, 0)
        
        # Should detect the outermost block
        self.assertEqual(len(blocks), 1)
        self.assertIn("Outer details", blocks[0].content)
        self.assertIn("Inner details", blocks[0].content)
    
    def test_very_large_environment_details(self):
        """Test handling very large environment details."""
        # Create a large environment details block
        large_content = "Workspace: /home/user/project\n"
        large_content += "Files: " + ",".join([f"file{i}.py" for i in range(1000)]) + "\n"
        large_content += "Content: " + "x" * 10000  # 10KB of content
        
        content = f"<environment_details>\n{large_content}\n</environment_details>"
        
        blocks = self.manager.detect_environment_details(content, 0)
        
        self.assertEqual(len(blocks), 1)
        self.assertGreater(len(blocks[0].content), 10000)
    
    def test_unicode_content(self):
        """Test handling Unicode content in environment details."""
        content = """
        <environment_details>
        Workspace: /home/user/проект
        Files: файл.py, тест.py
        Content: 测试内容 🚀
        </environment_details>
        """
        
        blocks = self.manager.detect_environment_details(content, 0)
        
        self.assertEqual(len(blocks), 1)
        self.assertIn("проект", blocks[0].content)
        self.assertIn("测试内容", blocks[0].content)
        self.assertIn("🚀", blocks[0].content)
    
    def test_empty_content(self):
        """Test handling empty content."""
        result = self.manager.deduplicate_environment_details([])
        
        self.assertEqual(len(result.original_messages), 0)
        self.assertEqual(len(result.deduplicated_messages), 0)
        self.assertEqual(result.tokens_saved, 0)
    
    def test_content_without_environment_details(self):
        """Test handling content without environment details."""
        messages = [
            {"role": "user", "content": "Regular message without environment details"},
            {"role": "assistant", "content": "Another regular message"}
        ]
        
        result = self.manager.deduplicate_environment_details(messages)
        
        self.assertEqual(len(result.original_messages), 2)
        self.assertEqual(len(result.deduplicated_messages), 2)
        self.assertEqual(result.tokens_saved, 0)
        self.assertEqual(len(result.removed_blocks), 0)


if __name__ == '__main__':
    unittest.main()