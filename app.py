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

body, .gradio-container {
    font-family: 'Inter', -apple-system, sans-serif !important;
    background-color: #fdfdfd !important;
    color: #1a1a1a !important;
}

.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding-left: 10px !important;
    padding-right: 10px !important;
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

/* Inputs */
input, textarea {
    background-color: #ffffff !important;
    border: 1px solid #d4d4d4 !important;
    border-radius: 6px !important;
    color: #111111 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important;
    padding: 10px !important;
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
    
    def log_task(task_output):
        timestamp = datetime.now().strftime("%H:%M:%S")
        description = task_output.description.lower()
        target_file = None
        current_task_type = None
        
        # Robust Multi-Keyword Task Identification
        if any(kw in description for kw in ["blueprint", "architecture", "design task"]):
            current_task_type = "design_task"
            target_file = os.path.join("output", f"{module_name}_design.md")
        elif any(kw in description for kw in ["business logic", "logic only", "python module"]):
            if "gradio ui" not in description: # Ensure we don't pick frontend task incorrectly
                current_task_type = "code_task"
                target_file = os.path.join("output", module_name)
        
        if "gradio ui" in description:
            current_task_type = "frontend_task"
            target_file = os.path.join("output", "app.py")
        elif "unit tests" in description or "test task" in description:
            current_task_type = "test_task"
            target_file = os.path.join("output", f"test_{module_name}")
        elif any(kw in description for kw in ["readme.md", "professional readme", "documentation task"]):
            current_task_type = "documentation_task"
            target_file = os.path.join("output", "README.md")

        if target_file:
            try:
                # Prioritize 'code' field if in Pydantic, otherwise use raw
                if task_output.pydantic and hasattr(task_output.pydantic, 'code'):
                    content = task_output.pydantic.code
                else:
                    content = str(task_output.raw)
                
                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(content)
                
                if target_file.endswith('.py'):
                    strip_markdown_from_python(target_file)
                
                msg = f"[{timestamp}] 💾 File Saved: {os.path.basename(target_file)}"
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

    inputs = {'requirements': requirements, 'module_name': module_name, 'class_name': class_name}
    current_logs = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Initializing Engineering Team...\n"
    yield ("Team is starting...", "", "", "", "", "", current_logs, gr.update(visible=False))
    
    result_container = {"success": False, "data": None, "error": None, "done": False}
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

def set_banking(): return "A secure personal banking system with accounts, transfers, and transaction history. Needs to handle negative balances and basic fraud checks.", "banking.py", "Bank"
def set_weather(): return "A weather dashboard that integrates with a mock API. Users can search for cities and see a 5-day forecast. Use Gradio for the UI.", "weather_app.py", "WeatherSystem"
def set_trading(): return "A high-frequency trading simulation platform. Handle limit orders, market orders, and portfolio rebalancing.", "investment.py", "PortfolioManager"

# Build UI
with gr.Blocks(theme=gr.themes.Base(primary_hue="zinc", neutral_hue="zinc"), css=custom_css, title="Engineering Team | Enterprise") as demo:
    with gr.Row():
        with gr.Column(scale=8):
            gr.Markdown("# ⚡ AI Engineering Team (Enterprise Edition)")
            gr.Markdown("*Full Software Development Automation for the Modern Enterprise.*")
        with gr.Column(scale=2, min_width=100):
            reset_btn = gr.Button("Reset session", variant="secondary")

    with gr.Row():
        with gr.Column(scale=3, min_width=300): # Fixed width for inputs to ensure right column gets space
            with gr.Group():
                gr.Markdown("<p style='font-size: 0.9em; color: #666; margin-bottom: 5px; padding-left: 5px;'><i>Quick Scenarios</i></p>")
                with gr.Row():
                    btn_bank = gr.Button("🏦 Banking", variant="secondary")
                    btn_weather = gr.Button("🌦️ Weather", variant="secondary")
                    btn_trading = gr.Button("📈 Trading", variant="secondary")
                
                reqs = gr.TextArea(
                    label="Requirements", 
                    placeholder="Describe your software...", 
                    lines=8,
                    value="A high-frequency trading simulation platform. Handle limit orders, market orders, and portfolio rebalancing."
                )
                with gr.Row():
                    mod_name = gr.Textbox(label="Module Name", placeholder="e.g. core.py", value="investment.py")
                    cls_name = gr.Textbox(label="Class Name", placeholder="e.g. MyManager", value="PortfolioManager")
                
                run_btn = gr.Button("Execute Engineering Task", variant="primary")
            
            status = gr.Markdown("Ready to engineer.")
            download_btn = gr.File(label="⬇️ Download Output (ZIP)", visible=False)
            
            with gr.Group():
                terminal_log = gr.TextArea(
                    label="Engineering Logs",
                    placeholder="Team activity logs...",
                    lines=12, interactive=False, elem_classes=["terminal-box"]
                )
            
        with gr.Column(scale=7): # Larger scale for output content
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

    # Wire buttons
    btn_bank.click(set_banking, [], [reqs, mod_name, cls_name])
    btn_weather.click(set_weather, [], [reqs, mod_name, cls_name])
    btn_trading.click(set_trading, [], [reqs, mod_name, cls_name])
    
    run_btn.click(
        fn=solve_requirements_streaming,
        inputs=[reqs, mod_name, cls_name],
        outputs=[status, design_out, code_out, app_out, test_out, readme_out, terminal_log, download_btn]
    )
    
    reset_btn.click(fn=None, js="() => { window.location.reload(); }")

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2, max_size=10).launch()
