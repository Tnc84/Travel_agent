# Multi-Agent Travel Assistant

A flexible and extensible multi-agent travel assistant built with Python.

## Features
- Modular multi-agent architecture
- Multiple LLM provider support (Ollama, Hugging Face)
- Free travel data pipeline (OpenStreetMap Overpass + Open-Meteo, optional OpenTripMap fallback)
- Async tool fan-out with partial/degraded responses
- Streaming support for web (`/ask/stream`) and progressive rendering in CLI
- Flexible date parsing (RO/EN): `15 Aug`, `23 Iul`, `Jul 23`, `August 15`, `25-04`, `10-23`
- Phone-aware ranking for venues (`contact:phone` / `phone` first)
- Centralized provider/model selection in `core/provider_factory.py`
- Centralized agent registration/routing in `core/agent_registry.py` and `core/intent_router.py`

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

4. Create a `.env` file:
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

# Travel pipeline timeouts/caches
TRAVEL_TOOL_TIMEOUT_SECONDS=8
TRAVEL_GLOBAL_TIMEOUT_SECONDS=15
TRAVEL_SEARCH_RADIUS_M=4000
TRAVEL_WEATHER_CACHE_TTL_SECONDS=1800
TRAVEL_PLACES_CACHE_TTL_SECONDS=1800

# Free tools endpoints
OPEN_METEO_ENDPOINT=https://api.open-meteo.com/v1/forecast
OPEN_METEO_ARCHIVE_ENDPOINT=https://archive-api.open-meteo.com/v1/archive
OVERPASS_ENDPOINTS=https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter,https://overpass.openstreetmap.fr/api/interpreter

# Optional: OpenTripMap fallback for attractions
OPENTRIPMAP_API_KEY=
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

### Travel Query Examples
- `I want to go to London on 23 Iul`
- `London 15 August`
- `I want to go to New York on December 24`
- `Paris 25-04`
- `Rome 10-23`

Numeric ambiguous dates like `06-12` are rejected by design to avoid silent misinterpretation.

## Project Structure
- `main.py`: CLI entry point
- `run.py`: web app launcher
- `ui/`: web interface
- `agents/`: specialized agents only
- `providers/`: LLM provider abstractions and implementations
- `core/`: coordinator, provider factory, registry, router, location and travel pipeline logic
- `core/tools/`: external free tool clients (Overpass, Open-Meteo, OpenTripMap)

## Architecture Notes
- `providers/base.py`: abstract provider contract (`LLMProvider`)
- `providers/ollama.py`, `providers/huggingface.py`: concrete provider implementations
- `core/provider_factory.py`: selects provider and model from environment with fallback
- `core/agent_registry.py`: single source of truth for available agents and routing keywords
- `core/agent_builder.py`: creates, initializes, and registers all agents
- `core/intent_router.py`: shared intent detection and keyword routing
- `core/date_parser.py`: normalizes flexible user dates to ISO (`YYYY-MM-DD`)
- `core/location_resolver.py`: canonical location resolution with confidence scoring
- `core/location_providers.py`: free geocoding adapters (Nominatim + Photon)
- `core/location_cache.py`: TTL cache for location lookups
- `core/travel_pipeline.py`: async orchestration for weather/hotels/restaurants/attractions
- `core/travel_flow.py`: thin integration layer for CLI/web entrypoints
- `core/tools/osm_overpass_client.py`: OSM POI retrieval + failover endpoints
- `core/tools/openmeteo_client.py`: forecast + climate-normal fallback for distant dates
- `core/tools/opentripmap_client.py`: optional attractions fallback
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

## Travel Pipeline Behavior
- Runs weather + POI sections in parallel.
- Returns partial output if one provider fails.
- For dates beyond live forecast horizon, weather uses climate-normal fallback from historical data.
- Hotels/restaurants/attractions are prioritized by real phone availability when present.
- SSE endpoint `POST /ask/stream` emits: `location_resolved`, section-ready events, `final_message`, `done`.
