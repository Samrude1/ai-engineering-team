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

# CSS for the "Enterprise Edition" Slate & Azure Theme
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono&display=swap');

body, .gradio-container {
    background-color: #0F172A !important; /* Slate 900 */
    color: #F8FAFC !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}

.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding-top: 2rem !important;
}

/* Card-style Grouping */
.group-card {
    background: #1E293B !important; /* Slate 800 */
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    padding: 20px !important;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3) !important;
    margin-bottom: 20px !important;
}

/* Typography */
h1 {
    color: #38BDF8 !important; /* Sky 400 */
    font-size: 2.5rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    margin-bottom: 0.5rem !important;
}

p, li, th, td, label {
    color: #E2E8F0 !important;
}

/* Inputs */
input, textarea, select {
    background-color: #0F172A !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
    color: #F8FAFC !important;
    font-size: 0.95rem !important;
    padding: 12px !important;
    transition: all 0.2s ease !important;
}

input:focus, textarea:focus {
    border-color: #38BDF8 !important;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2) !important;
    outline: none !important;
}

/* Action Buttons */
button.primary {
    background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
    border: none !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 12px 24px !important;
    transition: all 0.3s ease !important;
}

button.primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(2, 132, 199, 0.4) !important;
}

button.secondary {
    background: #334155 !important;
    border: 1px solid #475569 !important;
    color: #F8FAFC !important;
    border-radius: 8px !important;
}

button.secondary:hover {
    background: #475569 !important;
}

/* PresetsRow Styling */
.preset-btn {
    font-size: 0.85rem !important;
    padding: 8px 12px !important;
    min-width: 140px !important;
}

/* Terminal Styling */
.terminal-box textarea {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    background-color: #020617 !important;
    border: 1px solid #0EA5E9 !important;
    color: #38BDF8 !important;
    white-space: pre-wrap !important;
    border-radius: 10px !important;
}

/* Tabs Styling */
div.tabs {
    background: transparent !important;
    border: none !important;
}

div.tabs button {
    color: #94A3B8 !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
}

div.tabs button.selected {
    color: #38BDF8 !important;
    border-bottom: 3px solid #38BDF8 !important;
    background: rgba(56, 189, 248, 0.05) !important;
}
"""

def solve_requirements_streaming(requirements, module_name, class_name, request: gr.Request):
    client_ip = request.client.host if request else "unknown"
    if client_ip not in IP_USAGE: IP_USAGE[client_ip] = 0
    if IP_USAGE[client_ip] >= MAX_REQUESTS_PER_IP:
        yield ("⚠️ Rate limit reached.", "", "", "", "", "", "System Error: Rate limit reached.", gr.update(visible=False))
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
        
        if "engineering blueprint" in description: current_task_type = "design_task"
        elif "write a python module" in description:
            current_task_type = "code_task"
            target_file = os.path.join("output", module_name)
        elif "write a gradio ui" in description:
            current_task_type = "frontend_task"
            target_file = os.path.join("output", "app.py")
        elif "write unit tests" in description:
            current_task_type = "test_task"
            target_file = os.path.join("output", f"test_{module_name}")
        elif "readme.md" in description: current_task_type = "documentation_task"

        if target_file and task_output.pydantic:
            try:
                code = task_output.pydantic.code
                with open(target_file, "w", encoding="utf-8") as f: f.write(code)
                strip_markdown_from_python(target_file)
                msg = f"[{timestamp}] 💾 File Saved: {os.path.basename(target_file)}"
            except Exception as e: msg = f"[{timestamp}] ⚠️ Error: {str(e)}"
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
    current_logs = f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Initializing Enterprise Engineering Team...\n"
    yield ("🚀 Team is starting... (Approx 3-8 mins)", "", "", "", "", "", current_logs, gr.update(visible=False))
    
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
        yield ("🚀 Rocket Engineering Team is working...", "", "", "", "", "", current_logs, gr.update(visible=False))
        time.sleep(1)

    if result_container["success"]:
        current_logs += f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Engineering Team finished successfully!\n"
        sanitize_all_outputs('output', module_name)
        def read_file(path): return open(path, 'r', encoding='utf-8').read() if os.path.exists(path) else ""
        zip_path = create_project_zip('output', zip_name_prefix=module_name.split('.')[0])
        yield (
            "✅ Project Generated! Download below.",
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

def set_preset(choice):
    presets = {
        "🏦 Banking System": ("A secure personal banking system with accounts, transfers, and transaction history. Needs to handle negative balances and basic fraud checks.", "banking.py", "Bank"),
        "🌦️ Weather Dashboard": ("A weather dashboard that integrates with a mock API. Users can search for cities and see a 5-day forecast. Use Gradio for the UI.", "weather_app.py", "WeatherSystem"),
        "📈 Trading Platform": ("A high-frequency trading simulation platform. Handle limit orders, market orders, and portfolio rebalancing.", "investment.py", "PortfolioManager")
    }
    return presets[choice]

# Build UI
with gr.Blocks(theme=gr.themes.Base(primary_hue="sky", neutral_hue="slate"), css=custom_css, title="Engineering Team | Enterprise") as demo:
    with gr.Row():
        with gr.Column(scale=9):
            gr.Markdown("# ⚡ AI Engineering Team (Enterprise Edition)")
            gr.Markdown("*Full Software Development Automation for the Modern Enterprise.*")
        with gr.Column(scale=1):
            reset_btn = gr.Button("🔄 Reset", variant="secondary")

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Group(elem_classes=["group-card"]):
                gr.Markdown("### 🏢 Project Gallery")
                preset_options = ["🏦 Banking System", "🌦️ Weather Dashboard", "📈 Trading Platform"]
                preset_radio = gr.Radio(preset_options, label="Select a scenario to pre-fill", value=None)
                
                gr.Markdown("---")
                reqs = gr.TextArea(label="Requirements", placeholder="Describe your software...", lines=8)
                with gr.Row():
                    mod_name = gr.Textbox(label="Module Name", placeholder="e.g. core.py")
                    cls_name = gr.Textbox(label="Class Name", placeholder="e.g. MyManager")
                
                run_btn = gr.Button("🚀 KICKOFF TEAM", variant="primary")
            
            status = gr.Markdown("Ready to engineer.")
            download_btn = gr.File(label="⬇️ Download Output (ZIP)", visible=False)
            
            with gr.Group(elem_classes=["group-card"]):
                terminal_log = gr.TextArea(
                    label="💠 Mission Control Terminal",
                    placeholder="Team activity logs...",
                    lines=12, interactive=False, elem_classes=["terminal-box"]
                )
            
        with gr.Column(scale=2):
            with gr.Tabs():
                with gr.TabItem("📋 Architecture"):
                    design_out = gr.Markdown("Awaits blueprinting...")
                with gr.TabItem("🐍 Backend"):
                    code_out = gr.Code(language="python")
                with gr.TabItem("🖥️ Gradio UI"):
                    app_out = gr.Code(language="python")
                with gr.TabItem("🧪 Tests"):
                    test_out = gr.Code(language="python")
                with gr.TabItem("📖 README"):
                    readme_out = gr.Markdown("Awaits generation...")

    preset_radio.change(set_preset, inputs=[preset_radio], outputs=[reqs, mod_name, cls_name])
    
    run_btn.click(
        fn=solve_requirements_streaming,
        inputs=[reqs, mod_name, cls_name],
        outputs=[status, design_out, code_out, app_out, test_out, readme_out, terminal_log, download_btn]
    )
    
    reset_btn.click(fn=None, js="() => { window.location.reload(); }")

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=2, max_size=10).launch()
