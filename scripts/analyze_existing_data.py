#!/usr/bin/env python3
"""
Analyze the reasoning content data we already collected
"""

# Reasoning content from previous tests
reasoning_46 = """1.  **Deconstruct the Request:** The user wants me to solve the arithmetic expression "12 * 15 + 8 * 3". The key phrase is "Solve step by step". This means I can't just give the final answer. I need to show my work and explain each step clearly.

2.  **Identify the Operations:** The expression has two multiplication operations and one addition operation:
    *   12 * 15
    *   8 * 3
    *   The results of these two multiplications are then added together.

3.  **Recall the Order of Operations (PEMDAS/BODMAS):**
    *   **P**arentheses / **B**rackets
    *   **E**xponents / **O**rders
    *   **M**ultiplication and **D**ivision (from left to right)
    *   **A**ddition and **S**ubtraction (from left to right)

4.  **Apply the Order of Operations to the Problem:**
    *   The expression is `12 * 15 + 8 * 3`.
    *   There are no parentheses or exponents.
    *   The next level is multiplication. There are two multiplication operations: `12 * 15` and `8 * 3`. According to PEMDAS, I must do these *before* the addition. I can do them in any order since they are separate parts of the expression.

5.  **Step 1: Solve the first multiplication (12 * 15).**
    *   I can do this in my head or by writing it out. Let's write it out to be clear for the user.
    *   Method 1: Standard multiplication.
        ```
          15
        x 12
        ----
         30  (2 * 15)
        +150  (10 * 15)
        ----
         180
        ```
    *   Method 2: Break it down (distributive property).
        *   12 * 15 = 12 * (10 + 5) = (12 * 10) + (12 * 5) = 120 + 60 = 180.
    *   Both methods give the same result: 180. I'll use the breakdown method in the explanation as it's often easier for people to follow.

6.  **Step 2: Solve the second multiplication (8 * 3).**
    *   This one is simpler.
    *   8 * 3 = 24.

7.  **Step 3: Perform the addition.**
    *   Now I substitute the results of the multiplications back into the original expression.
    *   Original: `12 * 15 + 8 * 3`
    *   Becomes: `180 + 24`
    *   Now, I need to add these two numbers.
        ```
          180
        +  24
        -----
         204
        ```
    *   Units column: 0 + 4 = 4.
    *   Tens column: 8 + 2 = 10. Write down 0, carry over 1.
    *   Hundreds column: 1 + (the carried-over 1) = 2.
    *   The result is 204.

8.  **Structure the Final Answer:**
    *   Start with a clear statement of the problem.
    *   Use headings or numbered steps to make it easy to follow. "Step 1", "Step 2", etc.
    *   Explain the order of operations (PEMDAS) as the guiding principle. This adds educational value.
    *   Show the calculation for each step clearly.
    *   First, calculate `12 * 15`. Show the breakdown (12 * 10 + 12 * 5).
    *   Second, calculate `8 * 3`.
    *   Third, add the two results together. Show the column addition or a simple sum.
    *   End with a clear, final answer statement.

9.  **Review and Refine:**
    *   Step 1: "First, we need to solve the multiplication parts of the problem, according to the order of operations (PEMDAS/BODMAS)." - Good, explains the 'why'.
    *   "Calculate 12 * 15:" - Clear heading.
    *   `12 * 15 = 180` - Correct. I'll add the breakdown: `12 * 10 = 120` and `12 * 5 = 60`, then `120 + 60 = 180`. This is more "step-by-step".
    *   "Calculate 8 * 3:" - Clear heading.
    *   `8 * 3 = 24` - Correct.
    *   "Now, add the results together:" - Clear transition.
    *   `180 + 24 = 204` - Correct.
    *   Final Answer: "So, 12 * 15 + 8 * 3 = 204." - Perfect summary."""

reasoning_45v = """Got it, let's see. I need to solve 12 times 15 plus 8 times 3. First, I remember that in math, multiplication comes before addition, so I should do the two multiplication problems first, then add the results.

First multiplication: 12 * 15. I can break this down: 12 * 10 = 120, and 12 * 5 = 60. So 120 + 60 = 180.

Second multiplication: 8 * 3 = 24.

Now add the two results: 180 + 24 = 204.

So the final answer is 204."""

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
        print(f"   Possible issues:")
        print(f"   - Buffer overflow in parsing systems")
        print(f"   - Timeout in processing long content")
        print(f"   - Memory limits in client applications")
    
    if len_45v < 1000:
        print(f"\n✅ glm-4.5v reasoning content is more concise ({len_45v} chars)")
        print(f"   This might be more compatible with parsing systems")
        print(f"   Advantages:")
        print(f"   - Faster processing")
        print(f"   - Lower memory usage")
        print(f"   - Better compatibility with limited clients")

def main():
    """Analyze reasoning content from both models"""
    print("🔍 Analyzing existing reasoning content data...")
    
    # Analyze each
    analyze_reasoning_structure(reasoning_46, "glm-4.6")
    analyze_reasoning_structure(reasoning_45v, "glm-4.5v")
    
    # Compare styles
    compare_reasoning_styles(reasoning_46, reasoning_45v)
    
    print("\n🏁 Analysis complete!")
    print("\n💡 Key Insight:")
    print("The glm-4.6 model produces much more detailed reasoning content (6.3x longer)")
    print("This could explain why Kilo can recognize 4.5v but not 4.6 reasoning blocks.")
    print("Possible reasons:")
    print("1. Length limits in Kilo's parsing system")
    print("2. Timeout issues with long content processing")
    print("3. Memory constraints in the client application")
    print("4. Different parsing expectations for detailed vs concise reasoning")

if __name__ == "__main__":
    main()