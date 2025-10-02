
#!/usr/bin/env python3
"""
Comprehensive test suite for x-kilo-followsup header functionality

This test suite validates the x-kilo-followsup feature by testing:
1. Header detection and processing
2. Tools use pattern recognition
3. Followup question injection for both endpoints
4. Streaming and non-streaming response handling
5. Edge cases and error conditions
"""

import os
import sys
import json
import httpx
import asyncio
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# Load environment variables
load_dotenv()

# Configuration
API_BASE = "http://localhost:5000"
API_KEY = os.getenv("SERVER_API_KEY")

class XKiloFollowupTestSuite:
    """Comprehensive test suite for x-kilo-followsup functionality"""
    
    def __init__(self):
        self.api_base = API_BASE
        self.api_key = API_KEY
        self.passed_tests = 0
        self.total_tests = 0
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
    
    def get_headers(self, include_followup: bool = True) -> dict:
        """Get request headers with optional x-kilo-followsup"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else None
        }
        
        if include_followup:
            headers["x-kilo-followsup"] = "true"
        
        # Remove None headers
        return {k: v for k, v in headers.items() if v is not None}
    
    def test_header_detection_chat_completions(self):
        """Test x-kilo-followsup header detection in /v1/chat/completions"""
        try:
            headers = self.get_headers(include_followup=True)
            payload = {
                "model": "glm-4.6",
                "messages": [
                    {"role": "user", "content": "What is 2+2?"}
                ],
                "stream": False
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{self.api_base}/v1/chat/completions", headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Check if followup was added
                    has_followup = "<ask_followup_question>" in content
                    self.log_test(
                        "Chat Completions Header Detection", 
                        has_followup,
                        f"Response length: {len(content)} chars"
                    )
                    return has_followup
                else:
                    self.log_test(
                        "Chat Completions Header Detection", 
                        False,
                        f"HTTP {response.status_code}: {response.text[:100]}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test("Chat Completions Header Detection", False, f"Exception: {e}")
            return False
    
    def test_no_header_no_followup(self):
        """Test that no followup is added when header is missing"""
        try:
            headers = self.get_headers(include_followup=False)
            payload = {
                "model": "glm-4.6", 
                "messages": [
                    {"role": "user", "content": "What is 3+3?"}
                ],
                "stream": False
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{self.api_base}/v1/chat/completions", headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    # Check that followup was NOT added
                    has_followup = "<ask_followup_question>" in content
                    self.log_test(
                        "No Header - No Followup",
                        not has_followup,
                        f"Response length: {len(content)} chars"
                    )
                    return not has_followup
                else:
                    self.log_test(
                        "No Header - No Followup",
                        False,
                        f"HTTP {response.status_code}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test("No Header - No Followup", False, f"Exception: {e}")
            return False
    
    def test_anthropic_endpoint(self):
        """Test x-kilo-followsup with /v1/messages endpoint"""
        try:
            headers = self.get_headers(include_followup=True)
            payload = {
                "model": "glm-4.6",
                "messages": [
                    {"role": "user", "content": "What is 4+4?"}
                ],
                "max_tokens": 500
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{self.api_base}/v1/messages", headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    content_blocks = result.get("content", [])
                    
                    # Extract text content
                    content = ""
                    for block in content_blocks:
                        if block.get("type") == "text":
                            content += block.get("text", "")
                    
                    has_followup = "<ask_followup_question>" in content
                    self.log_test(
                        "Anthropic Endpoint Followup",
                        has_followup,
                        f"Response length: {len(content)} chars"
                    )
                    return has_followup
                else:
                    self.log_test(
                        "Anthropic Endpoint Followup",
                        False,
                        f"HTTP {response.status_code}"
                    )
                    return False
                    
        except Exception as e:
            self.log_test("Anthropic Endpoint Followup", False, f"Exception: {e}")
            return False
    
    def test_streaming_response(self):
        """Test x-kilo-followsup with streaming responses"""
        try:
            headers = self.get_headers(include_followup=True)
            payload = {
                "model": "glm-4.6",
                "messages": [
                    {"role": "user", "content": "What is 5+5?"}
                ],
                "stream": True
            }
            
            with httpx.Client(timeout=30.0) as client:
                with client.stream("POST", f"{self.api_base}/v1/chat/completions", headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        content_parts = []
                        found_followup = False
                        
                        for line in response.iter_lines():
                            if line:
                                line_str = line.decode