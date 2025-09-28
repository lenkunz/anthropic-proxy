#!/usr/bin/env python3
"""
Test contextual image description generation with a real image file.
This test uses pexels-photo-1108099.jpeg from the workspace.
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
    """Encode image file to base64 data URL."""
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            # Detect image format from file extension
            if image_path.lower().endswith('.png'):
                mime_type = "image/png"
            elif image_path.lower().endswith(('.jpg', '.jpeg')):
                mime_type = "image/jpeg"
            elif image_path.lower().endswith('.gif'):
                mime_type = "image/gif"
            elif image_path.lower().endswith('.webp'):
                mime_type = "image/webp"
            else:
                mime_type = "image/jpeg"  # Default fallback
            
            return f"data:{mime_type};base64,{image_base64}"
    except Exception as e:
        print(f"❌ Error encoding image: {e}")
        return None

def test_contextual_image_descriptions():
    print("🧪 Testing contextual image description generation with real image")
    
    # Check if image file exists
    image_path = "pexels-photo-1108099.jpeg"
    if not os.path.exists(image_path):
        print(f"❌ Image file not found: {image_path}")
        return
    
    # Encode the image
    image_data_url = encode_image_file(image_path)
    if not image_data_url:
        print("❌ Failed to encode image")
        return
    
    # Create a conversation about analyzing the image
    # This will set up context for contextual description generation
    messages = [
        {
            "role": "user",
            "content": "Hi, I'm working on a computer vision project to analyze photographs."
        },
        {
            "role": "assistant", 
            "content": "That sounds interesting! Computer vision is a fascinating field. What kind of photograph analysis are you working on?"
        },
        {
            "role": "user",
            "content": "I'm interested in scene understanding and object detection in everyday photos. Can you help me analyze images for things like lighting, composition, and objects present?"
        },
        {
            "role": "assistant",
            "content": "Absolutely! I'd be happy to help with scene analysis. For comprehensive image analysis, I typically look at:\n\n1. **Lighting conditions** - natural vs artificial, direction, quality\n2. **Composition elements** - rule of thirds, leading lines, symmetry\n3. **Object detection** - identifying and localizing objects in the scene\n4. **Scene context** - indoor/outdoor, setting, atmosphere\n5. **Technical aspects** - focus, exposure, color balance\n\nFeel free to share an image and I'll provide a detailed analysis!"
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Here's a photograph I'd like you to analyze. Please provide detailed insights about the scene, lighting, objects, and overall composition."},
                {"type": "image_url", "image_url": {"url": image_data_url}}
            ]
        },
        # Add more messages to push the image older than threshold
        {
            "role": "assistant",
            "content": "I'd be happy to analyze this photograph for you! Let me examine the various elements in detail."
        },
        {
            "role": "user", 
            "content": "What specific photographic techniques or principles can you identify in this image?"
        },
        {
            "role": "assistant",
            "content": "Great question! I can identify several photographic techniques and principles in this image that contribute to its visual impact."
        },
        {
            "role": "user",
            "content": "Now, can you provide a comprehensive analysis of this photograph focusing on the scene, objects, and artistic elements?"
        }
    ]
    
    print(f"Messages: {len(messages)}")
    print("Expected: AI should provide contextual description related to photography/scene analysis")
    
    # Test payload
    payload = {
        "model": "glm-4.5",  # This should auto-switch to text endpoint due to image age
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    headers = {
        "content-type": "application/json", 
        "x-api-key": API_KEY
    }
    
    start_time = time.time()
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "http://localhost:5000/v1/chat/completions",
                headers=headers,
                json=payload
            )
        
        elapsed = time.time() - start_time
        
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Check usage info for endpoint detection
            usage = result.get("usage", {})
            endpoint_type = usage.get("endpoint_type", "unknown")
            print(f"📡 Endpoint: {endpoint_type}")
            
            # Get response content
            content = result["choices"][0]["message"]["content"]
            print("📝 Full Response:")
            print(content)
            print("=" * 80)
            
            # Check for contextual terms related to photography/scene analysis
            contextual_terms = [
                "photograph", "image", "scene", "lighting", "composition", 
                "objects", "visual", "photographic", "camera", "shot",
                "focus", "exposure", "color", "background", "foreground"
            ]
            
            content_lower = content.lower()
            found_terms = [term for term in contextual_terms if term in content_lower]
            
            if found_terms:
                print(f"🎉 SUCCESS: Contextual image description working!")
                print(f"   Found contextual photography terms: {', '.join(found_terms[:5])}")
                return True
            else:
                print(f"❌ FAILURE: No contextual photography terms found in response")
                return False
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    test_contextual_image_descriptions()