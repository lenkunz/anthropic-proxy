#!/usr/bin/env python3
"""
Analyze the detailed structure of reasoning content from both models
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("SERVER_API_KEY")
OPENAI_UPSTREAM = os.getenv("OPENAI_UPSTREAM_BASE", "https://api.z.ai/api/coding/paas/v4")

def get_model_response(model_name):
    """Get response from a specific model"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "Solve step by step: What is 12 * 15 + 8 * 3?"}
        ],
        "temperature": 0,
        "thinking": {
            "type": "enabled"
        }
    }
    
    try:
        response = requests.post(f"{OPENAI_UPSTREAM}/chat/completions", headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            print(f"❌ {model_name} API call failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ {model_name} API call error: {e}")
        return None

def analyze_reasoning_structure(reasoning_content, model_name):
    """Analyze the structure of reasoning content"""
    print(f"\n=== Analyzing {model_name} Reasoning Content ===")
    print(f"Length: {len(reasoning_content)} characters")
    
    # Check for common patterns
    patterns = {
        "Numbered steps": lambda x: any(x.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) for x in x.split('\n') if x.strip()),
        "Bullet points": lambda x: '*' in x or '-' in x,
        "Markdown headers": lambda x: '#' in x,
        "Bold text": lambda x: '**' in x,
        "Italic text": lambda x: '*' in x,
        "Code blocks": lambda x: '```' in x,
        "Inline code": lambda x: '`' in x,
        "Quotes": lambda x: '"' in x,
        "Parentheses": lambda x: '(' in x and ')' in x,
        "Square brackets": lambda x: '[' in x and ']' in x,
        "Curly braces": lambda x: '{' in x and '}' in x,
    }
    
    print("Patterns found:")
    for pattern_name, pattern_func in patterns.items():
        found = pattern_func(reasoning_content)
        status = "✅" if found else "❌"
        print(f"  {status} {pattern_name}")
    
    # Analyze line structure
    lines = reasoning_content.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    print(f"\nLine analysis:")
    print(f"  Total lines: {len(lines)}")
    print(f"  Non-empty lines: {len(non_empty_lines)}")
    print(f"  Average line length: {sum(len(line) for line in non_empty_lines) / len(non_empty_lines) if non_empty_lines else 0:.1f}")
    
    # Check first few lines
    print(f"\nFirst 5 lines:")
    for i, line in enumerate(lines[:5]):
        if line.strip():
            print(f"  {i+1}: {line.strip()[:100]}...")
    
    # Check for specific thinking indicators
    thinking_indicators = [
        "step by step", "first", "next", "then", "finally", 
        "analyze", "consider", "evaluate", "calculate",
        "thinking", "reasoning", "logic", "process"
    ]
    
    found_indicators = []
    for indicator in thinking_indicators:
        if indicator.lower() in reasoning_content.lower():
            found_indicators.append(indicator)
    
    if found_indicators:
        print(f"\nThinking indicators found: {', '.join(found_indicators)}")
    else:
        print(f"\n❌ No common thinking indicators found")

def compare_reasoning_styles(reasoning_46, reasoning_45v):
    """Compare reasoning styles between models"""
    print(f"\n=== Comparing Reasoning Styles ===")
    
    # Length comparison
    len_46 = len(reasoning_46)
    len_45v = len(reasoning_45v)
    ratio = len_46 / len_45v if len_45v > 0 else 0
    
    print(f"Length comparison:")
    print(f"  glm-4.6: {len_46} chars")
    print(f"  glm-4.5v: {len_45v} chars")
    print(f"  Ratio (4.6/4.5v): {ratio:.1f}x")
    
    # Word count
    words_46 = len(reasoning_46.split())
    words_45v = len(reasoning_45v.split())
    
    print(f"\nWord count:")
    print(f"  glm-4.6: {words_46} words")
    print(f"  glm-4.5v: {words_45v} words")
    
    # Sentence count (rough estimate)
    sentences_46 = reasoning_46.count('.') + reasoning_46.count('!') + reasoning_46.count('?')
    sentences_45v = reasoning_45v.count('.') + reasoning_45v.count('!') + reasoning_45v.count('?')
    
    print(f"\nSentence count (rough):")
    print(f"  glm-4.6: {sentences_46}")
    print(f"  glm-4.5v: {sentences_45v}")
    
    # Check if one might be too verbose for some systems
    if len_46 > 2000:
        print(f"\n⚠️  glm-4.6 reasoning content is quite long ({len_46} chars)")
        print(f"   This might cause issues with systems that have length limits")
    
    if len_45v < 1000:
        print(f"\n✅ glm-4.5v reasoning content is more concise ({len_45v} chars)")
        print(f"   This might be more compatible with parsing systems")

def main():
    """Analyze reasoning content from both models"""
    print("🔍 Analyzing reasoning content structure...")
    
    if not API_KEY:
        print("❌ SERVER_API_KEY not found in .env file")
        return
    
    # Get responses from both models
    response_46 = get_model_response("glm-4.6")
    response_45v = get_model_response("glm-4.5v")
    
    if not response_46 or not response_45v:
        print("❌ Could not get responses from both models")
        return
    
    # Extract reasoning content
    reasoning_46 = response_46['choices'][0]['message'].get('reasoning_content', '')
    reasoning_45v = response_45v['choices'][0]['message'].get('reasoning_content', '')
    
    # Analyze each
    analyze_reasoning_structure(reasoning_46, "glm-4.6")
    analyze_reasoning_structure(reasoning_45v, "glm-4.5v")
    
    # Compare styles
    compare_reasoning_styles(reasoning_46, reasoning_45v)
    
    print("\n🏁 Analysis complete!")

if __name__ == "__main__":
    main()