#!/usr/bin/env python3
"""
Script to clean JUnit XML files for better compatibility with GitHub Actions.

This script removes problematic characters and ensures the XML is well-formed
for proper display in GitHub Actions test reports.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def clean_junit_xml(input_file="pytest-junit.xml", output_file="pytest-junit-clean.xml"):
    """
    Clean JUnit XML file by removing problematic characters and ensuring compatibility.
    
    Args:
        input_file (str): Path to the input JUnit XML file
        output_file (str): Path to the output cleaned XML file
    """
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        print(f"❌ Input file {input_file} not found")
        return False
    
    try:
        # Read the XML content
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Remove invalid XML characters (control characters except tab, newline, carriage return)
        # XML 1.0 valid characters: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
        valid_chars = []
        for char in content:
            code = ord(char)
            if (code == 0x09 or code == 0x0A or code == 0x0D or 
                (0x20 <= code <= 0xD7FF) or 
                (0xE000 <= code <= 0xFFFD) or 
                (0x10000 <= code <= 0x10FFFF)):
                valid_chars.append(char)
            else:
                # Replace invalid characters with a space
                valid_chars.append(' ')
        
        cleaned_content = ''.join(valid_chars)
        
        # Remove ANSI escape sequences (color codes)
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned_content = ansi_escape.sub('', cleaned_content)
        
        # Clean up multiple spaces
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content)
        
        # Try to parse and validate the XML
        try:
            root = ET.fromstring(cleaned_content)
            
            # Ensure the XML is well-formed by writing it back
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            print(f"✅ Successfully cleaned {input_file} -> {output_file}")
            return True
            
        except ET.ParseError as e:
            print(f"⚠️ XML parsing error after cleaning: {e}")
            # If parsing fails, just write the cleaned content as-is
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"✅ Wrote cleaned content to {output_file} (may have parsing issues)")
            return True
            
    except Exception as e:
        print(f"❌ Error cleaning XML file: {e}")
        return False


if __name__ == "__main__":
    success = clean_junit_xml()
    if not success:
        exit(1)