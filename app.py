import asyncio
import base64
import json
import time
import re
import hashlib
import os
from pathlib import Path
from typing import Any
from PIL import Image, ImageSequence, ImageStat
from dotenv import load_dotenv
from browser_use import Agent, Browser, ChatBrowserUse
from openai import OpenAI

load_dotenv()

EMAIL = os.getenv("GMAIL_USER")
APP_PASSWORD = os.getenv("GMAIL_PASS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# utils
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


def is_blank_frame(frame: Image.Image, threshold: float = 15.0) -> bool:
    """Detect if a frame is mostly blank."""
    gray = frame.convert("L")
    stat = ImageStat.Stat(gray)
    return stat.stddev[0] < threshold


# Extract last frame from GIF
def extract_last_frame_from_gif(gif_path: Path, output_path: Path):
    try:
        with Image.open(gif_path) as im:
            frames = [frame.copy().convert("RGB") for frame in ImageSequence.Iterator(im)]
            if frames:
                frames[-1].save(output_path, "PNG")
                print(f"Last frame extracted and saved as: {output_path}")
    except Exception as e:
        print(f"Could not extract last frame from {gif_path}: {e}")


# CDP helpers
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


# Run
async def run_task(task: str, dataset_root: Path = Path("dataset")):
    """
    Execute a browser automation task with AI agent.
    """
    enhanced_task = f"""
TASK: {task}

INSTRUCTIONS FOR EXECUTION:
1. READ CAREFULLY
2. BE PRECISE
3. BE PATIENT
4. BE THOROUGH
5. BE SMART
6. BE OBSERVANT
"""

    if EMAIL and APP_PASSWORD:
        enhanced_task += f"""
AUTHENTICATION CREDENTIALS:
- Email: {EMAIL}
- Password: {APP_PASSWORD}"""
    else:
        enhanced_task += "\nNOTE: No login credentials available."

    task_slug = slugify(task)
    run_dir = dataset_root / task_slug / now_ts()
    ensure_dir(run_dir)

    browser = Browser(use_cloud=False, headless=False)
    llm = ChatBrowserUse()

    agent = Agent(
        task=enhanced_task,
        llm=llm,
        browser=browser,
        use_vision=True,
        vision_detail_level="high",
        generate_gif=str(run_dir / "run.gif"),
        max_failures=5,
        retry_delay=2,
        step_timeout=180,
    )

    print("Agent configured.")
    await asyncio.sleep(0.2)
    try:
        await set_viewport(agent, width=1366, height=768)
    except Exception:
        pass

    history = await agent.run(max_steps=30)

    await asyncio.sleep(5)  # ensure final frames are written

    # Extract GIF frames
    gif_path = run_dir / "run.gif"
    frames_dir = run_dir / "frames"
    ensure_dir(frames_dir)
    last_frame_path = frames_dir / "frame_last.png"

    if gif_path.exists():
        print(f"Extracting frames from GIF: {gif_path}")
        gif = Image.open(gif_path)
        kept_frames = 0

        for i, frame in enumerate(ImageSequence.Iterator(gif)):
            if i == 0:
                continue  # skip first frame
            frame = frame.convert("RGB").copy()
            if is_blank_frame(frame):
                continue
            frame_path = frames_dir / f"frame_{kept_frames:03d}.png"
            frame.save(frame_path)
            kept_frames += 1

        extract_last_frame_from_gif(gif_path, last_frame_path)
        print(f"Extracted {kept_frames} frames + last frame.")
    else:
        print("No GIF generated.")

    # Step extraction 
    steps_data = []
    history_items = history.history if isinstance(history.history, list) else []

    for step_idx, history_item in enumerate(history_items):
        step_info = {
            "step_number": step_idx + 1,
            "action_type": "Unknown",
            "thought": "",
            "url": "",
            "action_details": "",
            "screenshot": "",
            "interacted_element": "",
            "action_description": "",
        }

        try:
            if hasattr(history_item, 'state') and history_item.state:
                state = history_item.state
                step_info['url'] = getattr(state, 'url', '')
                step_info['title'] = getattr(state, 'title', '')
                if hasattr(state, 'interacted_element') and state.interacted_element:
                    interacted = state.interacted_element[0] if isinstance(state.interacted_element, list) else state.interacted_element
                    if interacted:
                        step_info['interacted_element'] = str(interacted)

            if hasattr(history_item, 'model_output') and history_item.model_output:
                model_output = history_item.model_output
                if hasattr(model_output, 'current_state') and model_output.current_state:
                    current_state = model_output.current_state
                    evaluation = getattr(current_state, 'evaluation_previous_goal', '')
                    memory = getattr(current_state, 'memory', '')
                    next_goal = getattr(current_state, 'next_goal', '')
                    thought_parts = []
                    if evaluation: thought_parts.append(f"Evaluation: {evaluation}")
                    if memory: thought_parts.append(f"Memory: {memory}")
                    if next_goal: thought_parts.append(f"Next Goal: {next_goal}")
                    step_info['thought'] = "\n\n".join(thought_parts)

                if hasattr(model_output, 'action') and model_output.action:
                    actions = model_output.action
                    if actions and len(actions) > 0:
                        first_action = actions[0]
                        action_class_name = first_action.__class__.__name__ if hasattr(first_action, '__class__') else 'Unknown'
                        if hasattr(first_action, 'model_dump'):
                            action_dict = first_action.model_dump(exclude_none=True)
                            step_info['action_details'] = json.dumps(action_dict, indent=2)
                            # Determine action type
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
                        else:
                            step_info['action_type'] = action_class_name.replace('Action', '').strip() or 'Browser Action'

            if hasattr(history_item, 'result') and history_item.result:
                results = history_item.result
                if results and len(results) > 0:
                    result = results[0]
                    if hasattr(result, 'extracted_content') and result.extracted_content:
                        step_info['extracted_content'] = str(result.extracted_content)[:200]
                    if hasattr(result, 'error') and result.error:
                        step_info['error'] = str(result.error)

        except Exception as e:
            print(f"Could not extract full details for step {step_idx + 1}: {e}")

        steps_data.append(step_info)

    for s in steps_data:
        if not s.get("action_type") or s.get("action_type").lower() == "unknown":
            s["action_type"] = "Action"

    (run_dir / "steps_details.json").write_text(
        json.dumps(steps_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Saved {len(steps_data)} steps (no filtering)")

    frames_count = len(list(frames_dir.glob('*.png'))) if frames_dir.exists() else 0
    summary = {
        "task": task,
        "success": bool(history.is_successful()),
        "steps": len(steps_data),
        "urls": history.urls(),
        "errors": history.errors(),
        "gif": str(gif_path),
        "total_frames": frames_count,
        "last_frame": str(last_frame_path),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nSaved run to: {run_dir.resolve()}\n")


# Main
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
    else:
        task = input("Enter your task: ")
    print(f"\nTask: {task}")
    if EMAIL and APP_PASSWORD:
        print(f"Credentials loaded: {EMAIL}")
    else:
        print("No credentials in .env - login tasks may fail")
    print("\nStarting agent execution...\n")
    asyncio.run(run_task(task))
