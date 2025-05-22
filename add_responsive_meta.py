#!/usr/bin/env python3

"""
Script to add responsive meta tags to all HTML templates
"""

import os
import re

# Define the base directory for templates
templates_dir = "./templates"

# Define the meta tags to be added to all templates
META_TAGS = """    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">"""

# Script reference to be added
SCRIPT_TAG = """    <script src="/static/mobile-menu.js" defer></script>"""

def update_template(file_path):
    """Update a single template file with responsive meta tags."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Check if the meta viewport tag is already present
    if 'name="viewport"' in content:
        print(f"  - Meta viewport already exists in {file_path}")
        return False
    
    # Find the head tag
    head_match = re.search(r'<head>(.*?)</head>', content, re.DOTALL)
    if not head_match:
        print(f"  - No <head> tag found in {file_path}")
        return False
    
    # Get current head content
    head_content = head_match.group(1)
    
    # Check for any meta tags
    title_match = re.search(r'<title>(.*?)</title>', head_content, re.DOTALL)
    
    if title_match:
        # Insert meta tags after title tag
        new_head = head_content.replace(title_match.group(0), 
                                        title_match.group(0) + "\n" + META_TAGS)
    else:
        # Just append meta tags to head
        new_head = head_content + "\n" + META_TAGS
    
    # Add script tag before close of head if not already present
    if 'mobile-menu.js' not in new_head:
        new_head += "\n" + SCRIPT_TAG
    
    # Replace the head content
    new_content = content.replace(head_match.group(1), new_head)
    
    # Write the updated content back to the file
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    print(f"  + Updated {file_path}")
    return True

def process_templates():
    """Process all HTML templates in the templates directory."""
    print("Updating HTML templates with responsive meta tags...")
    
    files_updated = 0
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html') and file != 'base.html' and not file.endswith('.bak'):
                file_path = os.path.join(root, file)
                if update_template(file_path):
                    files_updated += 1
    
    print(f"Updated {files_updated} template files.")

if __name__ == "__main__":
    process_templates()
