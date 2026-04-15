import gradio as gr
import os
import shutil
import time
from threading import Thread
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from engineering_team.crew import EngineeringTeam
from engineering_team.utils import create_project_zip, cleanup_output, sanitize_all_outputs

# Rate Limiting Tracker
IP_USAGE = {}
MAX_REQUESTS_PER_IP = 15

# CSS for the "Electric Blue" Premium Theme
custom_css = """
body, .gradio-container {
    background-color: #0A0A0B !important;
    color: #E0E0E0 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}
.sidebar, .main {
    background-color: #0A0A0B !important;
}
input, textarea, select {
    background-color: #161618 !important;
    border: 1px solid #1E40AF !important;
    color: white !important;
}
button.primary {
    background: linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%) !important;
    border: none !important;
    box-shadow: 0 4px 15px rgba(30, 64, 175, 0.4) !important;
}
button.primary:hover {
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6) !important;
    transform: translateY(-1px);
}
.tabs {
    border-bottom: 1px solid #1E40AF !important;
}
.tabitem.selected {
    border-color: #3B82F6 !important;
}
#log-container {
    background-color: #000000 !important;
    border: 1px solid #1E40AF !important;
    border-radius: 8px;
}
h1, h2, h3 {
    color: #3B82F6 !important;
    text-shadow: 0 0 10px rgba(59, 130, 246, 0.3) ;
}
"""

def solve_requirements(requirements, module_name, class_name, request: gr.Request):
    # Simple IP-based Rate Limiter (anti-bot / anti-spam)
    client_ip = request.client.host if request else "unknown"
    
    if client_ip not in IP_USAGE:
        IP_USAGE[client_ip] = 0
        
    if IP_USAGE[client_ip] >= MAX_REQUESTS_PER_IP:
        yield f"⚠️ Rate limit exceeded for IP {client_ip}. Maximum {MAX_REQUESTS_PER_IP} test runs allowed to prevent spam.", "", "", "", "", gr.update(visible=False)
        return
        
    # Input length protection to prevent token-bombing
    if len(requirements) > 2000:
        yield "⚠️ Requirements input too long. Please keep the description under 2000 characters.", "", "", "", "", gr.update(visible=False)
        return

    # Prepare output directory
    cleanup_output('output')
    
    IP_USAGE[client_ip] += 1
    
    # Store inputs for the crew
    inputs = {
        'requirements': requirements,
        'module_name': module_name,
        'class_name': class_name
    }
    
    # Status updates
    yield f"Initializing Engineering Team... (Run {IP_USAGE[client_ip]}/{MAX_REQUESTS_PER_IP} for this IP)", None, None, None, None, gr.update(visible=False)
    
    # Run the crew
    try:
        # Note: In a production environment, you might want to redirect stdout to capture logs
        result = EngineeringTeam().crew().kickoff(inputs=inputs)
        
        # Post-process: strip any LLM markdown artifacts (backticks) from Python files
        sanitize_all_outputs('output', module_name)
        
        # Read generated files
        design_file = f"output/{module_name}_design.md"
        code_file = f"output/{module_name}"
        app_file = "output/app.py"
        test_file = f"output/test_{module_name}"
        
        design_content = ""
        if os.path.exists(design_file):
            with open(design_file, 'r', encoding='utf-8') as f:
                design_content = f.read()
                
        code_content = ""
        if os.path.exists(code_file):
            with open(code_file, 'r', encoding='utf-8') as f:
                code_content = f.read()
                
        app_content = ""
        if os.path.exists(app_file):
            with open(app_file, 'r', encoding='utf-8') as f:
                app_content = f.read()
                
        test_content = ""
        if os.path.exists(test_file):
            with open(test_file, 'r', encoding='utf-8') as f:
                test_content = f.read()
                
        # Create ZIP for download
        zip_path = create_project_zip('output', zip_name_prefix=module_name.split('.')[0])
        
        yield (
            "Successfully built the application! View the results in the tabs below.",
            design_content,
            code_content,
            app_content,
            test_content,
            gr.update(value=zip_path, visible=True)
        )
    except Exception as e:
        yield f"Error occurred: {str(e)}", None, None, None, None, gr.update(visible=False)

# Build UI
with gr.Blocks(theme=gr.themes.Default(), css=custom_css, title="AI Engineering Team") as demo:
    gr.Markdown("# ⚡ AI Engineering Team")
    gr.Markdown("### Full Software Development Automation - From Requirements to Design, Code, UI, and Tests.")
    
    with gr.Row():
        with gr.Column(scale=1):
            reqs = gr.TextArea(
                label="Requirements", 
                placeholder="Describe the software you want the team to build...",
                lines=10,
                value="A simple account management system for a trading simulation platform.\nThe system should allow users to create an account, deposit funds, and withdraw funds.\nThe system should allow users to record that they have bought or sold shares, providing a quantity."
            )
            with gr.Row():
                mod_name = gr.Textbox(label="Module Name", value="accounts.py")
                cls_name = gr.Textbox(label="Class Name", value="Account")
            
            run_btn = gr.Button("🚀 KICKOFF TEAM", variant="primary")
            
            status = gr.Markdown("Ready to build.")
            download_btn = gr.File(label="Download Generated Project", visible=False)
            
        with gr.Column(scale=2):
            with gr.Tabs() as tabs:
                with gr.TabItem("📋 Architecture Design"):
                    design_out = gr.Markdown("Waiting for kickoff...")
                with gr.TabItem("🐍 Backend Code"):
                    code_out = gr.Code(language="python")
                with gr.TabItem("🖥️ Gradio App"):
                    app_out = gr.Code(language="python")
                with gr.TabItem("🧪 Unit Tests"):
                    test_out = gr.Code(language="python")

    run_btn.click(
        fn=solve_requirements,
        inputs=[reqs, mod_name, cls_name],
        outputs=[status, design_out, code_out, app_out, test_out, download_btn]
    )

if __name__ == "__main__":
    # Queue is essential to handle traffic safely and limit concurrency
    demo.queue(default_concurrency_limit=1, max_size=10).launch()
