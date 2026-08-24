import shutil
import os
import re
import sys
import zipfile
import time
from datetime import datetime


def safe_read_file(file_path: str) -> str:
    """Safely reads the content of a file with UTF-8 encoding if it exists."""
    if not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def strip_markdown_from_python(file_path: str):
    """
    The SuperSanitizer: Ensures that a Python file contains ONLY Python code,
    stripped of all LLM-generated artifacts, markdown fences, and conversational filler.
    """
    if not os.path.exists(file_path):
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    # 1. Broad extraction: Find the largest block between backticks if they exist
    code_block_match = re.search(r'```(?:python)?\s*\n?([\s\S]*?)\n?```', content, re.IGNORECASE)
    if code_block_match:
        content = code_block_match.group(1).strip()

    # 2. Triple-Quote Wrapper stripping
    wrapper_match = re.match(r'^\s*("""|\'\'\')\s*\n?([\s\S]*?)\n?\s*\1\s*$', content)
    if wrapper_match:
        content = wrapper_match.group(2).strip()

    # 3. Clean any remaining outer backticks (fences)
    content = content.strip().strip('`').strip()

    # 4. Entry Point Scan: Discard all preamble lines & shebangs
    lines = [l for l in content.split('\n') if not l.startswith(('#!', '# -*- coding:'))]

    start_idx = 0
    found_start = False
    for i, line in enumerate(lines):
        clean_line = line.strip()
        if clean_line.startswith(('import ', 'from ', 'class ', 'def ', '#', '@', '"""', "'''")):
            # Ignore conversational false positives
            if not any(filler in clean_line.lower() for filler in ["here is", "surely", "certainly", "the code below", "this module", "below is"]):
                start_idx = i
                found_start = True
                break

    content = '\n'.join(lines[start_idx:]) if found_start else '\n'.join(lines)

    # 5. Final pass: ensure no trailing markdown garbage
    content = content.strip()
    if content.endswith('```'):
        content = content[:-3].strip()

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')


def resolve_task_target(description: str, task_index: int, output_dir: str, module_name: str) -> tuple[str, str]:
    """
    Maps task description or execution index to (task_type, target_file_path).
    """
    desc_lower = description.lower() if description else ""

    if "blueprint" in desc_lower or "design" in desc_lower or task_index == 1:
        return "design_task", os.path.join(output_dir, f"{module_name}_design.md")
    elif "requirements.txt" in desc_lower or task_index == 6:
        return "requirements_task", os.path.join(output_dir, "requirements.txt")
    elif "readme.md" in desc_lower or "documentation" in desc_lower or task_index == 5:
        return "documentation_task", os.path.join(output_dir, "README.md")
    elif "unit test" in desc_lower or "test_task" in desc_lower or task_index == 4:
        return "test_task", os.path.join(output_dir, f"test_{module_name}")
    elif "gradio ui" in desc_lower or task_index == 3:
        return "frontend_task", os.path.join(output_dir, "app.py")
    elif "implement the logic" in desc_lower or ("logic" in desc_lower and "gradio" not in desc_lower) or task_index == 2:
        return "code_task", os.path.join(output_dir, module_name)
    
    return "unknown_task", ""


def save_task_artifact(task_output, task_type: str, target_file: str) -> None:
    """
    Extracts, normalizes, sanitizes, and persists task output content to disk.
    """
    if not target_file:
        return

    # Extract raw content or Pydantic code field
    if getattr(task_output, 'pydantic', None) and hasattr(task_output.pydantic, 'code'):
        content = task_output.pydantic.code
    else:
        content = str(getattr(task_output, 'raw', task_output))

    # Specific normalization for requirements.txt
    if task_type == "requirements_task":
        if "gradio" not in content.lower() or "gradio==" in content.lower() or "gradio<" in content.lower():
            content = "\n".join([l for l in content.split("\n") if "gradio" not in l.lower()])
            content += "\ngradio>=5.0.0"
        if "requests" not in content.lower():
            content += "\nrequests"

        std_libs = getattr(sys, 'stdlib_module_names', {"math", "os", "sys", "json", "datetime", "random", "re", "time", "unittest", "logging"})
        clean_req_lines = [
            line for line in content.split("\n")
            if line.strip().split("=")[0].split(">")[0].split("<")[0].lower() not in std_libs
        ]
        content = "\n".join(clean_req_lines)

    # Write out raw content
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)

    # Post-process Python files
    if target_file.endswith('.py'):
        # Fix deprecated Gradio parameters
        content = content.replace("readonly=True", "interactive=False").replace("readonly = True", "interactive=False")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

        strip_markdown_from_python(target_file)

        # Remove any leaked Gradio imports from pure backend logic
        if task_type == "code_task":
            with open(target_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            clean_lines = [l for l in lines if not any(bad in l.lower() for bad in ["import gradio", "from gradio", "gr.", ".launch("])]
            with open(target_file, 'w', encoding='utf-8') as f:
                f.writelines(clean_lines)


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

    parent_dir = os.path.dirname(os.path.abspath(output_dir))
    zip_path = os.path.join(parent_dir, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output_dir))

    return zip_path


def cleanup_old_sessions(output_base='output', max_age_hours=1):
    """
    Cleans up subdirectories inside output_base and old ZIP files older than max_age_hours.
    """
    if not os.path.exists(output_base):
        os.makedirs(output_base, exist_ok=True)
        return

    now = time.time()
    for item in os.listdir(output_base):
        item_path = os.path.join(output_base, item)
        if os.path.getmtime(item_path) > now - (max_age_hours * 3600):
            continue

        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            elif item.endswith('.zip') and item.startswith('ai_engineered_'):
                os.remove(item_path)
        except Exception:
            pass
