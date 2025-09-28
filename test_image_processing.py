import requests
import base64
import json
import time
import os
from dotenv import load_dotenv

# Configuration
load_dotenv()
API_KEY = os.getenv("API_KEY") or os.getenv("SERVER_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", os.getenv("BASE_URL", "http://localhost:5000") + "/v1")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", os.getenv("BASE_URL", "http://localhost:5000") + "/v1")
if not API_KEY:
    print("Missing API_KEY in environment (.env). Exiting.")
    raise SystemExit(1)

# Sample base64 encoded image (1x1 red pixel PNG)
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="

def test_openai_endpoint():
    """Tests the OpenAI-compatible endpoint with an image request."""
    print("\n--- Testing OpenAI-Compatible Endpoint (glm-4.5v) ---")
    url = f"{OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "glm-4.5v",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image? Describe it briefly."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{SAMPLE_IMAGE_BASE64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    try:
        print(f"Sending request to: {url}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"Received response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        print("✅ OpenAI Endpoint Test: SUCCESS")
        print(f"   Status Code: {response.status_code}")
        print(f"   Model: {result.get('model')}")
        if result.get('choices') and len(result['choices']) > 0:
            content = result['choices'][0].get('message', {}).get('content')
            print(f"   Response Content: {content[:200]}{'...' if len(content) > 200 else ''}")
        else:
            print("   Response Content: No choices found in response.")
        return True
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ OpenAI Endpoint Test: FAILED - HTTP Error")
        print(f"   Status Code: {http_err.response.status_code}")
        try:
            error_details = http_err.response.json()
            print(f"   Error Details: {json.dumps(error_details, indent=4)}")
        except json.JSONDecodeError:
            print(f"   Error Details: {http_err.response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"❌ OpenAI Endpoint Test: FAILED - Connection Error")
        print(f"   Details: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"❌ OpenAI Endpoint Test: FAILED - Timeout Error")
        print(f"   Details: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ OpenAI Endpoint Test: FAILED - Request Exception")
        print(f"   Details: {req_err}")
    except Exception as e:
        print(f"❌ OpenAI Endpoint Test: FAILED - An unexpected error occurred")
        print(f"   Details: {e}")
    return False

def test_anthropic_endpoint():
    """Tests the Anthropic endpoint with an image request."""
    print("\n--- Testing Anthropic Endpoint ---")
    url = f"{ANTHROPIC_BASE_URL}/messages"
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is in this image? Describe it briefly."
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": SAMPLE_IMAGE_BASE64
                        }
                    }
                ]
            }
        ]
    }
    try:
        print(f"Sending request to: {url}")
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"Received response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        print("✅ Anthropic Endpoint Test: SUCCESS")
        print(f"   Status Code: {response.status_code}")
        print(f"   Model: {result.get('model')}")
        if result.get('content') and len(result['content']) > 0:
            content_text = result['content'][0].get('text')
            print(f"   Response Content: {content_text[:200]}{'...' if len(content_text) > 200 else ''}")
        else:
            print("   Response Content: No content found in response.")
        return True
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ Anthropic Endpoint Test: FAILED - HTTP Error")
        print(f"   Status Code: {http_err.response.status_code}")
        try:
            error_details = http_err.response.json()
            print(f"   Error Details: {json.dumps(error_details, indent=4)}")
        except json.JSONDecodeError:
            print(f"   Error Details: {http_err.response.text}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"❌ Anthropic Endpoint Test: FAILED - Connection Error")
        print(f"   Details: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"❌ Anthropic Endpoint Test: FAILED - Timeout Error")
        print(f"   Details: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Anthropic Endpoint Test: FAILED - Request Exception")
        print(f"   Details: {req_err}")
    except Exception as e:
        print(f"❌ Anthropic Endpoint Test: FAILED - An unexpected error occurred")
        print(f"   Details: {e}")
    return False

if __name__ == "__main__":
    print("Starting image processing tests...")
    print("Please ensure the proxy server is running on http://localhost:8000")
    time.sleep(2) # Give user a moment to see the message

    openai_success = test_openai_endpoint()
    anthropic_success = test_anthropic_endpoint()

    print("\n--- Test Summary ---")
    print(f"OpenAI-Compatible Endpoint (glm-4.5v): {'PASSED' if openai_success else 'FAILED'}")
    print(f"Anthropic Endpoint: {'PASSED' if anthropic_success else 'FAILED'}")

    if openai_success and anthropic_success:
        print("\n🎉 All tests passed! Image processing appears to be working correctly.")
    else:
        print("\n⚠️ One or more tests failed. Please check the output above for details.")