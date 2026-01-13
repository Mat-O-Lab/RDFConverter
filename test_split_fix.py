#!/usr/bin/env python3
"""
Test script to verify the regex fix for splitting YARRRML rules
"""
import re
import requests

# Fetch the default mapping
mapping_url = "https://raw.githubusercontent.com/Mat-O-Lab/MapToMethod/refs/heads/main/examples/example-map.yaml"
response = requests.get(mapping_url)
yaml_text = response.text

print("="*80)
print("TESTING YARRRML RULE SPLITTING")
print("="*80)

# Find mappings section
mappings_match = re.search(r'^mappings:\s*$', yaml_text, re.MULTILINE)
if not mappings_match:
    print("ERROR: Could not find 'mappings:' section")
    exit(1)

print(f"\n✓ Found 'mappings:' section at position {mappings_match.start()}")

# Get all rule names from the YAML
import yaml
mapping_dict = yaml.safe_load(yaml_text)
rule_names = list(mapping_dict.get("mappings", {}).keys())
print(f"\n✓ Found {len(rule_names)} rules: {rule_names}")

# Test splitting each rule
print("\n" + "="*80)
print("TESTING RULE EXTRACTION")
print("="*80)

for rule_name in rule_names:
    print(f"\n--- Testing rule: {rule_name} ---")
    
    # Find this specific rule (must start at beginning of line with 2 spaces)
    rule_pattern = rf'^  {re.escape(rule_name)}:\s*$'
    rule_match = re.search(rule_pattern, yaml_text[mappings_match.end():], re.MULTILINE)
    
    if not rule_match:
        print(f"  ✗ Could not find rule '{rule_name}'")
        continue
    
    rule_start = mappings_match.end() + rule_match.start()
    print(f"  ✓ Found rule at position {rule_start}")
    
    # Find next rule at same indentation (2 spaces) or end
    rest_text = yaml_text[rule_start + rule_match.end():]
    # Look for next line starting with exactly 2 spaces, word chars, and colon (next rule)
    next_rule_match = re.search(r'\n  \w+:\s*$', rest_text, re.MULTILINE)
    
    if next_rule_match:
        rule_end = rule_start + rule_match.end() + next_rule_match.start()
        next_rule_name = rest_text[next_rule_match.start():next_rule_match.end()].strip().rstrip(':')
        print(f"  ✓ Found next rule '{next_rule_name}' at position {rule_end}")
    else:
        rule_end = len(yaml_text)
        print(f"  ✓ This is the last rule, ends at {rule_end}")
    
    # Extract just this rule's content
    rule_content = yaml_text[rule_start:rule_end].rstrip()
    
    # Check if rule content contains follow-up rules (should NOT)
    lines = rule_content.split('\n')
    # Count lines that start with exactly 2 spaces and a word followed by colon (potential rule headers)
    potential_rule_headers = [l for l in lines if re.match(r'^  \w+:\s*$', l)]
    
    if len(potential_rule_headers) == 1:
        print(f"  ✓ Extracted rule is clean (1 rule header found)")
    else:
        print(f"  ✗ WARNING: Found {len(potential_rule_headers)} potential rule headers!")
        print(f"    Headers: {potential_rule_headers}")
    
    # Show first few lines of extracted rule
    preview_lines = lines[:5]
    print(f"  Preview (first 5 lines):")
    for line in preview_lines:
        print(f"    {repr(line)}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
