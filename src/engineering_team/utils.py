import shutil
import os
import re
import zipfile
from datetime import datetime

def strip_markdown_from_python(file_path: str):
    """
    Reads a Python file and aggressively removes any LLM formatting artifacts:
    - Backtick code fences: ```python ... ```
    - Triple-quote wrapper blocks: \"\"\" ... \"\"\" at the start of the file
    Operates in-place.
    """
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # --- Pass 1: Remove backtick code fences ---
    # Opening fence: ```python or ``` on its own line
    content = re.sub(r'^```(?:python)?\s*\n', '', content, flags=re.MULTILINE)
    # Closing fence: ``` on its own line
    content = re.sub(r'\n```\s*$', '', content, flags=re.MULTILINE)
    # Any remaining stray ``` lines
    content = re.sub(r'^```\s*\n?', '', content, flags=re.MULTILINE)

    # --- Pass 2: Remove leading triple-quote wrapper block ---
    # LLMs sometimes wrap the entire output in """ ... """ instead of backticks.
    # We only strip the FIRST such block if it appears before any real Python code.
    # Pattern: file starts with """ (possibly with whitespace), then content, then closing """
    content = re.sub(r'^\s*"""[\s\S]*?"""\s*\n?', '', content, count=1)
    
    # --- Pass 3: Remove any single-line LLM preamble comments like "Here is the code:" ---
    content = re.sub(r'^(?:Here(?:\s+is)?[\s\S]*?:|Sure[,!][\s\S]*?:)\s*\n', '', content, flags=re.IGNORECASE)

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
