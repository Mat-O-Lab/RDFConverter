#!/usr/bin/env python3
"""Test script to verify CatenaX batch mapping prefix preservation"""

import requests
import json

# CatenaX batch mapping URL
MAPPING_URL = "https://dataportal.material-digital.de/dataset/6e69df9b-dbfb-4176-b0ad-231535797248/resource/8e00ed56-255c-46f2-b04e-fbd5b872efd9/download/catenax-batch-map.yaml"

# API endpoint
API_URL = "http://localhost:6003/api/createrdf"

def test_mapping():
    """Test the mapping and check if prefixes are preserved"""
    
    print("🧪 Testing CatenaX Batch Mapping...")
    print(f"📍 Mapping URL: {MAPPING_URL}")
    print()
    
    # Make API request
    payload = {
        "mapping_url": MAPPING_URL
    }
    
    print("🚀 Sending request to API...")
    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        print("✅ Mapping executed successfully!")
        print(f"📊 Rules applied: {result['num_mappings_applied']}")
        print(f"📊 Rules skipped: {result['num_mappings_skipped']}")
        print()
        
        # Check the output for proper prefix usage
        output = result['graph']
        
        print("🔍 Checking prefix preservation...")
        print()
        
        # Check for prefixes in output
        expected_prefixes = [
            'cx:',
            'ext-built:',
            'ext-classification:',
            'samm:',
            'mmm:'
        ]
        
        found_prefixes = []
        missing_prefixes = []
        
        for prefix in expected_prefixes:
            if prefix in output:
                found_prefixes.append(prefix)
                print(f"  ✅ Found prefix: {prefix}")
            else:
                missing_prefixes.append(prefix)
                print(f"  ❌ Missing prefix: {prefix}")
        
        print()
        
        # Check for string literal type declarations (the original problem)
        if 'a "urn:samm:' in output:
            print("❌ ISSUE: Found string literal type declarations (not fixed)")
            print("   Example: a \"urn:samm:io.catenax.batch:3.0.1#...\"")
        else:
            print("✅ No string literal type declarations found (issue fixed!)")
        
        print()
        
        # Show first 50 lines of output
        print("📄 First 50 lines of output:")
        print("=" * 80)
        lines = output.split('\n')[:50]
        for line in lines:
            print(line)
        print("=" * 80)
        
        # Save full output to file
        with open('/home/hanke/RDFConverter/test_output.ttl', 'w') as f:
            f.write(output)
        print()
        print("💾 Full output saved to: test_output.ttl")
        
        return len(found_prefixes) == len(expected_prefixes)
        
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to API. Is the server running?")
        print("   Start the server with: python app.py")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mapping()
    print()
    if success:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed - check output above")
