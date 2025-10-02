#!/usr/bin/env python3
"""
Final test to verify XML is preserved and only environment_details tags are processed
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, 'src')

from environment_details_manager import EnvironmentDetailsManager

load_dotenv()

def test_xml_preservation():
    """Test that XML content is preserved except for environment_details tags"""
    
    print("🧪 Testing XML preservation with environment_details detection...")
    
    # Test content with various XML and environment_details
    test_content = """<data>
    <config>
        <setting name="test">value & special chars</setting>
        <nested>
            <deep>Deep content</deep>
        </nested>
        <![CDATA[Some CDATA content with <tags>]]>
    </config>
    < 37 |     <other_xml>
        <item>Should be preserved</item>
    </other_xml>
    < 46 | </data>"""
    
    print("Original content:")
    print(test_content)
    print("\n" + "="*50 + "\n")
    
    # Test environment details detection
    manager = EnvironmentDetailsManager()
    
    # Test 1: Detect environment details
    blocks = manager.detect_environment_details(test_content, 0)
    print(f"✅ Detected {len(blocks)} environment_details blocks")
    
    for i, block in enumerate(blocks):
        print(f"  Block {i+1}: {block.content[:50]}...")
    
    # Test 2: Check that other XML is preserved
    remaining_content = test_content
    for block in blocks:
        remaining_content = remaining_content.replace(block.content, "")
    
    print(f"\n✅ Remaining content after removing environment_details:")
    print(remaining_content)
    
    # Verify other XML is still there
    xml_elements_to_check = [
        "<data>",
        "<config>",
        "<setting name=\"test\">value & special chars</setting>",
        "<nested>",
        "<deep>Deep content</deep>",
        "<![CDATA[Some CDATA content with <tags>]]>",
        "<other_xml>",
        "<item>Should be preserved</item>",
        "</data>"
    ]
    
    print(f"\n🔍 Checking if XML elements are preserved:")
    all_preserved = True
    for element in xml_elements_to_check:
        if element in remaining_content:
            print(f"  ✅ {element}")
        else:
            print(f"  ❌ {element} - MISSING!")
            all_preserved = False
    
    # Verify environment_details are removed
    env_details_to_check = [
        "<environment_details>",
        "working_dir",
        "files"
    ]
    
    print(f"\n🔍 Checking if environment_details are removed:")
    all_removed = True
    for element in env_details_to_check:
        if element not in remaining_content:
            print(f"  ✅ {element} - REMOVED")
        else:
            print(f"  ❌ {element} - STILL PRESENT!")
            all_removed = False
    
    # Final result
    if all_preserved and all_removed:
        print(f"\n🎉 SUCCESS: XML is preserved, only environment_details are processed!")
        return True
    else:
        print(f"\n❌ FAILURE: XML preservation or environment_details removal failed!")
        return False

if __name__ == "__main__":
    success = test_xml_preservation()
    sys.exit(0 if success else 1)