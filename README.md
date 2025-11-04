# **Agent B**
###*Browser automation system with intelligent screenshot filtering.*

###Features:

- **AI Agent**: Autonomous web browsing using natural language instructions
- **Smart Screenshots**: Automatic capture with duplicate filtering
- **GIF Recording**: Full session recordings for visual debugging
- **Web Interface**: Streamlit UI for task management
- **Task History**: Complete history with screenshot galleries
- **Privacy-First**: Runs locally with credential redaction


## **Quick Start**

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
BROWSER_USE=your_browser-use_api_key_here
GMAIL_USER=your.email@gmail.com
GMAIL_PASS=your_gmail_app_password
```

### 3. Run the Application

#### Option A: Streamlit Web Interface (Recommended)

```bash
streamlit run streamlit_app.py
```

Then open your browser to `http://localhost:8501`

#### Option B: Command Line

```bash
python app.py
```



## **Usage Guide**

### Streamlit Web Interface

1. **Navigate to "Run Task" tab**
2. **Enter your task** in natural language:
   - Example: "Search for 'Python tutorials' on Google"
   - Example: "Go to Amazon and search for 'wireless mouse'"
3. **Click "Run Task"** and wait for completion
4. **View results** in the "Task History" tab

### Command Line Interface

```bash
python app.py "Go to Google and search for 'AI news'"
```

Or run interactively:
```bash
python app.py
# Enter task when prompted
```

---

##  **Good Task Examples**

✔ **Simple Search Tasks**
```
Search for 'machine learning courses' on Google
Go to YouTube and search for 'Python tutorials'
Open Wikipedia and search for 'Artificial Intelligence'
```

✔ **E-commerce Tasks**
```
Go to Amazon and search for 'laptop'
Visit eBay and search for 'vintage cameras'
```

✔ **Navigation Tasks**
```
Go to GitHub and search for 'web scraping'
Visit Stack Overflow and search for 'Python async'
```

✗ **Avoid These**
```
✗ Tasks requiring CAPTCHA solving
✗ Tasks requiring payment/checkout
✗ Tasks with complex multi-step verification
```


## Project Structure

```
browser-use/
├── app.py                  # Core automation logic
├── streamlit_app.py        # Web interface
├── requirements.txt        # Python dependencies
├── .env                    # Credentials (create this)
├── README.md               # This file
└── dataset/                # Generated task results
    └── {task-slug}/
        └── {timestamp}/
            ├── run.gif            # Full recording
            ├── summary.json       # Task metadata
            └── frames/
                ├── frame_000.png  # Kept frames
                ├── frame_001.png
                └── duplicates/    # Filtered frames
```



## Configuration Options

### app.py Settings

Edit these parameters in `run_task()`:

```python
agent = Agent(
    task=task,
    use_vision=True,              # Enable vision capabilities
    vision_detail_level="high",   # high/low/auto
    max_failures=3,               # Retry attempts
    step_timeout=180,             # Timeout per step (seconds)
)

history = await agent.run(max_steps=30)  # Maximum steps
```

### Streamlit Settings

Accessible via sidebar in the web interface:
- **Max Steps**: Adjust maximum agent steps (5-50)
- **Show Duplicates**: Toggle duplicate frame visibility


## Advanced Usage

### Custom Task Execution

```python
import asyncio
from app import run_task

# Run custom task
asyncio.run(run_task("Your task here", dataset_root=Path("custom_output")))
```

### Adjust Viewport Size

Modify in `app.py`:

```python
await set_viewport(agent, width=1920, height=1080)
```

## Troubleshooting

### Issue: Browser Won't Launch

**Solution**: Ensure Chrome/Chromium is installed
```bash
# Install Chrome on Ubuntu
sudo apt-get install chromium-browser
```

### Issue: Import Errors

**Solution**: Reinstall dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Issue: Credentials Not Loading

**Solution**: Verify .env file format
```bash
# Check if .env exists and is readable
cat .env

# Ensure no extra spaces or quotes
# Correct: OPENAI_API_KEY=sk-xxxxx
# Wrong:   OPENAI_API_KEY = "sk-xxxxx"
```


## System Requirements

- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for dependencies + storage for screenshots
- **OS**: Windows, macOS, or Linux
- **Browser**: Chrome/Chromium (automatically managed)

##  Security & Privacy

- All processing runs **locally** on your machine
- Credentials stored in **local .env** file (not version controlled)
- Screenshots stored **locally** in `dataset/` folder
- Keep your `.env` file **secure** and never commit it


## Quick Test

Run this simple test to verify everything works:

```bash
# Test 1: Check dependencies
pip list | grep -E "browser-use|openai|streamlit"

# Test 2: Run simple task
python app.py "Go to example.com"

# Test 3: Launch Streamlit
streamlit run streamlit_app.py
```


Enjoy using Agent B! ✨


