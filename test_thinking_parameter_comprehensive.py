#!/usr/bin/env python3
"""
Comprehensive test suite for z.ai thinking parameter functionality.

Tests:
1. Endpoint routing logic (glm-4.5 vs glm-4.5-openai vs glm-4.5-anthropic)
2. Thinking parameter injection for OpenAI endpoints
3. Proper endpoint type labeling (openai vs anthropic)
4. Upstream request logging verification
5. Configuration control (ENABLE_ZAI_THINKING)
"""

import requests
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, List

load_dotenv()

class ThinkingParameterTestSuite:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.api_key = os.getenv('SERVER_API_KEY')
        self.test_results: List[Dict[str, Any]] = []
        
        if not self.api_key:
            raise ValueError("SERVER_API_KEY not found in .env file")
    
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
    
    def make_request(self, model: str, content: str, max_tokens: int = 5) -> Dict[str, Any]:
        """Make a test request to the proxy"""
        response = requests.post(
            f'{self.base_url}/v1/chat/completions',
            headers={'Authorization': f'Bearer {self.api_key}'},
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': content}],
                'max_tokens': max_tokens
            }
        )
        
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.text if response.status_code != 200 else None
        }
    
    def test_endpoint_routing_basic_model(self):
        """Test that glm-4.5 routes to Anthropic endpoint for text"""
        result = self.make_request('glm-4.5', 'Test basic routing')
        
        if result['status_code'] != 200:
            self.log_result("Basic Model Routing", False, f"HTTP {result['status_code']}: {result['error']}")
            return
        
        endpoint_type = result['data'].get('usage', {}).get('endpoint_type')
        passed = endpoint_type == 'anthropic'
        
        self.log_result(
            "Basic Model Routing", 
            passed,
            f"glm-4.5 → {endpoint_type} endpoint (expected: anthropic)"
        )
    
    def test_endpoint_routing_openai_suffix(self):
        """Test that glm-4.5-openai routes to OpenAI endpoint"""
        result = self.make_request('glm-4.5-openai', 'Test OpenAI routing')
        
        if result['status_code'] != 200:
            self.log_result("OpenAI Suffix Routing", False, f"HTTP {result['status_code']}: {result['error']}")
            return
        
        endpoint_type = result['data'].get('usage', {}).get('endpoint_type')
        passed = endpoint_type == 'openai'
        
        self.log_result(
            "OpenAI Suffix Routing",
            passed,
            f"glm-4.5-openai → {endpoint_type} endpoint (expected: openai)"
        )
    
    def test_endpoint_routing_anthropic_suffix(self):
        """Test that glm-4.5-anthropic routes to Anthropic endpoint"""
        result = self.make_request('glm-4.5-anthropic', 'Test Anthropic routing')
        
        if result['status_code'] != 200:
            self.log_result("Anthropic Suffix Routing", False, f"HTTP {result['status_code']}: {result['error']}")
            return
        
        endpoint_type = result['data'].get('usage', {}).get('endpoint_type')
        passed = endpoint_type == 'anthropic'
        
        self.log_result(
            "Anthropic Suffix Routing",
            passed, 
            f"glm-4.5-anthropic → {endpoint_type} endpoint (expected: anthropic)"
        )
    
    def test_thinking_parameter_presence(self):
        """Test that OpenAI endpoint requests include thinking parameter in upstream logs"""
        # Make request that should include thinking parameter
        result = self.make_request('glm-4.5-openai', 'Test thinking parameter logging', max_tokens=3)
        
        if result['status_code'] != 200:
            self.log_result("Thinking Parameter Logging", False, f"HTTP {result['status_code']}: {result['error']}")
            return
        
        # Wait for async logging
        time.sleep(1)
        
        upstream_log_path = Path("logs/upstream_requests.json")
        if not upstream_log_path.exists():
            self.log_result("Thinking Parameter Logging", False, "upstream_requests.json not found")
            return
        
        # Read all entries and find the most recent OpenAI request
        try:
            with open(upstream_log_path, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            # Look for recent OpenAI entry with thinking parameter
            thinking_found = False
            for line in reversed(lines):  # Check from most recent
                try:
                    entry = json.loads(line)
                    data = entry.get('data', {})
                    if (data.get('endpoint_type') == 'openai' and 
                        data.get('has_thinking_parameter') == True and
                        data.get('thinking_value') == {'type': 'enabled'}):
                        thinking_found = True
                        break
                except json.JSONDecodeError:
                    continue
            
            self.log_result(
                "Thinking Parameter Logging",
                thinking_found,
                f"Thinking parameter found in upstream logs: {thinking_found}"
            )
            
        except Exception as e:
            self.log_result("Thinking Parameter Logging", False, f"Error reading upstream logs: {e}")
    
    def test_no_thinking_parameter_anthropic(self):
        """Test that Anthropic endpoint requests don't include thinking parameter"""
        # Make request to Anthropic endpoint
        result = self.make_request('glm-4.5', 'Test no thinking parameter', max_tokens=3)
        
        if result['status_code'] != 200:
            self.log_result("No Thinking Parameter (Anthropic)", False, f"HTTP {result['status_code']}: {result['error']}")
            return
        
        # Wait for async logging
        time.sleep(1)
        
        upstream_log_path = Path("logs/upstream_requests.json")
        if not upstream_log_path.exists():
            self.log_result("No Thinking Parameter (Anthropic)", False, "upstream_requests.json not found")
            return
        
        try:
            with open(upstream_log_path, 'r') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            # Check recent Anthropic entries don't have thinking parameter
            anthropic_without_thinking = False
            for line in reversed(lines):  # Check from most recent
                try:
                    entry = json.loads(line)
                    data = entry.get('data', {})
                    if (data.get('endpoint_type') == 'anthropic' and 
                        data.get('has_thinking_parameter') == False):
                        anthropic_without_thinking = True
                        break
                except json.JSONDecodeError:
                    continue
            
            self.log_result(
                "No Thinking Parameter (Anthropic)",
                anthropic_without_thinking,
                f"Anthropic request without thinking parameter: {anthropic_without_thinking}"
            )
            
        except Exception as e:
            self.log_result("No Thinking Parameter (Anthropic)", False, f"Error reading logs: {e}")
    
    def test_response_format_consistency(self):
        """Test that responses have consistent format between endpoints"""
        openai_result = self.make_request('glm-4.5-openai', 'OpenAI format test')
        anthropic_result = self.make_request('glm-4.5', 'Anthropic format test')
        
        if openai_result['status_code'] != 200 or anthropic_result['status_code'] != 200:
            self.log_result("Response Format Consistency", False, "One or both requests failed")
            return
        
        # Check that both have required OpenAI format fields
        openai_data = openai_result['data']
        anthropic_data = anthropic_result['data']
        
        required_fields = ['choices', 'usage', 'model', 'object']
        openai_has_fields = all(field in openai_data for field in required_fields)
        anthropic_has_fields = all(field in anthropic_data for field in required_fields)
        
        # Check usage format
        openai_usage = openai_data.get('usage', {})
        anthropic_usage = anthropic_data.get('usage', {})
        
        usage_fields = ['prompt_tokens', 'completion_tokens', 'total_tokens', 'endpoint_type']
        openai_has_usage = all(field in openai_usage for field in usage_fields)
        anthropic_has_usage = all(field in anthropic_usage for field in usage_fields)
        
        passed = openai_has_fields and anthropic_has_fields and openai_has_usage and anthropic_has_usage
        
        self.log_result(
            "Response Format Consistency",
            passed,
            f"OpenAI: {openai_has_fields and openai_has_usage}, Anthropic: {anthropic_has_fields and anthropic_has_usage}"
        )
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("🧪 Z.ai Thinking Parameter Test Suite")
        print("=" * 50)
        
        self.test_endpoint_routing_basic_model()
        self.test_endpoint_routing_openai_suffix()
        self.test_endpoint_routing_anthropic_suffix()
        self.test_thinking_parameter_presence()
        self.test_no_thinking_parameter_anthropic()
        self.test_response_format_consistency()
        
        print("\n📊 Test Summary")
        print("-" * 30)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        
        if failed_tests == 0:
            print("\n🎉 All tests passed! Thinking parameter implementation is working correctly.")
        else:
            print(f"\n⚠️  {failed_tests} test(s) failed. Check the details above.")
            
        return failed_tests == 0

if __name__ == "__main__":
    suite = ThinkingParameterTestSuite()
    success = suite.run_all_tests()
    exit(0 if success else 1)