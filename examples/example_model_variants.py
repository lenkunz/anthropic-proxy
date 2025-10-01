#!/usr/bin/env python3
"""
Example demonstrating model variant functionality.
Shows how different model names route to different endpoints.
"""

import asyncio
import httpx
import json
import os
import requests
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any

# Add project root to path and load environment from project root
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

# Configuration
API_BASE = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY")

if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    print("Please ensure your .env file contains: SERVER_API_KEY=your_api_key_here")
    exit(1)

def make_request(model: str, content: str, description: str) -> Dict[str, Any]:
    """Make a request to the proxy and return results with timing"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Model: {model}")
    print(f"Content: {content}")
    
    url = f"{API_BASE}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 100,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    start_time = time.time()
    
    try:
        print(f"📤 Sending request...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response_time = time.time() - start_time
        
        print(f"📥 Response received in {response_time:.2f}s")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"Response Model: {data.get('model', 'Unknown')}")
            print(f"Response: {data['choices'][0]['message']['content'][:100]}...")
            return {"success": True, "data": data, "time": response_time}
        else:
            print(f"❌ FAILED")
            print(f"Error: {response.text[:200]}...")
            return {"success": False, "error": response.text, "time": response_time}
            
    except Exception as e:
        response_time = time.time() - start_time
        print(f"💥 EXCEPTION after {response_time:.2f}s")
        print(f"Error: {str(e)}")
        return {"success": False, "error": str(e), "time": response_time}

def demonstrate_endpoint_preferences():
    """Demonstrate the new endpoint preference functionality"""
    
    print("🌟 ANTHROPIC PROXY - MODEL VARIANT DEMONSTRATION")
    print("=" * 80)
    print("This script demonstrates the new model variant functionality")
    print("that allows users to control endpoint routing via model names.")
    print("=" * 80)
    
    test_message = "Hello! Please respond with a brief greeting that mentions which AI system you are."
    
    # Test all model variants
    test_cases = [
        {
            "model": "glm-4.6",
            "description": "Auto-routing model (should use Anthropic for text)",
            "expected": "Routes to Anthropic endpoint for text-only requests"
        },
        {
            "model": "glm-4.6-openai",
            "description": "OpenAI-forced model (should use OpenAI endpoint)",
            "expected": "Always routes to OpenAI endpoint"
        },
        {
            "model": "glm-4.6-anthropic",
            "description": "Anthropic-forced model (should use Anthropic endpoint)",
            "expected": "Always routes to Anthropic endpoint for text"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        result = make_request(
            model=test_case["model"],
            content=test_message,
            description=test_case["description"]
        )
        
        result.update({
            "model": test_case["model"],
            "expected": test_case["expected"]
        })
        results.append(result)
        
        time.sleep(1)  # Rate limiting
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{result['model']:<20} | {status} | {result['time']:.2f}s")
    
    success_count = sum(1 for r in results if r["success"])
    total_count = len(results)
    
    print(f"\nResults: {success_count}/{total_count} tests successful")
    
    if success_count == total_count:
        print("🎉 All model variants are working correctly!")
    else:
        print("⚠️  Some tests failed. Check API keys and service availability.")
    
    print(f"\n{'='*80}")
    print("💡 USAGE NOTES")
    print(f"{'='*80}")
    print("• Use 'glm-4.6' for automatic smart routing based on content")
    print("• Use 'glm-4.6-openai' to force requests to OpenAI endpoint")
    print("• Use 'glm-4.6-anthropic' to force text requests to Anthropic endpoint")
    print("• Image requests with '-anthropic' suffix still route to OpenAI (required)")
    print("• Configure TEXT_ENDPOINT_PREFERENCE in .env for global preferences")

def main():
    """Main function"""
    print("Starting model variant demonstration...")
    
    # Check if service is running
    try:
        response = requests.get(f"{API_BASE}/v1/models", timeout=5)
        if response.status_code != 200:
            print(f"❌ Service not available at {API_BASE}")
            print("Please ensure the proxy is running: python main.py")
            return
    except Exception as e:
        print(f"❌ Cannot connect to service at {API_BASE}")
        print(f"Error: {e}")
        print("Please ensure the proxy is running: python main.py")
        return
    
    demonstrate_endpoint_preferences()

if __name__ == "__main__":
    main()