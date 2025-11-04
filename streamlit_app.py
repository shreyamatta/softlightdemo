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
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
    .image-caption {
        text-align: center;
        font-size: 0.9rem;
        color: #666;
        margin-top: 0.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions

def get_all_task_runs(dataset_root: Path = Path("dataset")):
    """
    Retrieve all task runs from the dataset directory.
    
    Returns:
        List of tuples: (task_slug, timestamp, run_dir_path)
    """
    if not dataset_root.exists():
        return []
    
    runs = []
    for task_dir in dataset_root.iterdir():
        if task_dir.is_dir():
            for run_dir in task_dir.iterdir():
                if run_dir.is_dir() and (run_dir / "summary.json").exists():
                    runs.append((task_dir.name, run_dir.name, run_dir))
    
    # Sort by timestamp
    runs.sort(key=lambda x: x[1], reverse=True)
    return runs


def load_run_summary(run_dir: Path):
    """
    Load summary.json from a run directory.
    
    Args:
        run_dir: Path to the run directory
        
    Returns:
        dict: Summary data or None if not found
    """
    summary_file = run_dir / "summary.json"
    if summary_file.exists():
        try:
            return json.loads(summary_file.read_text(encoding="utf-8"))
        except Exception as e:
            st.error(f"Failed to load summary: {e}")
    return None


# Main Application
def main():
    
    # Header
    st.markdown('<div class="main-header"> Agent B </div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        from dotenv import load_dotenv
        load_dotenv()
        
        email = os.getenv("GMAIL_USER")
        password = os.getenv("GMAIL_PASS")
        
        # Example tasks
        st.header("Example Tasks")
        
        if email and password:
            example_tasks = [
                "Search for 'Python tutorials' on Google",
                "Go to Amazon and search for 'laptop'",
                "Open YouTube and search for 'AI tutorials'",
                "Go to Wikipedia and search for 'Machine Learning'",
            ]
        else:
            example_tasks = [
                "Search for 'Python tutorials' on Google",
                "Go to Amazon and search for 'laptop'",
                "Open YouTube and search for 'AI tutorials'",
                "Visit Wikipedia and search for 'Machine Learning'",
            ]
        
        selected_example = st.selectbox(
            "Select an example:",
            [""] + example_tasks,
            index=0
        )
        
        if st.button("Use Example"):
            if selected_example:
                st.session_state.task_input = selected_example
                st.rerun()
        
        st.markdown("---")
        
        # Settings
        st.header("Settings")
        max_steps = st.slider("Max Steps", min_value=5, max_value=50, value=30)
    
    # Create tabs
    tab1, tab2 = st.tabs(["Run Task", "Task History"])
    
    # Run
    with tab1:
        st.header("Watch your tasks come alive!")
        
        # Task input
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
        
        # Execute task
        if run_button and task_input.strip():
            st.markdown('<div class="status-box info-box">⏳ Task execution in progress...</div>',
                       unsafe_allow_html=True)
            
            # Progress indicators
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Update progress
                progress_bar.progress(10)
                status_text.text("Initializing browser agent...")
                
                # Run the task
                progress_bar.progress(30)
                status_text.text("Agent executing task...")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(run_task(task_input))
                finally:
                    loop.close()
                
                progress_bar.progress(100)
                status_text.text("Task completed!")
                
                st.markdown('<div class="status-box success-box">Task completed successfully!</div>',
                           unsafe_allow_html=True)
                st.success("Results are now available in the 'Task History' tab.")
                
                # Auto-switch to history tab on next rerun
                st.balloons()
                
            except NotImplementedError as e:
                progress_bar.progress(100)
                status_text.text("Windows Subprocess Error")
                st.markdown(
                    '<div class="status-box error-box">Windows Asyncio Error: Browser subprocess failed to start</div>',
                    unsafe_allow_html=True
                )
                st.error(
                    "**Troubleshooting Steps:**\n"
                    "1. Close Streamlit and restart: `Ctrl+C` then `streamlit run streamlit_app.py`\n"
                    "2. Try using the command line version instead: `python app.py`\n"
                    "3. Ensure Chrome/Chromium is installed\n"
                    "4. Check if Windows Defender/Antivirus is blocking browser launch"
                )
                with st.expander("Technical Details"):
                    st.code(f"{type(e).__name__}: {str(e)}", language="python")
                    
            except Exception as e:
                progress_bar.progress(100)
                status_text.text("Task failed")
                error_msg = str(e) if str(e) else "Unknown error occurred"
                st.markdown(
                    f'<div class="status-box error-box">Error: {error_msg}</div>',
                    unsafe_allow_html=True
                )
                st.error(f"**Error Type:** {type(e).__name__}")
                
                # Show helpful troubleshooting
                with st.expander("🔍 Troubleshooting Tips"):
                    st.markdown("""
                    **Common Issues:**
                    - **Missing API Key**: Check your `.env` file has `OPENAI_API_KEY`
                    - **Browser Launch Failed**: Ensure Chrome/Chromium is installed
                    - **Timeout**: Task may be too complex, try simpler tasks first
                    - **Network Issues**: Check your internet connection
                    
                    **Try:**
                    1. Refresh the page and try again
                    2. Use a simpler task like "Go to example.com"
                    3. Check the terminal/console for detailed error logs
                    4. Try the CLI version: `python app.py "your task"`
                    """)
                    st.code(f"Full error: {type(e).__name__}: {error_msg}", language="python")
    
    with tab2:
        st.header("Task Execution History")
        
        # Load all task runs
        runs = get_all_task_runs()
        
        if not runs:
            st.info("No task runs found. Execute a task in the 'Run Task' tab to see results here.")
        else:
            st.success(f"Found {len(runs)} task run(s)")
            
            # Display runs
            for idx, (task_slug, timestamp, run_dir) in enumerate(runs):
                with st.expander(f"{task_slug} - {timestamp}", expanded=(idx == 0)):
                    # Load summary
                    summary = load_run_summary(run_dir)
                    
                    # Initialize filtered_steps
                    filtered_steps = []

                    if summary:
                        # Display summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("Status", "Success" if summary.get("success") else "Failed")
                        with col2:
                            # Show number of filtered steps (safe now)
                            st.metric("Steps", len(filtered_steps))
                        
                        # Display task details
                        st.markdown("**Task:**")
                        st.text(summary.get("task", "N/A"))
                        
                        # Display errors if any (filter out None values)
                        errors = [e for e in summary.get("errors", []) if e is not None and str(e).strip() and str(e).lower() != 'none']
                        if errors:
                            st.markdown("**Errors:**")
                            for error in errors:
                                st.error(error)
                        
                        st.markdown("---")
                        
                        # Display execution with screenshots and actions
                        st.markdown("### Step-by-Step Execution")
                        
                        # Load detailed steps information
                        steps_file = run_dir / "steps_details.json"
                        steps_with_actions = []
                        
                        if steps_file.exists():
                            try:
                                steps_with_actions = json.loads(steps_file.read_text(encoding="utf-8"))
                            except Exception as e:
                                st.warning(f"Could not load detailed steps: {e}")
                        
                        # If steps_details.json doesn't exist, try to get from summary
                        if not steps_with_actions and "steps_with_actions" in summary:
                            steps_with_actions = summary["steps_with_actions"]
                        
                        # Get all frame images
                        frames_dir = run_dir / "frames"
                        all_frames = {}
                        if frames_dir.exists():
                            for frame_path in sorted(frames_dir.glob("*.png")):
                                all_frames[frame_path.name] = frame_path
                        
                        # Filter and renumber steps
                        if steps_with_actions:
                            filtered_steps = []
                            for step_data in steps_with_actions:
                                step_num = step_data.get("step_number", 0)
                                
                                # Skip step 1 (initial state)
                                if step_num == 1:
                                    continue
                                
                                # Skip steps with "Waited" messages or wait actions
                                extracted_content = step_data.get("extracted_content", "")
                                action_description = step_data.get("action_description", "")
                                action_details = step_data.get("action_details", "")
                                
                                if (("waited" in str(extracted_content).lower()) or
                                    ("waited" in str(action_description).lower()) or
                                    ("wait" in step_data.get("action_type", "").lower() and "wait" in str(action_details).lower())):
                                    continue
                                
                                filtered_steps.append(step_data)
                            
                            # Renumber filtered steps for display
                            for display_index, sd in enumerate(filtered_steps, start=1):
                                sd["display_step_number"] = display_index
                            
                            displayed_count = len(filtered_steps)
                            st.info(f"Steps: {displayed_count}")
                            
                            # Display filtered steps with screenshots and details
                            if filtered_steps and all_frames:
                                for sd in filtered_steps:
                                    original_step_num = sd.get("step_number", 0)
                                    display_step_num = sd.get("display_step_number", original_step_num)
                                    action_type = sd.get("action_type", "Unknown action")
                                    thought = sd.get("thought", "")
                                    url = sd.get("url", "")
                                    action_details = sd.get("action_details", "")
                                    screenshot_name = sd.get("screenshot", "")
                                    action_description = sd.get("action_description", "")
                                    
                                    # Create expandable section 
                                    with st.expander(f"Step {display_step_num}: {action_type}", expanded=(display_step_num <= 3)):
                                        col1, col2 = st.columns([2, 3])
                                        
                                        with col1:
                                            # Display screenshot
                                            if screenshot_name in all_frames:
                                                screenshot_path = all_frames[screenshot_name]
                                                try:
                                                    img = Image.open(screenshot_path)
                                                    
                                                    # Check if image is mostly blank/white
                                                    img_array = np.array(img.convert('L'))
                                                    mean_brightness = img_array.mean()
                                                    
                                                    # Display image
                                                    st.image(img, use_container_width=True)
                                                    
                                                    if mean_brightness > 250:
                                                        st.caption("Blank/Loading Screen")
                                                    elif mean_brightness < 10:
                                                        st.caption("Black/Transitional Screen")
                                                    elif url and 'about:blank' in url:
                                                        st.caption("Empty Tab (Initial State)")
                                                        
                                                except Exception as e:
                                                    st.error(f"Could not load screenshot: {e}")
                                            else:
                                                st.warning("Screenshot not available")
                                        
                                        with col2:
                                            # Display action details
                                            st.markdown(f"**Action:** `{action_type}`")
                                            
                                            if action_description and action_description != action_type:
                                                st.markdown(f"**Details:** {action_description}")
                                            
                                            interacted_element = sd.get("interacted_element", "")
                                            if interacted_element and interacted_element != "None":
                                                st.markdown(f"**Clicked Element:** `{interacted_element}`")
                                            
                                            if url and url != "None":
                                                st.markdown(f"**URL:** `{url}`")
                                            
                                            # Show title
                                            title = sd.get("title", "")
                                            if title and title != "None":
                                                st.markdown(f"**Page:** {title}")
                                            
                                            extracted_content = sd.get("extracted_content", "")
                                            if extracted_content and extracted_content != "None":
                                                st.markdown(f"**Extracted Data:**")
                                                st.text_area("", extracted_content, height=80, key=f"extracted_{display_step_num}_{timestamp}", disabled=True)
                                            
                                            error = sd.get("error", "")
                                            if error and error != "None":
                                                st.error(f"Error: {error}")
                                            
                                            # Agent reasoning
                                            if thought and thought.strip() and thought != "None":
                                                with st.expander("Agent Reasoning"):
                                                    st.text_area("", thought, height=150, key=f"thought_{display_step_num}_{timestamp}", disabled=True)
                                            
                                            # Technical details
                                            if action_details and action_details != "No action" and action_details != "None":
                                                with st.expander("Technical Details"):
                                                    st.code(action_details, language="json")
                                        st.markdown("---")
                            else:
                                # If there are filtered steps but no frames available
                                if filtered_steps and not all_frames:
                                    st.warning("Detailed step screenshots not available for this run. Still showing step metadata.")
                                    for sd in filtered_steps:
                                        display_step_num = sd.get("display_step_number", sd.get("step_number", 0))
                                        action_type = sd.get("action_type", "Unknown action")
                                        with st.expander(f"Step {display_step_num}: {action_type}", expanded=(display_step_num <= 3)):
                                            st.write(sd)
                                            st.markdown("---")
                                else:
                                    st.warning("No steps after filtering or no frames available.")
                        
                        # Fallback: no steps info, but frames exist
                        elif all_frames:
                            st.warning("Detailed step information not available. Showing all screenshots:")
                            
                            cols_per_row = 2
                            frame_list = sorted(all_frames.items())
                            for i in range(0, len(frame_list), cols_per_row):
                                cols = st.columns(cols_per_row)
                                for j, col in enumerate(cols):
                                    if i + j < len(frame_list):
                                        frame_name, frame_path = frame_list[i + j]
                                        with col:
                                            img = Image.open(frame_path)
                                            st.image(img, caption=frame_name, use_container_width=True)
                        else:
                            st.error("No screenshots found for this task run")
                    else:
                        st.error("Failed to load summary data")


#Main
if __name__ == "__main__":
    # Initialize session state
    if 'task_input' not in st.session_state:
        st.session_state.task_input = ""
    
    # Run main application
    main()
