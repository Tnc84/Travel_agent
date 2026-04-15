# Multi-Agent Chatbot

A flexible and extensible multi-agent chatbot system built with Python.

## Features
- Modular agent system
- Multiple LLM provider support (Ollama, Hugging Face)
- Easy to extend with new agents
- SOLID principles implementation
- Centralized provider/model selection in `core/provider_factory.py` with fallback support

## Setup

1. Install required Ubuntu packages:
```bash
sudo apt update
sudo apt install python3-pip python3.12-venv
```

2. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```
# Optional for Hugging Face (higher rate limits with key)
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Optional provider selection: ollama or huggingface
LLM_PROVIDER=ollama

# Optional model settings
OLLAMA_MODEL=mistral:latest
HUGGINGFACE_MODEL=HuggingFaceH4/zephyr-7b-beta
```

Note: do not use global `pip install` on Ubuntu system Python. Install packages only inside `.venv`.

## Usage

Run CLI chatbot:
```bash
python3 main.py
```

Run web interface:
```bash
python3 run.py
```

Then open `http://127.0.0.1:5000`.

## Project Structure
- `main.py`: CLI entry point
- `run.py`: web app launcher
- `ui/`: web interface
- `agents/`: specialized agents and LLM providers
- `core/`: coordinator and base abstractions

## Supported LLM Providers
- **Ollama**: local server (default `http://localhost:11434`)
- **Hugging Face**: API-based provider (works with or without key, rate-limited without key)
