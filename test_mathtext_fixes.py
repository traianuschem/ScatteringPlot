#!/usr/bin/env python3
"""
Quick test for MathText formatter fixes (v7.0)
"""

from utils.mathtext_formatter import preprocess_mathtext, format_legend_text

# Test 1: Chained expressions with **...$...$...**
print("=" * 60)
print("Test 1: Chained expressions")
print("=" * 60)
test1 = "**$I \\cdot q^4$**"
result1 = preprocess_mathtext(test1)
print(f"Input:  {test1}")
print(f"Output: {result1}")
print()

test1b = "**Text $\\alpha$ more**"
result1b = preprocess_mathtext(test1b)
print(f"Input:  {test1b}")
print(f"Output: {result1b}")
print()

# Test 2: Simple bold text
print("=" * 60)
print("Test 2: Simple formatting")
print("=" * 60)
test2 = "**Messung**"
result2 = preprocess_mathtext(test2)
print(f"Input:  {test2}")
print(f"Output: {result2}")
print()

test2b = "*Fit*"
result2b = preprocess_mathtext(test2b)
print(f"Input:  {test2b}")
print(f"Output: {result2b}")
print()

# Test 3: format_legend_text with bold flag
print("=" * 60)
print("Test 3: format_legend_text with bold=True")
print("=" * 60)
test3 = "Messung"
result3 = format_legend_text(test3, bold=True)
print(f"Input:  {test3} (bold=True)")
print(f"Output: {result3}")
print()

test3b = "Messung $\\alpha$"
result3b = format_legend_text(test3b, bold=True)
print(f"Input:  {test3b} (bold=True)")
print(f"Output: {result3b}")
print()

# Test 4: Complex formulas
print("=" * 60)
print("Test 4: Complex formulas")
print("=" * 60)
test4 = "$I \\cdot q^4$"
result4 = preprocess_mathtext(test4)
print(f"Input:  {test4}")
print(f"Output: {result4}")
print()

test4b = "$q^{-1}$"
result4b = preprocess_mathtext(test4b)
print(f"Input:  {test4b}")
print(f"Output: {result4b}")
print()

test4c = "($\\cdot 1$)"
result4c = preprocess_mathtext(test4c)
print(f"Input:  {test4c}")
print(f"Output: {result4c}")
print()

print("=" * 60)
print("All tests completed!")
print("=" * 60)
