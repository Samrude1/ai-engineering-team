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

# Task to Friendly Log Mapping
TASK_LOG_MAP = {
    "design_task": "🧠 Architecting the system blueprint...",
    "code_task": "💻 Engineering core backend logic...",
    "frontend_task": "📱 Building Gradio demonstration interface...",
    "test_task": "🧪 Writing comprehensive unit tests...",
    "documentation_task": "📖 Generating professional project documentation..."
}

# Custom CSS for the Professional Minimalist 'Zinc' Theme (Matching Sidekick)
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

body {
    margin: 0 !important;
    padding: 0 !important;
    overflow-x: hidden !important;
    width: 100% !important;
}

body, .gradio-container {
    font-family: 'Inter', -apple-system, sans-serif !important;
    background-color: #fdfdfd !important;
    color: #1a1a1a !important;
}

.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding-left: 20px !important;
    padding-right: 20px !important;
    width: 100% !important;
}

/* Typography */
h1 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    color: #111111 !important;
    letter-spacing: -0.03em !important;
    margin-bottom: 0.2rem !important;
    font-size: 2.2rem !important;
}

@media (max-width: 768px) {
    h1 {
        font-size: 1.6rem !important;
    }
    .gradio-container {
        padding-left: 10px !important;
        padding-right: 10px !important;
    }
    /* Force ALL rows to stack on mobile */
    .gradio-container .row, 
    .gradio-container .gap,
    .gradio-container [class*="row-"] {
        flex-direction: column !important;
        flex-wrap: wrap !important;
    }
    /* Ensure columns and form elements take full width */
    .gradio-container .column,
    .gradio-container .form,
    .gradio-container [class*="column-"],
    .gradio-container .tabs {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
    }
}

h2, h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    color: #111111 !important;
    letter-spacing: -0.02em !important;
    border-bottom: 1px solid #eaeaea;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem !important;
}

p, li, th, td, label, span {
    color: #374151 !important; /* Slate 700 */
}

/* Inputs (Exclude Checkboxes from global overrides) */
input:not([type="checkbox"]), textarea {
    background-color: #ffffff !important;
    border: 1px solid #d4d4d4 !important;
    border-radius: 6px !important;
    color: #111111 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    padding: 10px !important;
    max-width: 100% !important;
}

input:focus, textarea:focus {
    border-color: #111111 !important;
    box-shadow: 0 0 0 1px #111111 !important;
    outline: none !important;
}

/* Buttons */
button.primary {
    background: #111111 !important;
    color: #ffffff !important;
    border: 1px solid #111111 !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08) !important;
    transition: all 0.2s ease !important;
    padding: 10px 20px !important;
    width: 100% !important;
}

@media (min-width: 768px) {
    button.primary {
        width: auto !important;
    }
}

button.primary:hover {
    background: #2a2a2a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12) !important;
}

button.secondary {
    background: #ffffff !important;
    color: #111111 !important;
    border: 1px solid #d4d4d4 !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}

button.secondary:hover {
    background: #f9fafb !important;
    border-color: #111111 !important;
}

/* Terminal & Logs */
.terminal-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    background-color: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    color: #111827 !important;
    white-space: pre-wrap !important;
    border-radius: 8px !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
    overflow-x: hidden !important;
}

/* Tabs */
div.tabs {
    border: none !important;
    background: transparent !important;
}

div.tabs button {
    font-weight: 500 !important;
    color: #6b7280 !important;
    border-bottom: 2px solid transparent !important;
}

div.tabs button.selected {
    color: #111111 !important;
    border-bottom: 2px solid #111111 !important;
    background: transparent !important;
}

/* Fix for right-side data cutoff */
.tabitem {
    background: #ffffff !important;
    border: 1px solid #e5e7eb !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 20px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
    overflow-x: auto !important;
}

@media (max-width: 768px) {
    .tabitem {
        padding: 10px !important;
    }
}

"""

def solve_requirements_streaming(requirements, module_name, class_name, request: gr.Request):
    client_ip = request.client.host if request else "unknown"
    if client_ip not in IP_USAGE: IP_USAGE[client_ip] = 0
    if IP_USAGE[client_ip] >= MAX_REQUESTS_PER_IP:
        yield ("⚠️ Rate limit reached.", "", "", "", "", "", "System Error: Rate limit.", gr.update(visible=False))
        return
    
    if not requirements.strip():
        yield ("⚠️ Please enter your requirements.", "", "", "", "", "", "Input Error: Empty requirements.", gr.update(visible=False))
        return

    cleanup_output('output')
    IP_USAGE[client_ip] += 1
    log_queue = queue.Queue()
    os.makedirs('output', exist_ok=True)
    
    result_container = {"success": False, "data": None, "error": None, "done": False, "task_index": 0}
    
    def log_task(task_output):
        timestamp = datetime.now().strftime("%H:%M:%S")
        result_container["task_index"] += 1
        idx = result_container["task_index"]
        
        target_file = None
        current_task_type = None
        
        # Mapping by sequential index (1-based)
        if idx == 1: # design_task
            current_task_type = "design_task"
            target_file = os.path.join("output", f"{module_name}_design.md")
        elif idx == 2: # code_task
            current_task_type = "code_task"
            target_file = os.path.join("output", module_name)
        elif idx == 3: # frontend_task
            current_task_type = "frontend_task"
            target_file = os.path.join("output", "app.py")
        elif idx == 4: # test_task
            current_task_type = "test_task"
            target_file = os.path.join("output", f"test_{module_name}")
        elif idx == 5: # documentation_task
            current_task_type = "documentation_task"
            target_file = os.path.join("output", "README.md")
        elif idx == 6: # requirements_task
            current_task_type = "requirements_task"
            target_file = os.path.join("output", "requirements.txt")

        if target_file:
            try:
                # Prioritize 'code' field if in Pydantic, otherwise use raw
                if task_output.pydantic and hasattr(task_output.pydantic, 'code'):
                    content = task_output.pydantic.code
                else:
                    content = str(task_output.raw)
                
                if current_task_type == "requirements_task":
                    # Force modern Gradio if agent uses an old version or omits it
                    if "gradio" not in content.lower() or "gradio==" in content.lower() or "gradio<" in content.lower():
                        # Strip any existing gradio line and add the modern one
                        content = "\n".join([l for l in content.split("\n") if "gradio" not in l.lower()])
                        content += "\ngradio>=5.0.0"
                    if "requests" not in content.lower(): content += "\nrequests"
                    
                    # Remove standard libraries that AI often incorrectly includes
                    std_libs = ["math", "os", "sys", "json", "datetime", "random", "re", "time", "unittest", "logging"]
                    content = "\n".join([l for l in content.split("\n") if l.strip().lower() not in std_libs])
                
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(content)
                
                if target_file.endswith('.py'):
                    # Fix common AI deprecation mistakes
                    content = content.replace("readonly=True", "interactive=False")
                    content = content.replace("readonly = True", "interactive=False")
                    
                    strip_markdown_from_python(target_file)
                    # Brute-force: Remove any Gradio leakage from backend modules
                    if current_task_type == "code_task":
                        with open(target_file, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        clean_lines = [l for l in lines if not any(bad in l.lower() for bad in ["import gradio", "from gradio", "gr.", ".launch("])]
                        with open(target_file, 'w', encoding='utf-8') as f:
                            f.writelines(clean_lines)
                
                msg = f"[{timestamp}] 💾 File Saved: {os.path.basename(target_file)}"
                if current_task_type == "documentation_task":
                    msg += "\nFinishedSuccessfully"
            except Exception as e:
                msg = f"[{timestamp}] ⚠️ Error saving {os.path.basename(target_file)}: {str(e)}"
        else:
            summary = TASK_LOG_MAP.get(current_task_type, f"Task Completed: {task_output.description[:40]}...")
            msg = f"[{timestamp}] ✅ {summary}"
        
        log_queue.put(msg)
        
    def log_step(step_output):
        timestamp = datetime.now().strftime("%H:%M:%S")
        msg = f"[{timestamp}] ⚙️ Agent thinking..."
        if hasattr(step_output, 'agent'): msg = f"[{timestamp}] 🤖 {step_output.agent} is active..."
        log_queue.put(msg)

    today_str = datetime.now().strftime("%B %d, %Y")
    enriched_requirements = (
        f"CRITICAL: Today is {today_str}.\n"
        "- LOGIC: Never use len(list)+1 for IDs; use a persistent self.next_id counter.\n"
        "- API: Use 'interactive=False' for read-only fields (Gradio 5+).\n"
        "- AESTHETICS: Implement 'Premium' design with custom CSS (Glassmorphism/Gradients).\n"
        "- UX: Use professional terminology (e.g. 'Deploy Task') and provide clear feedback logs.\n"
        "- INDUSTRIAL QUALITY: Well-commented, modular code, and robust error handling.\n\n"
        f"### USER REQUIREMENTS:\n{requirements}"
    )
    
    inputs = {'requirements': enriched_requirements, 'module_name': module_name, 'class_name': class_name}
    current_logs = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Initializing Engineering Team...\n"
    yield ("Team is starting...", "", "", "", "", "", current_logs, gr.update(visible=False))
    
    def run_crew():
        try:
            crew_obj = EngineeringTeam(task_callback=log_task, step_callback=log_step).crew()
            result_container["data"] = crew_obj.kickoff(inputs=inputs)
            result_container["success"] = True
        except Exception as e: result_container["error"] = str(e)
        finally: result_container["done"] = True

    thread = threading.Thread(target=run_crew)
    thread.start()

    while not result_container["done"]:
        try:
            while True:
                new_log = log_queue.get_nowait()
                current_logs += new_log + "\n"
        except queue.Empty: pass
        
        main_status = "Engineering Team is working..."
        if "FinishedSuccessfully" in current_logs: main_status = "Finalizing output..."
        
        yield (main_status, "", "", "", "", "", current_logs, gr.update(visible=False))
        time.sleep(0.5)

    if result_container["success"]:
        current_logs += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Engineering Team finished successfully!\n"
        sanitize_all_outputs('output', module_name)
        def read_file(path): return open(path, 'r', encoding='utf-8').read() if os.path.exists(path) else ""
        zip_path = create_project_zip('output', zip_name_prefix=module_name.split('.')[0])
        yield (
            "✅ All projects generated!",
            read_file(f"output/{module_name}_design.md"),
            read_file(f"output/{module_name}"),
            read_file("output/app.py"),
            read_file(f"output/test_{module_name}"),
            read_file("output/README.md"),
            current_logs,
            gr.update(value=zip_path, visible=True)
        )
    else:
        current_logs += f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {result_container['error']}\n"
        yield ("❌ Error occurred.", "", "", "", "", "", current_logs, gr.update(visible=False))

# Build UI
with gr.Blocks(theme=gr.themes.Base(primary_hue="zinc", neutral_hue="zinc"), css=custom_css, title="Engineering Team | Enterprise") as demo:
    with gr.Row():
        with gr.Column(scale=8, min_width=300):
            gr.Markdown("# ⚡ AI Engineering Team (Enterprise Edition)")
            gr.Markdown("*Full Software Development Automation for the Modern Enterprise.*")
        with gr.Column(scale=2, min_width=100):
            reset_btn = gr.Button("Reset session", variant="secondary")

    with gr.Row():
        with gr.Column(scale=3, min_width=300):
            with gr.Group():
                reqs = gr.TextArea(
                    label="Product Requirements & Specification", 
                    placeholder="Example: A Trading Simulation Platform.\n- Account management: Create, deposit, and withdraw funds.\n- Share trading: Buy/sell shares (e.g. AAPL, TSLA) with a get_share_price(symbol) logic.\n- Portfolio reporting: Calculate total value, profit/loss, and list holdings.\n- Constraints: Prevent negative balances and selling shares users don't own.\n- Modern UI: Gradio 5+ interface with a real-time dashboard view.", 
                    lines=15,
                    value=""
                )
                with gr.Row():
                    mod_name = gr.Textbox(label="Main Module Name", placeholder="e.g. engine.py", value="logic.py")
                    cls_name = gr.Textbox(label="Primary Class Name", placeholder="e.g. ProjectManager", value="System")
                
                run_btn = gr.Button("Execute Engineering Task", variant="primary")
            
            status = gr.Markdown("Ready to engineer.")
            download_btn = gr.File(label="⬇️ Download Output (ZIP)", visible=False)
            
            with gr.Group():
                terminal_log = gr.TextArea(
                    label="Engineering Logs",
                    placeholder="Team activity logs...",
                    lines=12, interactive=False, elem_classes=["terminal-box"]
                )
            
        with gr.Column(scale=7, min_width=300): # Larger scale for output content
            with gr.Tabs():
                with gr.TabItem("📋 Architecture"):
                    design_out = gr.Markdown("Waiting...", elem_classes=["tabitem"])
                with gr.TabItem("🐍 Backend"):
                    code_out = gr.Code(language="python", elem_classes=["tabitem"])
                with gr.TabItem("🖥️ Gradio UI"):
                    app_out = gr.Code(language="python", elem_classes=["tabitem"])
                with gr.TabItem("🧪 Tests"):
                    test_out = gr.Code(language="python", elem_classes=["tabitem"])
                with gr.TabItem("📖 README"):
                    readme_out = gr.Markdown("Waiting...", elem_classes=["tabitem"])

    run_btn.click(
        fn=solve_requirements_streaming,
        inputs=[reqs, mod_name, cls_name],
        outputs=[status, design_out, code_out, app_out, test_out, readme_out, terminal_log, download_btn]
    )
    
    reset_btn.click(fn=None, js="() => { window.location.reload(); }")

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2, max_size=10).launch()
