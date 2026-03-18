#!/usr/bin/env python3
"""
Remove all Chinese text from Agent SOUL.md files
Replace with pure English
"""

import pathlib
import re

ROOT = pathlib.Path('/home/auto/.openclaw/workspace-taizi/onepersonlab-agents/agents')

# Chinese to English replacements
REPLACEMENTS = [
    # Role names
    ('太子 (Crown Prince)', 'Crown Prince'),
    ('皇上 (Emperor)', 'Emperor'),
    ('中书省', 'Planning Office'),
    ('门下省', 'Review Board'),
    ('尚书省', 'Operations Office'),
    ('六部', 'Six Ministries'),
    
    # Common phrases
    ('阶段性进展', 'stage progress'),
    ('严禁', 'strictly forbid'),
    ('封驳', 'veto'),
    
    # Task ID format - change OPL to OPL (keep)
    # But remove Chinese comments
]

def remove_chinese(content):
    """Remove Chinese characters and replace with English"""
    result = content
    
    # Apply specific replacements first
    for zh, en in REPLACEMENTS:
        result = result.replace(zh, en)
    
    # Remove remaining Chinese characters in comments/parentheses
    # Pattern: match Chinese characters
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    
    # Remove Chinese from parenthetical notes
    lines = result.split('\n')
    cleaned_lines = []
    for line in lines:
        # Remove Chinese characters but keep the line
        cleaned_line = chinese_pattern.sub('', line)
        # Clean up multiple spaces
        cleaned_line = re.sub(r'\s+', ' ', cleaned_line)
        # Remove empty parentheses
        cleaned_line = cleaned_line.replace('( )', '').replace('()', '')
        cleaned_lines.append(cleaned_line)
    
    return '\n'.join(cleaned_lines)

def process_file(filepath):
    """Process a single SOUL.md file"""
    content = filepath.read_text(encoding='utf-8')
    
    # Check if has Chinese
    if not re.search(r'[\u4e00-\u9fff]', content):
        print(f"  - {filepath.parent.name}: No Chinese found")
        return False
    
    cleaned = remove_chinese(content)
    filepath.write_text(cleaned, encoding='utf-8')
    print(f"  ✓ {filepath.parent.name}: Chinese removed")
    return True

def main():
    print("🧹 Removing Chinese from Agent SOUL.md files")
    print("=" * 50)
    
    processed = 0
    for soul_file in ROOT.glob('*/SOUL.md'):
        if process_file(soul_file):
            processed += 1
    
    print("=" * 50)
    print(f"✅ Complete: {processed} agents cleaned")

if __name__ == '__main__':
    main()
