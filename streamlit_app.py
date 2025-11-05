import asyncio
import streamlit as st
from pathlib import Path
import json
from datetime import datetime
from PIL import Image
import sys
import os
import platform
import numpy as np

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).parent))
from app import run_task, ensure_dir

# Page
st.set_page_config(
    page_title="Agent B",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 1rem; }
    .status-box { padding: 1rem; border-radius: 0.5rem; margin: 1rem 0; }
    .success-box { background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
    .error-box { background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
    .info-box { background-color: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; }
    .image-caption { text-align: center; font-size: 0.9rem; color: #666; margin-top: 0.5rem; }
    .metric-card { background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; border: 1px solid #dee2e6; }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def get_all_task_runs(dataset_root: Path = Path("dataset")):
    if not dataset_root.exists():
        return []
    runs = []
    for task_dir in dataset_root.iterdir():
        if task_dir.is_dir():
            for run_dir in task_dir.iterdir():
                if run_dir.is_dir() and (run_dir / "summary.json").exists():
                    runs.append((task_dir.name, run_dir.name, run_dir))
    runs.sort(key=lambda x: x[1], reverse=True)
    return runs

def load_run_summary(run_dir: Path):
    summary_file = run_dir / "summary.json"
    if summary_file.exists():
        try:
            return json.loads(summary_file.read_text(encoding="utf-8"))
        except Exception as e:
            st.error(f"Failed to load summary: {e}")
    return None


# Helper to display step with frame
def display_step(st, sd, frame_path, display_step_num, timestamp):
    if not frame_path:
        return  # Skip steps with no screenshot

    action_type = sd.get("action_type", "Action")
    thought = sd.get("thought", "")
    url = sd.get("url", "")
    action_details = sd.get("action_details", "")
    action_description = sd.get("action_description", "")
    title = sd.get("title", "")
    extracted_content = sd.get("extracted_content", "")
    error = sd.get("error", "")
    
    with st.expander(f"Step {display_step_num}: {action_type}", expanded=(display_step_num <= 3)):
        col1, col2 = st.columns([2, 3])
        with col1:
            try:
                img = Image.open(frame_path)
                st.image(img, use_container_width=True)
            except:
                st.error("Could not load screenshot")
        with col2:
            if action_description and action_description != action_type:
                st.markdown(f"**Details:** {action_description}")
            if url and url != "None":
                st.markdown(f"**URL:** `{url}`")
            if title and title != "None":
                st.markdown(f"**Page:** {title}")
#            if extracted_content and extracted_content != "None":
#                st.markdown(f"**Extracted Data:**")
#                st.text_area("", extracted_content, height=80, key=f"extracted_{display_step_num}_{timestamp}", disabled=True)
            if error and error != "None":
                st.error(f"Error: {error}")
            if thought and thought.strip() and thought != "None":
                with st.expander("Agent Reasoning"):
                    st.text_area("", thought, height=150, key=f"thought_{display_step_num}_{timestamp}", disabled=True)
            if action_details and action_details != "No action" and action_details != "None":
                with st.expander("Technical Details"):
                    st.code(action_details, language="json")
        st.markdown("---")


# Main Application
def main():
    st.markdown('<div class="main-header"> Agent B </div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        from dotenv import load_dotenv
        load_dotenv()
        email = os.getenv("GMAIL_USER")
        password = os.getenv("GMAIL_PASS")
        
        st.header("Example Tasks")
        example_tasks = [
            "Search for 'Python tutorials' on Google",
            "Go to Amazon and search for 'laptop'",
            "Open YouTube and search for 'AI tutorials'",
            "Visit Wikipedia and search for 'Machine Learning'",
        ]
        selected_example = st.selectbox("Select an example:", [""] + example_tasks, index=0)
        if st.button("Use Example") and selected_example:
            st.session_state.task_input = selected_example
            st.rerun()
        
        st.markdown("---")
        
    
    tab1, tab2 = st.tabs(["Run Task", "Task History"])
    
    # Run Task
    with tab1:
        st.header("Watch your tasks come alive!")
        task_input = st.text_area(
            "Enter your task:",
            value=st.session_state.get('task_input', ''),
            height=100,
            placeholder="Example: Go to Google and search for 'Softlight'"
        )
        col1, col2 = st.columns([1, 4])
        with col1:
            run_button = st.button("Run Task", type="primary", use_container_width=True)
        with col2:
            if run_button and not task_input.strip():
                st.warning("Please enter a task first!")
        
        if run_button and task_input.strip():
            st.markdown('<div class="status-box info-box"> Task execution in progress...</div>', unsafe_allow_html=True)
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                progress_bar.progress(10)
                status_text.text("Initializing browser agent")
                progress_bar.progress(30)
                status_text.text("Agent executing task")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(run_task(task_input))
                finally:
                    loop.close()
                
                progress_bar.progress(100)
                status_text.text("Task completed!")
                st.markdown('<div class="status-box success-box">Task completed successfully!</div>', unsafe_allow_html=True)
            except Exception as e:
                progress_bar.progress(100)
                status_text.text("Task failed")
                st.markdown(f'<div class="status-box error-box">Error: {str(e)}</div>', unsafe_allow_html=True)
    
    # Task History
    with tab2:
        st.header("Task Execution History")
        runs = get_all_task_runs()
        
        if not runs:
            st.info("No task runs found. Execute a task in the 'Run Task' tab to see results here.")
        else:
            st.success(f"Found {len(runs)} task run(s)")
            
            for idx, (task_slug, timestamp, run_dir) in enumerate(runs):
                with st.expander(f"{task_slug} - {timestamp}", expanded=(idx == 0)):
                    summary = load_run_summary(run_dir)
                    if not summary:
                        st.error("Failed to load summary data")
                        continue
                    
                    # Load steps and frames safely
                    steps_file = run_dir / "steps_details.json"
                    steps_data = []
                    if steps_file.exists():
                        try:
                            steps_data = json.loads(steps_file.read_text(encoding="utf-8"))
                        except Exception as e:
                            st.warning(f"Could not load steps: {e}")
                    
                    frames_dir = run_dir / "frames"
                    frame_list = sorted([p for p in frames_dir.glob("*.png")]) if frames_dir.exists() else []

                    # Display only steps with corresponding screenshots
                    filtered_steps = []
                    filtered_frames = []
                    for i, frame_path in enumerate(frame_list):
                        if i < len(steps_data):
                            filtered_steps.append(steps_data[i])
                            filtered_frames.append(frame_path)
                    filtered_pair_count = len(filtered_frames)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Status", "Success" if summary.get("success") else "Failed")
                    with col2:
                        st.metric("Steps", filtered_pair_count)
                    
                    st.markdown("**Task:**")
                    st.text(summary.get("task", "N/A"))
                    
                    errors = [e for e in summary.get("errors", []) if e]
                    if errors:
                        st.markdown("**Errors:**")
                        for error in errors:
                            st.error(error)
                    
                    st.markdown("---")
                    st.markdown("### Step-by-Step Execution")
                    
                    for i in range(filtered_pair_count):
                        display_step(st, filtered_steps[i], filtered_frames[i], i+1, timestamp)


# Main
if __name__ == "__main__":
    if 'task_input' not in st.session_state:
        st.session_state.task_input = ""
    main()
