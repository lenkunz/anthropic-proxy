#!/usr/bin/env python3
"""
Debug the convert_usage_to_openai function issue
"""

def _as_int_or_none(value):
    """Convert a value to a non-negative integer or None if invalid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            result = int(value)
            return result if result >= 0 else None
        except (ValueError, OverflowError):
            return None
    if isinstance(value, str):
        try:
            result = int(float(value))
            return result if result >= 0 else None
        except (ValueError, OverflowError):
            return None
    return None

def convert_usage_to_openai_BROKEN(usage):
    """The current broken version"""
    if not isinstance(usage, dict):
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}

    # Handle prompt tokens (input + cache tokens)
    prompt = _as_int_or_none(usage.get("prompt_tokens"))
    if prompt is None:
        # Start with base input tokens
        base_input = _as_int_or_none(usage.get("input_tokens")) or 0
        
        # Add cache-related tokens to input
        cache_creation = _as_int_or_none(usage.get("cache_creation_input_tokens")) or 0
        cache_read = _as_int_or_none(usage.get("cache_read_input_tokens")) or 0
        
        # BUG IS HERE: Sum all input-related tokens
        if base_input > 0 or cache_creation > 0 or cache_read > 0:  # This ignores case where base_input=25 but others are 0
            prompt = base_input + cache_creation + cache_read
        else:
            prompt = None  # THIS IS THE BUG!

    # Handle completion tokens
    completion = _as_int_or_none(usage.get("completion_tokens"))
    if completion is None:
        completion = _as_int_or_none(usage.get("output_tokens"))

    # Handle total tokens
    total = _as_int_or_none(usage.get("total_tokens"))
    if total is None:
        total = _as_int_or_none(usage.get("combined_tokens"))
    
    # If still no total and we have both prompt and completion, calculate it
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }

def convert_usage_to_openai_FIXED(usage):
    """The fixed version"""
    if not isinstance(usage, dict):
        return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}

    # Handle prompt tokens (input + cache tokens)
    prompt = _as_int_or_none(usage.get("prompt_tokens"))
    if prompt is None:
        # Start with base input tokens
        base_input = _as_int_or_none(usage.get("input_tokens"))
        cache_creation = _as_int_or_none(usage.get("cache_creation_input_tokens"))
        cache_read = _as_int_or_none(usage.get("cache_read_input_tokens"))
        
        # Fix: Check if any value is not None, then sum (including zeros)
        if any(v is not None for v in [base_input, cache_creation, cache_read]):
            prompt = (base_input or 0) + (cache_creation or 0) + (cache_read or 0)
        else:
            prompt = None

    # Handle completion tokens
    completion = _as_int_or_none(usage.get("completion_tokens"))
    if completion is None:
        completion = _as_int_or_none(usage.get("output_tokens"))

    # Handle total tokens
    total = _as_int_or_none(usage.get("total_tokens"))
    if total is None:
        total = _as_int_or_none(usage.get("combined_tokens"))
    
    # If still no total and we have both prompt and completion, calculate it
    if total is None and prompt is not None and completion is not None:
        total = prompt + completion

    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }

# Test case from the logs
test_usage = {
    'input_tokens': 25, 
    'output_tokens': 7, 
    'cache_read_input_tokens': 0
}

print("🐛 Testing the bug in convert_usage_to_openai:")
print(f"Input: {test_usage}")
print()

broken_result = convert_usage_to_openai_BROKEN(test_usage)
print(f"❌ Broken result: {broken_result}")
print()

fixed_result = convert_usage_to_openai_FIXED(test_usage)
print(f"✅ Fixed result: {fixed_result}")
print()

print("🔍 The bug explanation:")
print("The broken version checks 'if base_input > 0 or cache_creation > 0 or cache_read > 0'")
print("When base_input=25 and cache_read=0, it should still sum them (25+0=25)")
print("But the logic wrongly sets prompt=None when not all values are > 0")