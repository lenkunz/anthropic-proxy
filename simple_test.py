#!/usr/bin/env python3
"""
Simple test to identify API errors with the provided key
"""

import requests
import json
import os
from dotenv import load_dotenv

# Configuration
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
API_KEY = os.getenv("API_KEY")

def test_simple_request():
    """Test a simple request to identify the issue"""
    print("Testing simple API request...")
    if not API_KEY:
        print("Missing API_KEY in environment (.env). Aborting.")
        return False
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "x-api-key": API_KEY
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "Hello, this is a simple test message."}
        ],
        "max_tokens": 100,
        "stream": False
    }
    
    # Do not print secrets in logs
    print(f"Headers: {{'Content-Type': 'application/json', 'Authorization': 'Bearer ***', 'x-api-key': '***'}}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", 
                              json=payload, 
                              headers=headers)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Content: {response.text}")
        
        try:
            json_response = response.json()
            print(f"JSON Response: {json.dumps(json_response, indent=2)}")
            
            # Check for errors in the response
            if "error" in json_response:
                print(f"\n❌ ERROR FOUND: {json_response['error']}")
                return False
            else:
                print(f"\n✅ SUCCESS: No errors found in response")
                return True
                
        except json.JSONDecodeError:
            print(f"\n⚠️  WARNING: Response is not valid JSON")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ REQUEST FAILED: {e}")
        return False

if __name__ == "__main__":
    test_simple_request()