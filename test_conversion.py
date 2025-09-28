#!/usr/bin/env python3
"""Inspect how OpenAI payloads are prepared for the upstream vision endpoint."""

import json
import base64
import copy

AUTOVISION_MODEL = "glm-4.5v"


def prepare_openai_payload_for_upstream(payload):
    """Mirror the proxy behaviour for OpenAI-compatible requests."""
    upstream_payload = copy.deepcopy(payload)
    upstream_payload["model"] = AUTOVISION_MODEL
    return upstream_payload


small_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77yAAAAABJRU5ErkJggg=="

original_payload = {
    "model": "gpt-4o",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What do you see in this image?"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{small_png_base64}"
                    }
                }
            ]
        }
    ],
    "max_tokens": 100
}

print("🔍 Original payload:")
print(json.dumps(original_payload, indent=2))

prepared = prepare_openai_payload_for_upstream(original_payload)
print("\n📤 Payload forwarded upstream:")
print(json.dumps(prepared, indent=2))
