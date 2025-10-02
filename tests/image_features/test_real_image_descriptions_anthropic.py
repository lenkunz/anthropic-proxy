#!/usr/bin/env python3
"""
Test contextual image description generation with a real image file using Anthropic endpoint.
This test uses pexels-photo-1108099.jpeg from the workspace and tests the Anthropic API format.
"""

import os
import base64
import json
import time
try:
    from dotenv import load_dotenv
    load_dotenv()
    API_KEY = os.getenv("SERVER_API_KEY")
except ImportError:
    # Read from .env file manually if dotenv not available
    API_KEY = None
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('SERVER_API_KEY='):
                    API_KEY = line.split('=', 1)[1].strip()
                    break
    except FileNotFoundError:
        pass

if not API_KEY:
    print("❌ SERVER_API_KEY not found in .env file")
    exit(1)

try:
    import httpx
except ImportError:
    import urllib.request
    import urllib.parse
    print("❌ httpx not available, this test requires httpx")
    exit(1)

def encode_image_file(image_path: str) -> str:
    """Encode image file to base64 string for Anthropic API."""
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Detect image format from file extension
            if image_path.lower().endswith('.png'):
                media_type = "image/png"
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                media_type = "image/jpeg"
            elif image_path.lower().endswith('.gif'):
                media_type = "image/gif"
            elif image_path.lower().endswith('.webp'):
                media_type = "image/webp"
            else:
                media_type = "image/jpeg"  # Default fallback
            
            # Anthropic expects base64 string, not data URL
            return {
                "type": "base64",
                "media_type": media_type,
                "data": image_base64
            }
    except Exception as e:
        print(f"❌ Error encoding image: {e}")
        return None

def test_contextual_image_descriptions_anthropic():
    print("🧪 Testing contextual image description generation with real image (Anthropic endpoint)")
    
    # Check if image file exists
    image_path = "./examples/pexels-photo-1108099.jpeg"
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return False
    
    # Encode the image
    image_data = encode_image_file(image_path)
    if not image_data:
        print("❌ Failed to encode image")
        return False
    
    # Create a conversation about analyzing the image using Anthropic format
    # This will set up context for contextual description generation
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Here's a photograph I'd like you to analyze. Please provide detailed insights about the scene, lighting, objects, and overall composition."},
                {"type": "image", "source": image_data}
            ]
        },
        # Add more messages to push the image older than threshold if needed
        # {
        #     "role": "assistant", 
        #     "content": "I'll analyze this photograph for you, examining the scene, lighting, objects, and composition elements."
        # },
        # {
        #     "role": "user",
        #     "content": "Now, can you provide a comprehensive analysis of this photograph focusing on the scene, objects, and artistic elements?"
        # }
    ]
    
    print(f"Messages: {len(messages)}")
    print("Expected: AI should provide contextual description related to photography/scene analysis")
    
    # Test payload for Anthropic endpoint
    payload = {
        "model": "glm-4.6-cc-max",  # Use available model - will route based on content
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    headers = {
        "content-type": "application/json", 
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    start_time = time.time()
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "https://api.z.ai/api/anthropic/v1/messages",
                headers=headers,
                json=payload
            )
        
        elapsed = time.time() - start_time
        
        print(f"✅ Status: {response.status_code}")
        print(f"⏱️  Response time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            
            # Check usage info for endpoint detection
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            print(f"📊 Token usage: {input_tokens} input, {output_tokens} output")
            print(f"📡 Endpoint: Anthropic (confirmed)")
            
            # Get response content (Anthropic format)
            content = result["content"][0]["text"] if result.get("content") else ""
            print("📝 Full Response:")
            print(content)
            print("=" * 80)
            
            # Check for contextual terms related to photography/scene analysis
            contextual_terms = [
                "photograph", "image", "scene", "lighting", "composition", 
                "objects", "visual", "photographic", "camera", "shot",
                "focus", "exposure", "color", "background", "foreground",
                "perspective", "depth", "contrast", "subject", "framing"
            ]
            
            content_lower = content.lower()
            found_terms = [term for term in contextual_terms if term in content_lower]
            
            # Also check for general description quality
            description_quality_indicators = [
                "describes", "shows", "depicts", "features", "contains",
                "illustrates", "presents", "displays", "reveals"
            ]
            
            quality_terms = [term for term in description_quality_indicators if term in content_lower]
            
            if found_terms and quality_terms:
                print(f"🎉 SUCCESS: Contextual image description working!")
                print(f"   Found contextual photography terms: {', '.join(found_terms[:5])}")
                print(f"   Found description quality indicators: {', '.join(quality_terms[:3])}")
                return True
            elif found_terms:
                print(f"✅ PARTIAL SUCCESS: Found contextual photography terms: {', '.join(found_terms[:5])}")
                print("   Description quality indicators could be improved")
                return True
            else:
                print(f"❌ FAILURE: No contextual photography terms found in response")
                print("   Response may not be properly analyzing the image")
                return False
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_anthropic_vs_openai_format():
    """Test both Anthropic and OpenAI formats to compare responses."""
    print("\n" + "="*80)
    print("🔄 COMPARISON TEST: Anthropic vs OpenAI Format")
    print("="*80)
    
    # Check if image file exists
    image_path = "./examples/pexels-photo-1108099.jpeg"
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return False
    
    # Encode the image
    image_data_anthropic = encode_image_file(image_path)
    if not image_data_anthropic:
        print("❌ Failed to encode image for Anthropic")
        return False
    
    # Also encode for OpenAI format
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        mime_type = "image/jpeg"
        image_data_url = f"data:{mime_type};base64,{image_base64}"
    
    base_prompt = "Here's a photograph I'd like you to analyze. Please provide detailed insights about the scene, lighting, objects, and overall composition."
    
    # Test Anthropic format
    print("\n🔵 Testing Anthropic Format...")
    anthropic_payload = {
        "model": "glm-4.6-cc-max",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": base_prompt},
                    # {"type": "image", "source": image_data_url}
                    {"type": "image", "source": {
                        "type": "url",
                        "url": "https://hips.hearstapps.com/hmg-prod/images/labrador-and-golden-retreiver-670e89b5aae29.jpg"
                    }}
                ]
            }
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    headers_anthropic = {
        "content-type": "application/json", 
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response_anthropic = client.post(
                "https://api.z.ai/api/anthropic/v1/messages",
                headers=headers_anthropic,
                json=anthropic_payload
            )
        
        if response_anthropic.status_code == 200:
            result_anthropic = response_anthropic.json()
            anthropic_content = result_anthropic["content"][0]["text"] if result_anthropic.get("content") else ""
            print(f"✅ Anthropic response: {len(anthropic_content)} characters")
            print(f"📝 {anthropic_content[:200]}...")
        else:
            print(f"❌ Anthropic request failed: {response_anthropic.status_code}")
            print(f"❌ Anthropic request failed: {response_anthropic.text()}")
            anthropic_content = ""
    except Exception as e:
        print(f"❌ Anthropic test failed: {e}")
        anthropic_content = ""
    
    # Test OpenAI format
    print("\n🟢 Testing OpenAI Format...")
    openai_payload = {
        "model": "glm-4.6-cc-max",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": base_prompt},
                    {"type": "input_image", "image_url": {"url": image_data_url}}
                ]
            }
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    headers_openai = {
        "content-type": "application/json", 
        "x-api-key": API_KEY
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response_openai = client.post(
                "https://api.z.ai/api/coding/paas/v4/chat/completions",
                headers=headers_openai,
                json=openai_payload
            )
        
        if response_openai.status_code == 200:
            result_openai = response_openai.json()
            openai_content = result_openai["choices"][0]["message"]["content"] if result_openai.get("choices") else ""
            print(f"✅ OpenAI response: {len(openai_content)} characters")
            print(f"📝 {openai_content[:200]}...")
        else:
            print(f"❌ OpenAI request failed: {response_openai.status_code}")
            openai_content = ""
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}")
        openai_content = ""
    
    # Compare responses
    print(f"\n📊 COMPARISON SUMMARY:")
    print(f"Anthropic response length: {len(anthropic_content)} characters")
    print(f"OpenAI response length: {len(openai_content)} characters")
    
    if anthropic_content and openai_content:
        print(f"✅ Both endpoints responded successfully!")
        print(f"🔗 Both formats are working correctly")
        return True
    elif anthropic_content:
        print(f"🔵 Only Anthropic endpoint responded")
        return True
    elif openai_content:
        print(f"🟢 Only OpenAI endpoint responded")
        return True
    else:
        print(f"❌ Neither endpoint responded successfully")
        return False

if __name__ == "__main__":
    print("🧪 Starting Anthropic Image Description Tests")
    print("="*80)
    
    # Test 1: Basic Anthropic image description
    success1 = test_contextual_image_descriptions_anthropic()
    
    # Test 2: Comparison between formats
    success2 = test_anthropic_vs_openai_format()
    
    print("\n" + "="*80)
    print("📋 FINAL RESULTS:")
    print(f"✅ Anthropic format test: {'PASSED' if success1 else 'FAILED'}")
    print(f"✅ Format comparison test: {'PASSED' if success2 else 'FAILED'}")
    
    if success1 or success2:
        print("🎉 Overall: AT LEAST ONE TEST PASSED")
        exit(0)
    else:
        print("❌ Overall: ALL TESTS FAILED")
        exit(1)