# Multi-Agent Chatbot

A flexible and extensible multi-agent chatbot system built with Python.

## Features
- Modular agent system
- Multiple LLM provider support (OpenAI, Anthropic, Hugging Face)
- Easy to extend with new agents
- SOLID principles implementation
- Automatic fallback between providers based on available API keys

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys (copy from .env.example):
```
# Required for OpenAI agents
OPENAI_API_KEY=your_api_key_here

# Required for Anthropic agents
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional for Hugging Face (provides higher rate limits)
HUGGINGFACE_API_KEY=your_huggingface_api_key_here
```

Note: You only need to provide keys for the APIs you want to use. The system will automatically use available APIs.

## Usage

Run the chatbot:
```bash
python main.py
```

Test Hugging Face agent specifically:
```bash
python test_huggingface.py
```

## Project Structure
- `main.py`: Entry point of the application
- `agents/`: Directory containing different agent implementations
  - `openai/`: OpenAI-based agents
  - `anthropic/`: Anthropic-based agents
  - `huggingface/`: Hugging Face-based agents
- `core/`: Core components and interfaces
- `config/`: Configuration files

## Supported LLM Providers
- **OpenAI**: Requires API key, uses models like gpt-3.5-turbo and gpt-4
- **Anthropic**: Requires API key, uses Claude models
- **Hugging Face**: Can be used with or without API key (rate limited without key) # Travel_agent
