import gradio as gr
import os
import sys
import threading
import queue
import time
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from engineering_team.crew import EngineeringTeam
from engineering_team.utils import create_project_zip, cleanup_output, sanitize_all_outputs

# Rate Limiting Tracker
IP_USAGE = {}
MAX_REQUESTS_PER_IP = 15

# CSS for the "Electric Blue" Premium Theme
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap');

body, .gradio-container {
    background-color: #0A0A0B !important;
    color: #F0F0F0 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}
label, .label-wrap span, p, li, td, th {
    color: #D0D8E8 !important;
}
input, textarea, select {
    background-color: #161618 !important;
    border: 1px solid #1E40AF !important;
    color: #F0F0F0 !important;
}
textarea::placeholder, input::placeholder {
    color: #6B7280 !important;
}
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
    color: #D1D5DB !important;
}
button.secondary:hover {
    border-color: #3B82F6 !important;
    color: #F0F0F0 !important;
}
.tab-nav button {
    color: #9CA3AF !important;
}
.tab-nav button.selected {
    color: #3B82F6 !important;
    border-bottom: 2px solid #3B82F6 !important;
}
h1 {
    color: #3B82F6 !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
    text-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
}
h2, h3 {
    color: #60A5FA !important;
}
.terminal-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    background-color: #000000 !important;
    border: 1px solid #1E40AF !important;
    color: #00FF00 !important; /* Classic terminal green */
}
"""

def solve_requirements_streaming(requirements, module_name, class_name, request: gr.Request):
    client_ip = request.client.host if request else "unknown"
    
    if client_ip not in IP_USAGE:
        IP_USAGE[client_ip] = 0
        
    if IP_USAGE[client_ip] >= MAX_REQUESTS_PER_IP:
        yield (f"⚠️ Rate limit reached ({MAX_REQUESTS_PER_IP} runs/IP).",
               "", "", "", "", "", "System Error: Rate limit exceeded for this IP.", gr.update(visible=False))
        return
        
    if len(requirements) > 2000:
        yield ("⚠️ Requirements too long.",
               "", "", "", "", "", "System Error: Input too long.", gr.update(visible=False))
        return

    cleanup_output('output')
    IP_USAGE[client_ip] += 1
    
    log_queue = queue.Queue()
    
    def log_task(task_output):
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] ✅ Task Completed: {task_output.description[:50]}..."
        log_queue.put(msg)
        
    def log_step(step_output):
        timestamp = datetime.now().strftime("%H:%M:%S")
        # Extract agent name if possible or just show generic step
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
    yield ("🚀 Team is working...", "", "", "", "", "", current_logs, gr.update(visible=False))
    
    # Thread result storage
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

    # Stream logs to UI until finished
    while not result_container["done"]:
        try:
            # Try to get all pending logs
            while True:
                new_log = log_queue.get_nowait()
                current_logs += new_log + "\n"
        except queue.Empty:
            pass
        
        yield ("🚀 Team is working... (Check the Terminal below)", "", "", "", "", "", current_logs, gr.update(visible=False))
        time.sleep(0.5)

    if result_container["success"]:
        current_logs += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Engineering Team finished successfully!\n"
        
        # Post-process
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
            "✅ Done!",
            design_content,
            code_content,
            app_content,
            test_content,
            readme_content,
            current_logs,
            gr.update(value=zip_path, visible=True)
        )
    else:
        error_msg = f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {result_container['error']}\n"
        current_logs += error_msg
        yield ("❌ Error occurred", "", "", "", "", "", current_logs, gr.update(visible=False))

# Build UI
with gr.Blocks(theme=gr.themes.Default(), css=custom_css, title="AI Engineering Team") as demo:
    gr.Markdown("# ⚡ AI Engineering Team")
    gr.Markdown("**Full Software Development Automation** — View the real-time activity terminal below.")
    
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
            
            status = gr.Markdown("Ready.")
            download_btn = gr.File(label="⬇️ Download Output (ZIP)", visible=False)
            
            # THE TERMINAL
            terminal_log = gr.TextArea(
                label="💠 Team Activity Terminal",
                placeholder="Agent logs will appear here...",
                lines=12,
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
