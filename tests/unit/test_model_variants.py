#!/usr/bin/env python3
"""
Test script for model variant functionality
"""

import requests
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Add project root to path and load environment from project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / ".env")

API_BASE = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY")

if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    print("Please ensure your .env file contains: SERVER_API_KEY=your_api_key_here")
    exit(1)

def test_model_endpoint(model: str, content: str = "Hello, this is a test.") -> Dict[str, Any]:
    """Test a specific model and return response info"""
    url = f"{API_BASE}/v1/chat/completions"
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": content}
        ],
        "max_tokens": 50,
        "stream": False
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response_time = time.time() - start_time
        
        return {
            "model": model,
            "status_code": response.status_code,
            "response_time": f"{response_time:.2f}s",
            "success": response.status_code == 200,
            "content": response.json() if response.status_code == 200 else response.text[:200] + "..."
        }
    
    except Exception as e:
        return {
            "model": model,
            "status_code": "ERROR",
            "response_time": f"{time.time() - start_time:.2f}s",
            "success": False,
            "content": str(e)
        }

def main():
    print("🧪 Testing Model Variants for Endpoint Preferences\n")
    
    # Test model variants
    test_models = [
        "glm-4.6",          # Should use auto routing (Anthropic for text)
        "glm-4.6-openai",   # Should force OpenAI endpoint
        "glm-4.6-anthropic", # Should force Anthropic endpoint
    ]
    
    print("=" * 80)
    print("TESTING MODEL VARIANTS")
    print("=" * 80)
    
    for model in test_models:
        print(f"\nTesting model: {model}")
        print("-" * 50)
        
        result = test_model_endpoint(model)
        
        print(f"Status: {'✅ SUCCESS' if result['success'] else '❌ FAILED'} ({result['status_code']})")
        print(f"Response Time: {result['response_time']}")
        
        if result['success']:
            content = result['content']
            if isinstance(content, dict):
                response_model = content.get('model', 'Unknown')
                assistant_content = content.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"Upstream Model: {response_model}")
                print(f"Response: {assistant_content[:100]}...")
            else:
                print(f"Response: {str(content)[:100]}...")
        else:
            print(f"Error: {result['content']}")
        
        print()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()