#!/usr/bin/env python3
"""
Calculate what base context window scales to 200k based on observed inflation ratios
"""

def calculate_base_context_window():
    """Calculate base context from observed inflation ratios"""
    
    print("🧮 CALCULATING BASE CONTEXT WINDOW")
    print("=" * 50)
    print("From upstream scaling test results:")
    print()
    
    # Observed inflation ratios from test
    test_results = [
        {"name": "Short Prompt", "openai": 12, "anthropic": 17},
        {"name": "Medium Prompt", "openai": 66, "anthropic": 102}, 
        {"name": "Long Prompt", "openai": 183, "anthropic": 285}
    ]
    
    target_context = 200000  # Anthropic's 200k context window
    
    print("📊 INFLATION ANALYSIS:")
    base_contexts = []
    
    for result in test_results:
        inflation_ratio = result["anthropic"] / result["openai"]
        base_context = target_context / inflation_ratio
        base_contexts.append(base_context)
        
        print(f"   {result['name']}:")
        print(f"     OpenAI: {result['openai']} tokens")
        print(f"     Anthropic: {result['anthropic']} tokens") 
        print(f"     Inflation: {inflation_ratio:.3f}x")
        print(f"     Base context → 200k: {base_context:,.0f} tokens")
        print()
    
    # Calculate average base context
    avg_base_context = sum(base_contexts) / len(base_contexts)
    
    print("🎯 SUMMARY:")
    print(f"   📈 Target context (Anthropic): {target_context:,} tokens")
    print(f"   📊 Calculated base contexts: {[f'{bc:,.0f}' for bc in base_contexts]}")
    print(f"   📍 Average base context: {avg_base_context:,.0f} tokens")
    print()
    
    # Compare to known values
    known_contexts = {
        "OpenAI GPT-4": 128000,
        "Claude 3.5 Sonnet": 200000,
        "GLM-4.5": 128000  # Suspected
    }
    
    print("🔍 COMPARISON TO KNOWN CONTEXT WINDOWS:")
    for model, context in known_contexts.items():
        difference = abs(avg_base_context - context)
        percentage_diff = (difference / context) * 100
        match_indicator = "✅" if percentage_diff < 10 else "❌"
        print(f"   {match_indicator} {model}: {context:,} tokens (diff: {difference:,.0f}, {percentage_diff:.1f}%)")
    
    print()
    print("💡 CONCLUSION:")
    if abs(avg_base_context - 128000) < abs(avg_base_context - 200000):
        print(f"   🎯 Base context ~{avg_base_context:,.0f} tokens matches GLM-4.5's 128k context window!")
        print(f"   📈 Anthropic inflates 128k → 200k (scaling factor: {200000/128000:.3f}x)")
        print(f"   🔧 Your proxy scales back: 200k → 128k (scaling factor: {128000/200000:.6f}x)")
    else:
        print(f"   🤔 Base context ~{avg_base_context:,.0f} doesn't clearly match known models")

if __name__ == "__main__":
    calculate_base_context_window()