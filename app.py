import asyncio
import base64
import json
import time
import re
import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional
from PIL import Image, ImageSequence  # 🆕 for GIF extraction

from dotenv import load_dotenv
from browser_use import Agent, Browser, ChatBrowserUse
from openai import OpenAI

load_dotenv()

EMAIL = os.getenv("GMAIL_USER")
APP_PASSWORD = os.getenv("GMAIL_PASS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---------------- util ----------------
def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "task"

def now_ts() -> str:
    return time.strftime("%Y-%m-%d-%H%M%S")

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def normalize_text(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t[:20000]

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

# ---------------- CDP helpers ----------------
async def cdp(agent: Agent):
    s = await agent.browser_session.get_or_create_cdp_session()
    return s.cdp_client, s.session_id

async def cdp_eval(agent: Agent, expression: str) -> Any:
    client, sid = await cdp(agent)
    await client.send.Runtime.enable(session_id=sid)
    res = await client.send.Runtime.evaluate(
        params={"expression": expression, "returnByValue": True},
        session_id=sid,
    )
    return (res.get("result") or {}).get("value")

async def set_viewport(agent: Agent, width: int = 1366, height: int = 768, scale: float = 1.0):
    client, sid = await cdp(agent)
    await client.send.Emulation.setDeviceMetricsOverride(
        params={
            "width": width,
            "height": height,
            "deviceScaleFactor": scale,
            "mobile": False,
            "screenWidth": width,
            "screenHeight": height,
        },
        session_id=sid,
    )

# ---------------- GPT filter ----------------
client = OpenAI(api_key=OPENAI_API_KEY)

def encode_img_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def sanitize_task_text(t: str) -> str:
    banned = ["password", "passcode", "email", "username", "login", "signin"]
    for b in banned:
        t = t.replace(b, "[REDACTED]")
    return t

def gpt_filter_screenshots(task, screenshot_paths):
    """
    Filter screenshots using GPT-4 Vision to remove duplicates and blank frames.
    
    Args:
        task: The task description
        screenshot_paths: List of paths to screenshot files
    
    Returns:
        dict: {'keep': [...], 'skip': [...]} with filtered frame paths
    """
    # Handle empty input
    if not screenshot_paths:
        print("⚠️ No screenshots to filter")
        return {"keep": [], "skip": []}
    
    # Limit to 15 images max to avoid API limits
    MAX_IMAGES = 15
    if len(screenshot_paths) > MAX_IMAGES:
        print(f"⚠️ Too many frames ({len(screenshot_paths)}). Processing first {MAX_IMAGES} frames.")
        screenshot_paths = screenshot_paths[:MAX_IMAGES]
    
    try:
        imgs_b64 = [encode_img_b64(p) for p in screenshot_paths]
        print(f"🔍 Filtering {len(imgs_b64)} frames using GPT-4 Vision...")
    except Exception as e:
        print(f"❌ Failed to encode images: {e}")
        return {"keep": screenshot_paths, "skip": []}

    # Create prompt with frame names for reference
    frame_names = [Path(p).name for p in screenshot_paths]
    
    messages = [
        {
            "role": "system",
            "content": (
                "You are a visual filtering assistant. "
                "Analyze the provided frames and identify which ones to keep or skip. "
                "Skip frames that are: blank/white screens, loading spinners, duplicates, or transitional states. "
                "Keep frames that show: meaningful content, unique screens, completed page loads, or distinct UI states."
            ),
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"Task context: {sanitize_task_text(task)}\n\n"
                        f"Frame names: {', '.join(frame_names)}\n\n"
                        "Analyze these frames and return ONLY a JSON object with this exact format:\n"
                        '{"keep": ["frame_001.png", "frame_005.png"], "skip": ["frame_002.png", "frame_003.png"]}\n\n'
                        "Rules:\n"
                        "1. Use exact filenames from the list above\n"
                        "2. Return valid JSON only (no markdown, no explanations)\n"
                        "3. Every frame must be in either 'keep' or 'skip'\n"
                        "4. Prefer keeping frames if uncertain"
                    ),
                },
                *[
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                    for b64 in imgs_b64
                ],
            ],
        },
    ]

    try:
        # Call GPT-4 Vision API with JSON mode
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        text = resp.choices[0].message.content.strip()
        print(f"\n🤖 GPT Response ({len(text)} chars):")
        print(text[:500] + ("..." if len(text) > 500 else ""))

        # Check for refusal
        if "unable to assist" in text.lower() or "cannot help" in text.lower():
            raise ValueError("GPT refused to process (safety filter triggered)")

        # Parse JSON response
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            # Try to clean markdown if present
            if text.startswith("```"):
                text = text.strip("` \n")
                text = re.sub(r"^json\s*", "", text, flags=re.IGNORECASE).strip()
                data = json.loads(text)
            else:
                raise

        # Validate response structure
        if not isinstance(data, dict) or "keep" not in data:
            print(f"⚠️ Invalid response structure: {data}")
            return {"keep": screenshot_paths, "skip": []}

        # Map GPT's frame names to real file paths
        real_map = {Path(p).name: p for p in screenshot_paths}
        keep_real, skip_real = [], []
        
        for frame_name in data.get("keep", []):
            normalized_name = Path(frame_name).name
            if normalized_name in real_map:
                keep_real.append(real_map[normalized_name])
            else:
                print(f"⚠️ Unknown frame in 'keep': {frame_name}")
        
        for frame_name in data.get("skip", []):
            normalized_name = Path(frame_name).name
            if normalized_name in real_map:
                skip_real.append(real_map[normalized_name])
            else:
                print(f"⚠️ Unknown frame in 'skip': {frame_name}")

        # Fallback: keep all frames if filtering removed everything
        if not keep_real:
            print("⚠️ No frames kept. Defaulting to keep all frames.")
            keep_real = screenshot_paths
            skip_real = []

        print(f"✅ Filtering complete: {len(keep_real)} kept, {len(skip_real)} skipped")
        
        return {"keep": keep_real, "skip": skip_real}

    except Exception as e:
        print(f"❌ GPT filtering failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {"keep": screenshot_paths, "skip": []}

# ---------------- run ----------------
async def run_task(task: str, dataset_root: Path = Path("dataset")):
    """
    Execute a browser automation task with AI agent.
    
    Args:
        task: Natural language task description
        dataset_root: Root directory to save results
        
    Returns:
        None - Results saved to filesystem
    """
    # Enhance task with detailed instructions for better agent behavior
    enhanced_task = f"""
    TASK: {task}

    INSTRUCTIONS FOR EXECUTION:
    1. READ CAREFULLY: Understand the complete task before starting any actions
    2. BE PRECISE: Follow the exact requirements specified in the task
    3. BE PATIENT: Wait for pages to fully load before interacting with elements
    4. BE THOROUGH: Complete all parts of the task, don't stop halfway
    5. BE SMART: If something doesn't work, try alternative approaches
    6. BE OBSERVANT: Verify that each action achieved its intended result

    BEHAVIORAL GUIDELINES:
    - Always wait for page elements to be fully visible and clickable before interacting
    - If you encounter errors, try at least 2-3 alternative approaches before giving up
    - Read page content carefully to understand context before taking actions
    - Use scroll actions when needed to find elements not immediately visible
    - Verify search results, form submissions, and navigation were successful
    - Extract and report relevant information when completing the task

    ERROR HANDLING:
    - If an element is not found, scroll the page or wait for it to load
    - If a click doesn't work, try clicking related elements or using keyboard actions
    - If navigation fails, retry with slightly different approaches
    - Document any persistent errors in your final response
    """
    
    # Add login credentials if available
    if EMAIL and APP_PASSWORD:
        enhanced_task += f"""
AUTHENTICATION CREDENTIALS (Use ONLY if login is required):
- Email/Username: {EMAIL}
- Password: {APP_PASSWORD}
- Login automatically when you encounter login pages or forms
- Complete the full authentication flow including any 2FA or verification steps

OTP/2FA HANDLING (For OTP-based login):
- If the website requires OTP/verification code after entering credentials:
  1. Open a new tab and navigate to https://mail.google.com
  2. Login to Gmail using the same credentials: {EMAIL} / {APP_PASSWORD}
  3. Check the inbox for the most recent email with OTP/verification code
  4. Extract the OTP code from the email (look for 6-digit codes or verification links)
  5. Switch back to the original tab
  6. Enter the extracted OTP code in the verification field
  7. Complete the login process
- Be patient and wait for emails to arrive (check inbox multiple times if needed)
- Look for emails from the service you're trying to login to
"""
    else:
        enhanced_task += """
NOTE: No login credentials available. Skip any tasks requiring authentication.
"""
    
    task_slug = slugify(task)
    run_dir = dataset_root / task_slug / now_ts()
    ensure_dir(run_dir)

    # Configure browser for better reliability
    browser = Browser(
        use_cloud=False,
        headless=False,  # Run in visible mode for better debugging
    )
    
    # Configure LLM for better instruction following
    llm = ChatBrowserUse()

    # Create agent with enhanced configuration
    agent = Agent(
        task=enhanced_task,  # Use enhanced task with detailed instructions
        llm=llm,
        browser=browser,
        use_vision=True,  # Enable visual understanding
        vision_detail_level="high",  # High detail for better element detection
        generate_gif=str(run_dir / "run.gif"),
        max_failures=5,  # Allow more retries for resilience
        retry_delay=2,  # Wait 2 seconds between retries
        step_timeout=180,  # 3 minutes per step
    )
    
    print(f"🤖 Agent configured with enhanced instructions for better task execution")

    # --- Run the agent ---
    await asyncio.sleep(0.2)
    try:
        await set_viewport(agent, width=1366, height=768)
    except Exception:
        pass

    history = await agent.run(max_steps=30)

    # --- Extract GIF frames as screenshots ---
    gif_path = run_dir / "run.gif"
    frames_dir = run_dir / "frames"
    ensure_dir(frames_dir)

    if gif_path.exists():
        print(f"🎞️ Extracting frames from GIF: {gif_path}")
        gif = Image.open(gif_path)
        for i, frame in enumerate(ImageSequence.Iterator(gif)):
            frame = frame.convert("RGB")
            frame_path = frames_dir / f"frame_{i:03d}.png"
            frame.save(frame_path)
        print(f"✅ Extracted {i+1} frames to {frames_dir}")

    # --- Process step-by-step history with action labels ---
    steps_data = []
    
    # Extract detailed step information from history using browser-use API
    print(f"📋 Processing {history.number_of_steps()} steps...")
    
    # Access history items (it's a property/list, not a method)
    history_items = history.history if isinstance(history.history, list) else []
    
    for step_idx, history_item in enumerate(history_items):
        step_info = {
            "step_number": step_idx + 1,
            "action_type": "Unknown",
            "thought": "",
            "url": "",
            "action_details": "",
            "screenshot": f"frame_{step_idx:03d}.png",
            "interacted_element": "",
            "action_description": ""
        }
        
        try:
            # Extract browser state (URL, title, screenshot path)
            if hasattr(history_item, 'state') and history_item.state:
                state = history_item.state
                step_info['url'] = getattr(state, 'url', '')
                step_info['title'] = getattr(state, 'title', '')
                
                # Get interacted element
                if hasattr(state, 'interacted_element') and state.interacted_element:
                    interacted = state.interacted_element[0] if isinstance(state.interacted_element, list) else state.interacted_element
                    if interacted:
                        step_info['interacted_element'] = str(interacted)
            
            # Extract model output (actions and reasoning)
            if hasattr(history_item, 'model_output') and history_item.model_output:
                model_output = history_item.model_output
                
                # Extract current state (evaluation, memory, goals)
                if hasattr(model_output, 'current_state') and model_output.current_state:
                    current_state = model_output.current_state
                    
                    # Get evaluation and next goal
                    evaluation = getattr(current_state, 'evaluation_previous_goal', '')
                    memory = getattr(current_state, 'memory', '')
                    next_goal = getattr(current_state, 'next_goal', '')
                    
                    # Combine into thought
                    thought_parts = []
                    if evaluation:
                        thought_parts.append(f"Evaluation: {evaluation}")
                    if memory:
                        thought_parts.append(f"Memory: {memory}")
                    if next_goal:
                        thought_parts.append(f"Next Goal: {next_goal}")
                    
                    step_info['thought'] = "\n\n".join(thought_parts)
                
                # Extract actions
                if hasattr(model_output, 'action') and model_output.action:
                    actions = model_output.action
                    
                    # Get first action (primary action for this step)
                    if actions and len(actions) > 0:
                        first_action = actions[0]
                        
                        # Get action name - extract from class name or action dict
                        action_class_name = first_action.__class__.__name__ if hasattr(first_action, '__class__') else 'Unknown'
                        
                        # Get action details as dict
                        if hasattr(first_action, 'model_dump'):
                            action_dict = first_action.model_dump(exclude_none=True)
                            step_info['action_details'] = json.dumps(action_dict, indent=2)
                            
                            # Map action class to readable names and extract parameters
                            if 'text' in action_dict:
                                step_info['action_type'] = 'Input Text'
                                step_info['action_description'] = f"Type: '{action_dict.get('text', '')[:100]}'"
                            elif 'url' in action_dict:
                                step_info['action_type'] = 'Navigate'
                                step_info['action_description'] = f"Go to: {action_dict.get('url', '')}"
                            elif 'index' in action_dict:
                                step_info['action_type'] = 'Click Element'
                                step_info['action_description'] = f"Click element #{action_dict.get('index', '')}"
                            elif 'content' in action_dict or 'extract' in action_class_name.lower():
                                step_info['action_type'] = 'Extract Content'
                                content = str(action_dict.get('content', ''))
                                step_info['action_description'] = f"Extract: {content[:100]}..." if len(content) > 100 else content
                            elif 'search' in action_class_name.lower():
                                step_info['action_type'] = 'Search'
                                step_info['action_description'] = f"Search: {action_dict.get('query', '')}"
                            elif 'scroll' in action_class_name.lower():
                                step_info['action_type'] = 'Scroll'
                                step_info['action_description'] = f"Scroll: {action_dict.get('direction', 'down')}"
                            elif 'wait' in action_class_name.lower():
                                step_info['action_type'] = 'Wait'
                                step_info['action_description'] = f"Wait {action_dict.get('seconds', 1)}s"
                            elif 'done' in action_class_name.lower():
                                step_info['action_type'] = 'Task Complete'
                                step_info['action_description'] = 'Task completed successfully'
                            else:
                                # Use class name as fallback
                                step_info['action_type'] = action_class_name.replace('Action', '').replace('Model', '').strip()
                                if not step_info['action_type']:
                                    step_info['action_type'] = 'Browser Action'
                        else:
                            step_info['action_type'] = action_class_name.replace('Action', '').replace('Model', '').strip() or 'Browser Action'
            
            # Extract result information
            if hasattr(history_item, 'result') and history_item.result:
                results = history_item.result
                if results and len(results) > 0:
                    result = results[0]
                    if hasattr(result, 'extracted_content') and result.extracted_content:
                        step_info['extracted_content'] = str(result.extracted_content)[:200]
                    if hasattr(result, 'error') and result.error:
                        step_info['error'] = str(result.error)
                        
        except Exception as e:
            print(f"⚠️ Could not extract full details for step {step_idx + 1}: {e}")
            import traceback
            traceback.print_exc()
        
        steps_data.append(step_info)
        action_display = f"{step_info['action_type']}"
        if step_info.get('action_description'):
            action_display += f" - {step_info['action_description']}"
        print(f"   Step {step_idx + 1}: {action_display}")
    
    # Save detailed steps information
    (run_dir / "steps_details.json").write_text(
        json.dumps(steps_data, indent=2, ensure_ascii=False), 
        encoding="utf-8"
    )
    print(f"✅ Saved {len(steps_data)} step details")

    # --- Save summary (NO GPT filtering) ---
    summary = {
        "task": task,
        "success": bool(history.is_successful()),
        "steps": history.number_of_steps(),
        "urls": history.urls(),
        "errors": history.errors(),
        "gif": str(gif_path),
        "total_frames": len(list(frames_dir.glob("*.png"))),
        "steps_with_actions": steps_data
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n✅ Saved run to: {run_dir.resolve()}\n")

# ------------- entry -------------
if __name__ == "__main__":
    import sys
    
    # Get task from command line or prompt
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = input("Enter your task: ")
    
    print(f"\n🎯 Task: {task}")
    
    # Check credentials
    if EMAIL and APP_PASSWORD:
        print(f"🔐 Credentials loaded: {EMAIL}")
    else:
        print("⚠️  No credentials in .env - login tasks may fail")
    
    print("\n⏳ Starting agent execution...\n")
    
    # Run task (credentials will be added automatically in run_task)
    asyncio.run(run_task(task))