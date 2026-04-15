import gradio as gr
import os
import sys
import threading
import queue
import time
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from engineering_team.crew import EngineeringTeam
from engineering_team.utils import create_project_zip, cleanup_output, sanitize_all_outputs, strip_markdown_from_python

# Rate Limiting Tracker
IP_USAGE = {}
MAX_REQUESTS_PER_IP = 15

# Task to Friendly Log Mapping - Short, interesting status updates
TASK_LOG_MAP = {
    "design_task": "🧠 Architecting the system blueprint...",
    "code_task": "💻 Engineering core backend logic...",
    "frontend_task": "📱 Building Gradio demonstration interface...",
    "test_task": "🧪 Writing comprehensive unit tests...",
    "documentation_task": "📖 Generating professional project documentation..."
}

# CSS for the "Electric Blue" Premium Theme
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap');

body, .gradio-container {
    background-color: #0A0A0B !important;
    color: #F8FAFC !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}

/* 1. Global High-Contrast Text Fixes */
/* Targets all leipäteksti, markdown items, and labels */
p, li, th, td, label, .markdown-text, .gr-form span {
    color: #FFFFFF !important;
    opacity: 1 !important;
}

/* Targets the subtitle specifically */
.gradio-container .prose p, .gradio-container .prose span {
    color: #E2E8F0 !important;
}

/* 2. Tab Menu Polishing */
/* This ensures tab headers are clearly visible and professional */
div.tabs button {
    color: #94A3B8 !important;
    font-weight: 500 !important;
}
div.tabs button.selected {
    color: #60A5FA !important;
    border-bottom: 2px solid #60A5FA !important;
}
div.tabs button:hover {
    color: #FFFFFF !important;
}

/* 3. Input & Terminal Styling */
input, textarea, select {
    background-color: #161618 !important;
    border: 1px solid #1E40AF !important;
    color: #FFFFFF !important;
}
textarea::placeholder, input::placeholder {
    color: #64748B !important;
}
.terminal-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    background-color: #000000 !important;
    border: 1px solid #1E40AF !important;
    color: #4ADE80 !important;
    white-space: pre-wrap !important;
}

/* 4. Primary Button Styling */
button.primary {
    background: linear-gradient(90deg, #1E40AF 0%, #3B82F6 100%) !important;
    border: none !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 15px rgba(30, 64, 175, 0.4) !important;
}
button.primary:hover {
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6) !important;
    transform: translateY(-1px);
}
button.secondary {
    background: #1C1C1E !important;
    border: 1px solid #374151 !important;
    color: #E2E8F0 !important;
}

/* Title Styling */
h1 {
    color: #3B82F6 !important;
    font-size: 2.2rem !important;
    font-weight: 700 !important;
    text-shadow: 0 0 20px rgba(59, 130, 246, 0.4);
}
h2, h3 {
    color: #60A5FA !important;
    border-bottom: 1px solid #1E3A8A;
    padding-bottom: 5px;
}
"""

def solve_requirements_streaming(requirements, module_name, class_name, request: gr.Request):
    client_ip = request.client.host if request else "unknown"
    
    if client_ip not in IP_USAGE:
        IP_USAGE[client_ip] = 0
        
    if IP_USAGE[client_ip] >= MAX_REQUESTS_PER_IP:
        yield ("⚠️ Rate limit reached (15 runs/IP).",
               "", "", "", "", "", "System Error: Rate limit reached.", gr.update(visible=False))
        return
        
    if len(requirements) > 2000:
        yield ("⚠️ Requirements too long.",
               "", "", "", "", "", "System Error: Input too long.", gr.update(visible=False))
        return

    cleanup_output('output')
    IP_USAGE[client_ip] += 1
    
    log_queue = queue.Queue()
    os.makedirs('output', exist_ok=True)
    
    def log_task(task_output):
        timestamp = datetime.now().strftime("%H:%M:%S")
        description = task_output.description.lower()
        
        target_file = None
        current_task_type = None
        
        if "prepare a professional engineering blueprint" in description:
            current_task_type = "design_task"
        elif "write a python module" in description:
            current_task_type = "code_task"
            target_file = os.path.join("output", module_name)
        elif "write a gradio ui" in description:
            current_task_type = "frontend_task"
            target_file = os.path.join("output", "app.py")
        elif "write unit tests" in description:
            current_task_type = "test_task"
            target_file = os.path.join("output", f"test_{module_name}")
        elif "write a professional readme.md" in description:
            current_task_type = "documentation_task"

        if target_file and task_output.pydantic:
            try:
                code = task_output.pydantic.code
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(code)
                strip_markdown_from_python(target_file)
                msg = f"[{timestamp}] 💾 File Saved: {os.path.basename(target_file)}"
            except Exception as e:
                msg = f"[{timestamp}] ⚠️ Error saving file: {str(e)}"
        else:
            summary = TASK_LOG_MAP.get(current_task_type, f"Task Completed: {task_output.description[:50]}...")
            msg = f"[{timestamp}] ✅ {summary}"
            
        log_queue.put(msg)
        
    def log_step(step_output):
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] ⚙️ Agent thinking..."
        if hasattr(step_output, 'agent'):
             msg = f"[{timestamp}] 🤖 {step_output.agent} is active..."
        log_queue.put(msg)

    inputs = {
        'requirements': requirements,
        'module_name': module_name,
        'class_name': class_name
    }
    
    current_logs = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Initializing Engineering Team...\n"
    yield ("🚀 Rocket Engineering Team is starting... (Approx 3-8 mins)", "", "", "", "", "", current_logs, gr.update(visible=False))
    
    result_container = {"success": False, "data": None, "error": None, "done": False}

    def run_crew():
        try:
            crew_obj = EngineeringTeam(task_callback=log_task, step_callback=log_step).crew()
            result_container["data"] = crew_obj.kickoff(inputs=inputs)
            result_container["success"] = True
        except Exception as e:
            result_container["error"] = str(e)
        finally:
            result_container["done"] = True

    thread = threading.Thread(target=run_crew)
    thread.start()

    while not result_container["done"]:
        try:
            while True:
                new_log = log_queue.get_nowait()
                current_logs += new_log + "\n"
        except queue.Empty:
            pass
        
        yield ("🚀 Rocket Engineering Team is working... (Approx 3-8 mins)", "", "", "", "", "", current_logs, gr.update(visible=False))
        time.sleep(1)

    if result_container["success"]:
        current_logs += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Engineering Team finished successfully!\n"
        
        sanitize_all_outputs('output', module_name)
        
        def read_file(path):
            return open(path, 'r', encoding='utf-8').read() if os.path.exists(path) else ""
        
        design_content = read_file(f"output/{module_name}_design.md")
        code_content   = read_file(f"output/{module_name}")
        app_content    = read_file("output/app.py")
        test_content   = read_file(f"output/test_{module_name}")
        readme_content = read_file("output/README.md")
                
        zip_path = create_project_zip('output', zip_name_prefix=module_name.split('.')[0])
        
        yield (
            "✅ All projects generated! Download your ZIP below.",
            design_content,
            code_content,
            app_content,
            test_content,
            readme_content,
            current_logs,
            gr.update(value=zip_path, visible=True)
        )
    else:
        current_logs += f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {result_container['error']}\n"
        yield ("❌ Error occurred during engineering process.", "", "", "", "", "", current_logs, gr.update(visible=False))

# Build UI
with gr.Blocks(theme=gr.themes.Default(), css=custom_css, title="AI Engineering Team") as demo:
    gr.Markdown("# ⚡ AI Engineering Team")
    # Subtitle contrast fix via Markdown structure
    gr.Markdown("Full Software Development Automation — View the real-time activity terminal below.")
    
    with gr.Row():
        with gr.Column(scale=1):
            reqs = gr.TextArea(
                label="Requirements", 
                placeholder="Describe the software you want building...",
                lines=8,
                value="A simple account management system for a trading simulation platform.\nThe system should allow users to create an account, deposit funds, and withdraw funds."
            )
            with gr.Row():
                mod_name = gr.Textbox(label="Module Name", value="accounts.py")
                cls_name = gr.Textbox(label="Class Name", value="Account")
            
            with gr.Row():
                run_btn   = gr.Button("🚀 KICKOFF TEAM", variant="primary", scale=3)
                reset_btn = gr.Button("🔄 Reset", variant="secondary", scale=1)
            
            status = gr.Markdown("Ready to engineer.")
            download_btn = gr.File(label="⬇️ Download Output (ZIP)", visible=False)
            
            terminal_log = gr.TextArea(
                label="💠 Team Activity Terminal",
                placeholder="Agent logs will appear here...",
                lines=15,
                interactive=False,
                elem_classes=["terminal-box"]
            )
            
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("📋 Architecture Design"):
                    design_out = gr.Markdown("Waiting...")
                with gr.TabItem("🐍 Backend Code"):
                    code_out = gr.Code(language="python")
                with gr.TabItem("🖥️ Gradio App"):
                    app_out = gr.Code(language="python")
                with gr.TabItem("🧪 Unit Tests"):
                    test_out = gr.Code(language="python")
                with gr.TabItem("📖 Project README"):
                    readme_out = gr.Markdown("Waiting...")

    run_btn.click(
        fn=solve_requirements_streaming,
        inputs=[reqs, mod_name, cls_name],
        outputs=[status, design_out, code_out, app_out, test_out, readme_out, terminal_log, download_btn]
    )
    
    reset_btn.click(fn=None, js="() => { window.location.reload(); }")

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1, max_size=10).launch()
