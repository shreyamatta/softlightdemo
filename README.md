# 🤖 Browser Automation Agent

AI-powered browser automation system with intelligent screenshot filtering and a beautiful Streamlit web interface.

---

## 🌟 Features

- **🤖 AI Agent**: Autonomous web browsing using natural language instructions
- **📸 Smart Screenshots**: Automatic capture with GPT-4 Vision duplicate filtering
- **🎥 GIF Recording**: Full session recordings for visual debugging
- **🖥️ Web Interface**: Beautiful Streamlit UI for task management
- **📊 Task History**: Complete history with screenshot galleries
- **🔒 Privacy-First**: Runs locally with credential redaction

---

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
GMAIL_USER=your.email@gmail.com
GMAIL_PASS=your_gmail_app_password
```

> **Note**: Use Gmail App Password (not regular password) from your Google Account settings.

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

---

## 📖 Usage Guide

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

## 🎯 Good Task Examples

✅ **Simple Search Tasks**
```
Search for 'machine learning courses' on Google
Go to YouTube and search for 'Python tutorials'
Open Wikipedia and search for 'Artificial Intelligence'
```

✅ **E-commerce Tasks**
```
Go to Amazon and search for 'laptop'
Visit eBay and search for 'vintage cameras'
```

✅ **Navigation Tasks**
```
Go to GitHub and search for 'web scraping'
Visit Stack Overflow and search for 'Python async'
```

❌ **Avoid These**
```
❌ Tasks requiring CAPTCHA solving
❌ Tasks requiring payment/checkout
❌ Tasks with complex multi-step verification
```

---

## 📁 Project Structure

```
browser-use/
├── app.py                  # Core automation logic
├── streamlit_app.py        # Web interface
├── requirements.txt        # Python dependencies
├── .env                    # Credentials (create this)
├── README.md              # This file
└── dataset/               # Generated task results
    └── {task-slug}/
        └── {timestamp}/
            ├── run.gif            # Full recording
            ├── summary.json       # Task metadata
            └── frames/
                ├── frame_000.png  # Kept frames
                ├── frame_001.png
                └── duplicates/    # Filtered frames
```

---

## 🔧 Configuration Options

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

---

## 🛠️ Advanced Usage

### Custom Task Execution

```python
import asyncio
from app import run_task

# Run custom task
asyncio.run(run_task("Your task here", dataset_root=Path("custom_output")))
```

### Disable GPT Filtering

Comment out the filtering section in `app.py`:

```python
# decision = gpt_filter_screenshots(sanitize_task_text(task), all_frames)
decision = {"keep": all_frames, "skip": []}
```

### Adjust Viewport Size

Modify in `app.py`:

```python
await set_viewport(agent, width=1920, height=1080)
```

---

## 🐛 Troubleshooting

### Issue: GPT Filtering Fails

**Solution**: Check your OpenAI API key and billing status
```bash
# Test API key
python -c "from openai import OpenAI; print(OpenAI().models.list())"
```

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

---

## 📊 System Requirements

- **Python**: 3.8 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 500MB for dependencies + storage for screenshots
- **OS**: Windows, macOS, or Linux
- **Browser**: Chrome/Chromium (automatically managed)

---

## 🔐 Security & Privacy

- ✅ All processing runs **locally** on your machine
- ✅ Credentials stored in **local .env** file (not version controlled)
- ✅ Sensitive data **redacted** before sending to OpenAI
- ✅ Screenshots stored **locally** in `dataset/` folder
- ⚠️ OpenAI API calls include **redacted screenshots** for filtering
- ⚠️ Keep your `.env` file **secure** and never commit it

---

## 🤝 Contributing

Contributions welcome! Please follow these guidelines:

1. **Code Style**: Follow PEP 8 with production-level comments
2. **Testing**: Test all changes thoroughly
3. **Documentation**: Update README for new features
4. **Security**: Never commit credentials or API keys

---

## 📝 API Usage Costs

**OpenAI API Usage:**
- GPT-4o-mini Vision: ~$0.01-0.05 per task (15 images max)
- Filtering is **optional** and can be disabled

**Estimated Monthly Costs:**
- Light usage (10 tasks/day): ~$5-10/month
- Moderate usage (50 tasks/day): ~$25-50/month

---

## 🎓 Learning Resources

- [browser-use Documentation](https://github.com/browser-use/browser-use)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)

---

## 📜 License

This project is provided as-is for educational and research purposes.

---

## 🆘 Support

**Common Issues:**
- Check the Troubleshooting section above
- Verify all dependencies are installed
- Ensure .env file is properly configured
- Check OpenAI API billing and limits

**Still need help?**
- Check existing GitHub issues
- Review the example tasks
- Verify your environment setup

---

## 🎉 Quick Test

Run this simple test to verify everything works:

```bash
# Test 1: Check dependencies
pip list | grep -E "browser-use|openai|streamlit"

# Test 2: Run simple task
python app.py "Go to example.com"

# Test 3: Launch Streamlit
streamlit run streamlit_app.py
```

---

**Version**: 1.0.0  
**Last Updated**: November 2025  
**Status**: ✅ Production Ready

---

Happy Automating! 🚀

