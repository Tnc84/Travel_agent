# Multi-Agent Chatbot

A flexible and extensible multi-agent chatbot system built with Python.

## Features
- Modular agent system
- Multiple LLM provider support (Ollama, Hugging Face)
- Easy to extend with new agents
- SOLID principles implementation
- Centralized provider/model selection in `core/provider_factory.py` with fallback support
- Centralized agent registration/routing with `core/agent_registry.py` and `core/intent_router.py`
- Prompt management moved to `agents/prompts/`

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

# Free location resolver settings
LOCATION_DEFAULT_COUNTRY_CODE=ro
LOCATION_CONFIDENCE_THRESHOLD=0.55
LOCATION_CACHE_TTL_SECONDS=21600
LOCATION_CACHE_PERSIST=1
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
- `agents/`: specialized agents only
- `providers/`: LLM provider abstractions and implementations
- `core/`: coordinator, provider factory, registry, builder, and routing logic

## Architecture Notes
- `providers/base.py`: abstract provider contract (`LLMProvider`)
- `providers/ollama.py`, `providers/huggingface.py`: concrete provider implementations
- `core/provider_factory.py`: selects provider and model from environment with fallback
- `core/agent_registry.py`: single source of truth for available agents and routing keywords
- `core/agent_builder.py`: creates, initializes, and registers all agents
- `core/intent_router.py`: shared intent detection and keyword routing
- `core/location_resolver.py`: canonical location resolution with confidence scoring
- `core/location_providers.py`: free geocoding adapters (Nominatim + Photon)
- `core/location_cache.py`: TTL cache for location lookups
- `agents/prompts/`: reusable system prompts for each agent

## Extending The System
- Add a new agent: create the agent class, add its prompt, then register it in `core/agent_registry.py`
- Add a new provider: implement it in `providers/` and wire it into `core/provider_factory.py`
- No changes are required in `main.py` or `ui/app.py` when adding a new registered agent

## Supported LLM Providers
- **Ollama**: local server (default `http://localhost:11434`)
- **Hugging Face**: API-based provider (works with or without key, rate-limited without key)

## Free Location Resolution
- Travel inputs are resolved into canonical locations before weather/hotel/restaurant prompts are generated.
- Primary geocoding provider: **Nominatim** (OpenStreetMap), fallback: **Photon**.
- A confidence score is computed for each location candidate; low-confidence matches trigger user clarification.
- Repeated lookups are cached with TTL to reduce latency and external API calls.
- Optional cache persistence file: `history/location_cache.json`.
