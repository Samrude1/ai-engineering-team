import shutil
import os
import re
import zipfile
import time
from datetime import datetime

def strip_markdown_from_python(file_path: str):
    """
    The SuperSanitizer: Its only purpose in the universe is to ensure
    that a Python file contains ONLY Python code, stripped of all
    LLM-generated artifacts, markdown fences, and conversational filler.
    """
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # 1. Broad extraction: Find the largest block between backticks if they exist
    code_block_match = re.search(r'```(?:python)?\s*\n?([\s\S]*?)\n?```', content, re.IGNORECASE)
    if code_block_match:
        content = code_block_match.group(1).strip()
    
    # 2. Triple-Quote Wrapper stripping (The 'Gemini Fix')
    wrapper_match = re.match(r'^\s*("""|\'\'\')\s*\n?([\s\S]*?)\n?\s*\1\s*$', content)
    if wrapper_match:
        content = wrapper_match.group(2).strip()

    # 3. Clean any remaining outer backticks (fences)
    content = content.strip().strip('`').strip()

    # 4. Entry Point Scan: Discard all preamble lines
    lines = content.split('\n')
    
    # NEW: Specific removal of shebangs and coding declarations that clutter Windows/Web environments
    lines = [l for l in lines if not l.startswith(('#!', '# -*- coding:'))]
    
    start_idx = 0
    found_start = False
    for i, line in enumerate(lines):
        clean_line = line.strip()
        # Look for explicit Python markers
        if clean_line.startswith(('import ', 'from ', 'class ', 'def ', '#', '@', '"""', "'''")):
            # Ignore false positives like "Here is the class..."
            if not any(filler in clean_line.lower() for filler in ["here is", "surely", "certainly", "the code below", "this module", "below is"]):
                start_idx = i
                found_start = True
                break
    
    if found_start:
        content = '\n'.join(lines[start_idx:])
    else:
        content = '\n'.join(lines)

    # 5. Final pass: ensure no trailing markdown garbage
    content = content.strip()
    if content.endswith('```'):
        content = content[:-3].strip()

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')






def sanitize_all_outputs(output_dir: str, module_name: str):
    """
    Runs post-processing on all generated Python files to remove LLM markdown artifacts.
    """
    python_files = [
        os.path.join(output_dir, module_name),
        os.path.join(output_dir, 'app.py'),
        os.path.join(output_dir, f'test_{module_name}'),
    ]
    for f in python_files:
        strip_markdown_from_python(f)


def create_project_zip(output_dir='output', zip_name_prefix='engineering_project'):
    """
    Creates a descriptively named ZIP file containing the contents of the output directory.
    """
    if not os.path.exists(output_dir):
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_prefix = zip_name_prefix.replace('.py', '').replace(' ', '_').lower()
    zip_filename = f"ai_engineered_{clean_prefix}_{timestamp}.zip"
    
    # Store the zip in the parent of output_dir (e.g. 'output' if output_dir is 'output/uuid')
    # If output_dir is 'output/uuid', parent is 'output'
    parent_dir = os.path.dirname(os.path.abspath(output_dir))
    zip_path = os.path.join(parent_dir, zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output_dir))
    
    return zip_path


def cleanup_old_sessions(output_base='output', max_age_hours=1):
    """
    Cleans up subdirectories inside output_base and old ZIP files that are older than max_age_hours.
    This ensures concurrent sessions don't conflict, and disk space is freed up over time.
    """
    if not os.path.exists(output_base):
        os.makedirs(output_base, exist_ok=True)
        return

    now = time.time()
    for item in os.listdir(output_base):
        item_path = os.path.join(output_base, item)
        # Skip if it's too new
        if os.path.getmtime(item_path) > now - (max_age_hours * 3600):
            continue
            
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            elif item.endswith('.zip') and item.startswith('ai_engineered_'):
                os.remove(item_path)
        except Exception:
            pass
