#!/usr/bin/env python3
"""
Comprehensive test for environment details deduplication integration points.

This test validates that environment deduplication is properly applied
before token counting across all endpoints and model types.
"""

import os
import asyncio
import json
import time
from typing import Dict, List, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_test_messages_with_environment_details() -> List[Dict[str, Any]]:
    """Create test messages with environment details for testing deduplication."""
    
    base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """<environment_details>
# VSCode Visible Files
test_file.py

# Current Workspace Directory
/home/user/project

# Current Time
Current time in ISO 8601 UTC format: 2025-01-01T10:00:00.000Z
User time zone: America/New_York, UTC-5

# Current Cost
$0.00

# Current Mode
<slug>code</slug>
<name>Code</name>

## Current Working Directory Files
- src/main.py
- src/utils.py
- README.md
</environment_details>

Hello! Can you help me with my code?"""
                }
            ]
        },
        {
            "role": "assistant", 
            "content": "I'd be happy to help you with your code! What would you like me to do?"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """<environment_details>
# VSCode Visible Files
test_file.py,another_file.py

# Current Workspace Directory
/home/user/project

# Current Time
Current time in ISO 8601 UTC format: 2025-01-01T10:01:00.000Z
User time zone: America/New_York, UTC-5

# Current Cost
$0.01

# Current Mode
<slug>code</slug>
<name>Code</name>

## Current Working Directory Files
- src/main.py
- src/utils.py
- README.md
- new_file.js
</environment_details>

Please help me refactor this function."""
                }
            ]
        },
        {
            "role": "assistant",
            "content": "I can help you refactor the function. Could you please share the code you'd like me to refactor?"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": "Here's the function I need help with:",
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "low"
                    }
                }
            ]
        }
    ]

def create_anthropic_messages() -> List[Dict[str, Any]]:
    """Create Anthropic-format messages with environment details."""
    
    base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """<environment_details>
# VSCode Visible Files
test_file.py

# Current Workspace Directory  
/home/user/project

# Current Time
Current time in ISO 8601 UTC format: 2025-01-01T10:00:00.000Z
User time zone: America/New_York, UTC-5

# Current Cost
$0.00

# Current Mode
<slug>code</slug>
<name>Code</name>

## Current Working Directory Files
- src/main.py
- src/utils.py
- README.md
</environment_details>

Hello! Can you help me with my code?"""
                }
            ]
        },
        {
            "role": "assistant",
            "content": "I'd be happy to help you with your code! What would you like me to do?"
        },
        {
            "role": "user", 
            "content": [
                {
                    "type": "text",
                    "text": """<environment_details>
# VSCode Visible Files
test_file.py,another_file.py

# Current Workspace Directory
/home/user/project

# Current Time
Current time in ISO 8601 UTC format: 2025-01-01T10:01:00.000Z
User time zone: America/New_York, UTC-5

# Current Cost
$0.01

# Current Mode
<slug>code</slug>
<name>Code</name>

## Current Working Directory Files
- src/main.py
- src/utils.py
- README.md
- new_file.js
</environment_details>

Please help me refactor this function.""",
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64_image
                    }
                }
            ]
        }
    ]

async def test_environment_details_manager():
    """Test the environment details manager directly."""
    print("🔍 Testing Environment Details Manager...")
    
    try:
        from src.environment_details_manager import get_environment_details_manager
        
        manager = get_environment_details_manager()
        if not manager.enabled:
            print("⚠️  Environment deduplication is disabled")
            return False
            
        # Test with OpenAI-format messages
        messages = create_test_messages_with_environment_details()
        
        print(f"📊 Original messages: {len(messages)}")
        
        # Count original tokens
        from src.accurate_token_counter import get_token_counter
        counter = get_token_counter()
        original_tokens = counter.count_messages_tokens(messages, "openai")
        print(f"📊 Original tokens: {original_tokens.total}")
        
        # Apply deduplication
        result = manager.deduplicate_environment_details(messages)
        
        print(f"✅ Deduplication successful")
        print(f"📊 Removed blocks: {len(result.removed_blocks)}")
        print(f"📊 Tokens saved: {result.tokens_saved}")
        print(f"📊 Deduplicated messages: {len(result.deduplicated_messages)}")
        
        # Count deduplicated tokens
        deduplicated_tokens = counter.count_messages_tokens(result.deduplicated_messages, "openai")
        print(f"📊 Deduplicated tokens: {deduplicated_tokens.total}")
        
        actual_saved = original_tokens.total - deduplicated_tokens.total
        print(f"📊 Actual tokens saved: {actual_saved}")
        
        return result.tokens_saved > 0
        
    except Exception as e:
        print(f"❌ Environment details manager test failed: {e}")
        return False

async def test_accurate_token_counter_integration():
    """Test environment deduplication integration in accurate token counter."""
    print("\n🔍 Testing Accurate Token Counter Integration...")
    
    try:
        from src.accurate_token_counter import get_token_counter
        
        counter = get_token_counter()
        messages = create_test_messages_with_environment_details()
        
        # Test regular counting
        regular_count = counter.count_messages_tokens(messages, "openai")
        print(f"📊 Regular token count: {regular_count.total}")
        
        # Test counting with environment deduplication
        dedup_count, env_tokens_saved = counter.count_messages_tokens_with_env_deduplication(messages, "openai")
        print(f"📊 Deduplicated token count: {dedup_count.total}")
        print(f"📊 Environment tokens saved: {env_tokens_saved}")
        
        success = env_tokens_saved > 0 and dedup_count.total < regular_count.total
        print(f"✅ Token counter integration: {'PASS' if success else 'FAIL'}")
        return success
        
    except Exception as e:
        print(f"❌ Token counter integration test failed: {e}")
        return False

async def test_context_window_manager_integration():
    """Test environment deduplication integration in context window manager."""
    print("\n🔍 Testing Context Window Manager Integration...")
    
    try:
        from src.context_window_manager import context_manager
        
        messages = create_test_messages_with_environment_details()
        
        print(f"📊 Testing with {len(messages)} messages")
        
        # Test intelligent context management (should apply deduplication)
        result = await context_manager.apply_intelligent_context_management(
            messages, 
            is_vision=True,  # Test with vision to trigger context management
            image_descriptions={},
            max_tokens=50000  # Low limit to trigger management
        )
        
        print(f"📊 Context management result: {result.success}")
        print(f"📊 Original tokens: {result.original_tokens}")
        print(f"📊 Final tokens: {result.final_tokens}")
        print(f"📊 Tokens saved: {result.tokens_saved}")
        
        success = result.tokens_saved > 0
        print(f"✅ Context window manager integration: {'PASS' if success else 'FAIL'}")
        return success
        
    except Exception as e:
        print(f"❌ Context window manager integration test failed: {e}")
        return False

async def test_message_condenser_integration():
    """Test environment deduplication integration in message condenser."""
    print("\n🔍 Testing Message Condenser Integration...")
    
    try:
        from src.message_condenser import AICondensationEngine
        
        engine = AICondensationEngine()
        messages = create_test_messages_with_environment_details()
        
        # Count original tokens
        from src.accurate_token_counter import get_token_counter
        counter = get_token_counter()
        original_tokens = counter.count_messages_tokens(messages, "openai")
        
        print(f"📊 Original tokens: {original_tokens.total}")
        
        # Test condensation (should apply deduplication first)
        result = await engine.condense_messages(
            messages,
            current_tokens=original_tokens.total,
            max_tokens=50000,  # Low limit to trigger condensation
            is_vision=True
        )
        
        print(f"📊 Condensation result: {result.success}")
        print(f"📊 Strategy used: {result.strategy_used}")
        print(f"📊 Tokens saved: {result.tokens_saved}")
        print(f"📊 Processing time: {result.processing_time:.2f}s")
        
        success = result.tokens_saved > 0
        print(f"✅ Message condenser integration: {'PASS' if success else 'FAIL'}")
        return success
        
    except Exception as e:
        print(f"❌ Message condenser integration test failed: {e}")
        return False

async def test_openai_chat_completions_endpoint():
    """Test environment deduplication in /v1/chat/completions endpoint."""
    print("\n🔍 Testing /v1/chat/completions Endpoint Integration...")
    
    try:
        import httpx
        
        # Check if server is running
        API_KEY = os.getenv("SERVER_API_KEY")
        if not API_KEY:
            print("⚠️  SERVER_API_KEY not found in .env file")
            return False
            
        messages = create_test_messages_with_environment_details()
        
        payload = {
            "model": "glm-4.6",
            "messages": messages,
            "max_tokens": 100,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}"
                },
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                print(f"📊 Response tokens: {usage}")
                print("✅ /v1/chat/completions endpoint: PASS")
                return True
            else:
                print(f"❌ /v1/chat/completions endpoint failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ /v1/chat/completions endpoint test failed: {e}")
        return False

async def test_anthropic_messages_endpoint():
    """Test environment deduplication in /v1/messages endpoint."""
    print("\n🔍 Testing /v1/messages Endpoint Integration...")
    
    try:
        import httpx
        
        # Check if server is running
        API_KEY = os.getenv("SERVER_API_KEY")
        if not API_KEY:
            print("⚠️  SERVER_API_KEY not found in .env file")
            return False
            
        messages = create_anthropic_messages()
        
        payload = {
            "model": "glm-4.6",
            "messages": messages,
            "max_tokens": 100,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8000/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": API_KEY
                },
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                usage = result.get("usage", {})
                print(f"📊 Response tokens: {usage}")
                print("✅ /v1/messages endpoint: PASS")
                return True
            else:
                print(f"❌ /v1/messages endpoint failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ /v1/messages endpoint test failed: {e}")
        return False

async def main():
    """Run all integration tests."""
    print("🚀 Starting Environment Details Deduplication Integration Tests\n")
    
    # Test individual components
    tests = [
        ("Environment Details Manager", test_environment_details_manager),
        ("Accurate Token Counter", test_accurate_token_counter_integration),
        ("Context Window Manager", test_context_window_manager_integration),
        ("Message Condenser", test_message_condenser_integration),
    ]
    
    component_results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            component_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            component_results.append((test_name, False))
    
    # Test API endpoints (only if server is running)
    api_tests = [
        ("/v1/chat/completions", test_openai_chat_completions_endpoint),
        ("/v1/messages", test_anthropic_messages_endpoint),
    ]
    
    api_results = []
    for test_name, test_func in api_tests:
        try:
            result = await test_func()
            api_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            api_results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    print("\n🔧 COMPONENT INTEGRATION TESTS:")
    for test_name, result in component_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    print("\n🌐 API ENDPOINT TESTS:")
    for test_name, result in api_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    # Overall results
    all_component_tests = all(result for _, result in component_results)
    all_api_tests = all(result for _, result in api_results) if api_results else False
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"  Component Integration: {'✅ ALL PASS' if all_component_tests else '❌ SOME FAIL'}")
    print(f"  API Endpoints: {'✅ ALL PASS' if all_api_tests else '❌ SOME FAIL or UNAVAILABLE'}")
    
    if all_component_tests:
        print("\n🎉 Environment deduplication is properly integrated across all components!")
    else:
        print("\n⚠️  Some component integrations need attention.")
    
    return all_component_tests

if __name__ == "__main__":
    asyncio.run(main())