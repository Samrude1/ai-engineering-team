import shutil
import os
import re
import zipfile
from datetime import datetime

def strip_markdown_from_python(file_path: str):
    """
    Reads a Python file and aggressively removes ANY LLM formatting artifacts.
    """
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # Pass 1: Extract content between ```python and ``` or ``` and ```
    code_block_match = re.search(r'```(?:python)?\s*\n?([\s\S]*?)\n?```', content, re.IGNORECASE)
    if code_block_match:
        content = code_block_match.group(1).strip()
    
    # Pass 2: Extreme Triple-Quote Wrapper stripping
    # Sometimes LLMs wrap the whole file in """ ... """ or ''' ... '''
    # We look for leading/trailing triple quotes that encompass the whole content.
    # We use a non-greedy dotall match to check if it's one big outer block.
    wrapper_match = re.match(r'^\s*("""|\'\'\')\s*\n?([\s\S]*?)\n?\s*\1\s*$', content)
    if wrapper_match:
        content = wrapper_match.group(2).strip()

    # Pass 3: Remove any leading/trailing single/double quotes (LLM "string" output)
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1].strip()
    if content.startswith("'") and content.endswith("'"):
        content = content[1:-1].strip()

    # Pass 4: "Find the Python" - discard anything before the first valid Python line
    lines = content.split('\n')
    start_idx = 0
    found_start = False
    for i, line in enumerate(lines):
        clean_line = line.strip()
        # Look for typical Python entry points
        if clean_line.startswith(('import ', 'from ', 'class ', 'def ', '#', '@', '"""', "'''")):
            # Double check it's not a conversational filler
            if not any(filler in clean_line.lower() for filler in ["here is", "surely", "certainly", "the code below", "this module"]):
                start_idx = i
                found_start = True
                break
    
    if found_start:
        content = '\n'.join(lines[start_idx:])

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
    # e.g., ai_engineered_accounts_20260415_190000.zip
    clean_prefix = zip_name_prefix.replace('.py', '').replace(' ', '_').lower()
    zip_filename = f"ai_engineered_{clean_prefix}_{timestamp}.zip"
    zip_path = os.path.join(os.path.dirname(os.path.abspath(output_dir)), zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Store files relative to output_dir
                zipf.write(file_path, os.path.relpath(file_path, output_dir))
    
    return zip_path


def cleanup_output(output_dir='output'):
    """
    Cleans up the output directory before a new run.
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
