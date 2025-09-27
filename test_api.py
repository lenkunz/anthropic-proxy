#!/usr/bin/env python3
"""
Test script to identify API errors with the provided key
Tests both OpenAI and Anthropic endpoints with various scenarios
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:5000"
API_KEY = "fa3d7a5f4e124139a058452de9d4ffc0.iPFnM3WRwfWnduJS"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
    "x-api-key": API_KEY
}

def make_request(endpoint: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Make a request and return comprehensive response info"""
    url = f"{BASE_URL}{endpoint}"
    request_headers = HEADERS.copy()
    if headers:
        request_headers.update(headers)
    
    print(f"\n{'='*60}")
    print(f"Testing: {endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print(f"Headers: {request_headers}")
    print(f"URL: {url}")
    
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=request_headers)
        elapsed = time.time() - start_time
        
        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text,
            "json": None,
            "elapsed_time": elapsed,
            "success": response.status_code == 200
        }
        
        try:
            result["json"] = response.json()
        except json.JSONDecodeError:
            result["json"] = None
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed:.2f}s")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text[:1000]}...")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return {
            "error": str(e),
            "success": False,
            "elapsed_time": time.time() - start_time
        }

def test_simple_text_message():
    """Test with a simple text message (no images)"""
    print("\n" + "="*80)
    print("TEST 1: Simple Text Message")
    print("="*80)
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, this is a simple test message."}
        ],
        "max_tokens": 100,
        "stream": False
    }
    
    return make_request("/v1/chat/completions", payload)

def test_with_different_models():
    """Test with different model names"""
    print("\n" + "="*80)
    print("TEST 2: Different Models")
    print("="*80)
    
    models_to_test = ["gpt-4", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
    results = {}
    
    for model in models_to_test:
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": f"Test message for {model}"}
            ],
            "max_tokens": 50,
            "stream": False
        }
        results[model] = make_request("/v1/chat/completions", payload)
    
    return results

def test_auth_methods():
    """Test different authentication methods"""
    print("\n" + "="*80)
    print("TEST 3: Authentication Methods")
    print("="*80)
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Test auth methods"}
        ],
        "max_tokens": 50,
        "stream": False
    }
    
    # Test with Bearer token only
    headers_bearer = {"Authorization": f"Bearer {API_KEY}"}
    result1 = make_request("/v1/chat/completions", payload, headers_bearer)
    
    # Test with x-api-key only
    headers_xapi = {"x-api-key": API_KEY}
    result2 = make_request("/v1/chat/completions", payload, headers_xapi)
    
    # Test with both (default)
    result3 = make_request("/v1/chat/completions", payload)
