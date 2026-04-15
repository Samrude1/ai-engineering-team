import shutil
import os
import zipfile
from datetime import datetime

def create_project_zip(output_dir='output', zip_name_prefix='engineering_project'):
    """
    Creates a ZIP file containing the contents of the output directory.
    """
    if not os.path.exists(output_dir):
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{zip_name_prefix}_{timestamp}.zip"
    zip_path = os.path.join(os.path.dirname(output_dir), zip_filename)
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Store files relative to the output_dir
                zipf.write(file_path, os.path.relpath(file_path, output_dir))
    
    return zip_path

def cleanup_output(output_dir='output'):
    """
    Cleans up the output directory before a new run.
    """
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
