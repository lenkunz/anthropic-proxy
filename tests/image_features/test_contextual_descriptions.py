#!/usr/bin/env python3
"""Test contextual image description generation"""

import json
import urllib.request

SAMPLE_IMAGE_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAG/fzQhxQAAAABJRU5ErkJggg=="

# Test with rich context to see if descriptions are contextual
test_messages = [
    {"role": "user", "content": "Hi, I'm working on a machine learning project about image classification."},
    {"role": "assistant", "content": "That sounds interesting! What kind of images are you planning to classify?"},
    {"role": "user", "content": "I'm focusing on medical imaging, specifically chest X-rays for pneumonia detection."},
    {"role": "assistant", "content": "Medical imaging is a great application for ML. Are you using convolutional neural networks?"},
    {"role": "user", "content": [
        {"type": "text", "text": "Yes! Here's a sample X-ray image from our dataset:"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{SAMPLE_IMAGE_B64}"}}
    ]},
    {"role": "assistant", "content": "I can see the X-ray image you shared."},
    {"role": "user", "content": "What patterns should I look for in the training data?"},
    {"role": "assistant", "content": "For pneumonia detection, key patterns include opacity changes and consolidation areas."},
    {"role": "user", "content": "Can you tell me about that X-ray image I showed you earlier? What would be the key features for pneumonia detection?"}
]

payload = {
    "model": "glm-4.5",
    "messages": test_messages,
    "max_tokens": 300,
    "temperature": 0.1
}

print("🧪 Testing contextual image description generation")
print(f"Messages: {len(test_messages)}")
print("Expected: AI should provide contextual description related to medical imaging/pneumonia detection")

try:
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        "http://localhost:5000/v1/chat/completions",
        data=data,
        headers={
            "Authorization": "Bearer f245254eb9e942449c68f76a3f06a7e5.Au4CB55cjPDZlyIu",
            "Content-Type": "application/json"
        }
    )
    
    with urllib.request.urlopen(req, timeout=60) as response:  # Increased timeout for description generation
        response_data = json.loads(response.read().decode('utf-8'))
        
        context_info = response_data.get("context_info", {})
        endpoint_type = context_info.get("endpoint_type", "unknown")
        
        response_text = response_data["choices"][0]["message"]["content"] if response_data.get("choices") else ""
        
        print(f"✅ Status: {response.status}")
        print(f"📡 Endpoint: {endpoint_type}")
        print(f"📝 Full Response:")
        print(response_text)
        print("="*80)
        
        # Look for medical/contextual terms in the response
        contextual_terms = [
            "pneumonia", "medical", "x-ray", "chest", "imaging", "detection",
            "opacity", "consolidation", "lung", "diagnosis", "pathology"
        ]
        
        contextual_match = any(term in response_text.lower() for term in contextual_terms)
        
        if endpoint_type == "anthropic" and contextual_match:
            print("🎉 SUCCESS: Contextual image description working!")
            print(f"   Found contextual medical terms in response")
        else:
            print("📊 Results:")
            print(f"   Endpoint correct: {endpoint_type == 'anthropic'}")
            print(f"   Contextual content: {contextual_match}")
            print(f"   Contains context terms: {[term for term in contextual_terms if term in response_text.lower()]}")

except Exception as e:
    print(f"❌ Error: {e}")