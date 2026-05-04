# Multi-Agent Travel Assistant

A flexible and extensible multi-agent travel assistant built with Python.

## Features
- Modular multi-agent architecture
- Multiple LLM provider support (Ollama, Hugging Face)
- Free travel data pipeline (OpenStreetMap Overpass + Open-Meteo, optional OpenTripMap fallback)
- LangGraph-based travel runtime with parallel weather + POI branches and partial/degraded responses
- Postgres checkpointing for durable, resumable graph state
- Streaming support for web (`/ask/stream`) and progressive rendering in CLI
- Flexible date parsing (RO/EN): `15 Aug`, `23 Iul`, `Jul 23`, `August 15`, `25-04`, `10-23`
- Phone-aware ranking for venues (`contact:phone` / `phone` first)
- Centralized provider/model selection in `core/llm/wiring.py` (`build_primary_provider`)
- Centralized agent wiring in `core/agent_platform/` and intent routing in `core/intent/`

## System architecture

High-level view of the repository: entrypoints, shared core services, the LangGraph travel runtime (with Postgres checkpointing), free-data tools, and the multi-agent LLM stack.

```mermaid
flowchart TB
  subgraph users["Users"]
    UCLI["CLI user"]
    UWEB["Browser"]
  end

  subgraph entry["Entrypoints"]
    MAIN["main.py"]
    RUNPY["run.py"]
    FLASK["ui/app.py Flask"]
  end

  subgraph shared["Shared core"]
    VAL["validation"]
    IR["intent travel_match / keyword_route"]
    LRES["location.resolver"]
    LPROV["location.providers + cache"]
  end

  subgraph graph_rt["LangGraph travel runtime core/graph"]
    RUNNER["runner invoke / stream_events"]
    BUILD["graph_builder"]
    CFG["config validate"]
    CKPT["checkpoint PostgresSaver or InMemory"]
    subgraph gnodes["Graph nodes"]
      N1["resolve_location"]
      N2["normalize_date"]
      N3["fetch_weather"]
      N4["fetch_poi"]
      N5["rank_and_filter"]
      N6["synthesize_response"]
      N7["fallback_response"]
      NCL["clarify terminal"]
    end
  end

  subgraph freetools["core/tools external APIs"]
    METEO["OpenMeteo forecast archive"]
    OVER["OSM Overpass"]
    OTM["OpenTripMap optional"]
  end

  subgraph llm["LLM and agents"]
    PFACT["llm wiring"]
    PIMPL["llm_providers Ollama HuggingFace"]
    ABUILD["agent_platform.builder"]
    AREG["agent_platform.registry"]
    COORD["coordinator"]
    AGENTS["agents prompts"]
  end

  subgraph persist["Persistence and ops"]
    PG[("Postgres checkpoint store")]
    HIST["history JSON logs"]
  end

  UCLI --> MAIN
  UWEB --> RUNPY
  RUNPY --> FLASK
  MAIN --> VAL
  FLASK --> VAL
  VAL --> IR
  IR -->|general chat| COORD
  IR -->|travel intent| RUNNER
  N1 --> LRES
  LRES --> LPROV
  RUNNER --> CFG
  RUNNER --> BUILD
  BUILD --> CKPT
  CKPT -.->|LANGGRAPH_CHECKPOINT_DSN| PG
  RUNNER --> N1
  N1 --> N2
  N2 --> N3
  N2 --> N4
  N3 --> N5
  N4 --> N5
  N5 -->|has section data| N6
  N5 -->|no data| N7
  N1 -.->|low confidence| NCL
  N2 -.->|bad date| NCL
  N3 --> METEO
  N4 --> OVER
  N4 --> OTM
  N6 --> COORD
  COORD --> AGENTS
  ABUILD --> COORD
  AREG -.->|agent defs| IR
  PFACT --> PIMPL
  ABUILD --> PIMPL
  FLASK --> HIST
```

Legend: every travel request goes straight to **TravelGraphRunner**; the graph itself owns location resolution, date normalization, tool fan-out, ranking, synthesis and clarification. State is persisted in **Postgres** when `LANGGRAPH_CHECKPOINT_DSN` is set. If the DSN is unset and `LANGGRAPH_ALLOW_NO_CHECKPOINT` is not `0`, the runtime defaults to **InMemory** (local dev). Set `LANGGRAPH_ALLOW_NO_CHECKPOINT=0` to require Postgres. **synthesize_response** delegates to the **Coordinator** so the Assistant agent uses the configured LLM provider on top of tool-grounded prompts.

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
TRAVEL_GLOBAL_TIMEOUT_SECONDS=90
TRAVEL_SEARCH_RADIUS_M=4000
TRAVEL_WEATHER_CACHE_TTL_SECONDS=1800
TRAVEL_PLACES_CACHE_TTL_SECONDS=1800

# LangGraph travel runtime
LANGGRAPH_ENABLED=1
# Postgres DSN for durable graph checkpointing (psycopg/psycopg-pool format).
# If unset and LANGGRAPH_ALLOW_NO_CHECKPOINT is not set to 0, the app uses an in-memory
# checkpointer so local runs work without Postgres (logs a warning).
LANGGRAPH_CHECKPOINT_DSN=postgresql://travel:travel@localhost:5432/travel_agent
# Set to 0 to require LANGGRAPH_CHECKPOINT_DSN (fail fast without Postgres).
# Set to 1 to allow in-memory checkpointing even when a DSN is configured but unreachable.
LANGGRAPH_ALLOW_NO_CHECKPOINT=0
# Optional retention policy for graph threads (seconds; informational, not auto-pruned)
LANGGRAPH_THREAD_TTL_SECONDS=86400

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
- `llm_providers/`: LLM provider abstractions and implementations (Ollama, Hugging Face)
- `core/`: LangGraph travel runtime, agent platform, intent, LLM wiring, validation, location stack
- `core/tools/`: external free tool clients (Overpass, Open-Meteo, OpenTripMap)

## Architecture Notes
- `llm_providers/base.py`: abstract provider contract (`LLMProvider`)
- `llm_providers/ollama.py`, `llm_providers/huggingface.py`: concrete provider implementations
- `core/llm/wiring.py`: selects provider and model from environment with fallback (`build_primary_provider`)
- `core/agent_platform/`: multi-agent orchestration (distinct from top-level package `agents/`)
  - `core/agent_platform/registry.py`: `@register_agent` and keyword metadata
  - `core/agent_platform/builder.py`: `build_agents` / `discover_agents` (import explicitly — avoids cycles with `agents/`)
  - `core/agent_platform/coordinator.py`: dispatch `process_message` to named agents
  - `core/agent_platform/base.py`: `Message` and `Agent` abstract base
- `core/intent/`: travel regex vs keyword routing (`match_travel_intent`, `route_by_keywords`)
- `core/date/parser.py`: normalizes flexible user dates to ISO (`normalize_user_date_to_iso`)
- `core/validation.py`: user input length and emptiness checks
- `core/support/`: small cross-cutting helpers (`clean_llm_response`, `retry_on_error`)
- `core/location/`: geocoding subsystem (public API: `LocationResolver`, `LocationResult`)
  - `core/location/resolver.py`: canonical location resolution with confidence scoring
  - `core/location/providers.py`: free geocoding adapters (Nominatim + Photon)
  - `core/location/cache.py`: TTL cache for location lookups
- `core/graph/`: LangGraph travel runtime (state, nodes, builder, runner, checkpoint)
  - `core/graph/state.py`: `TravelGraphState` typed schema and reducers
  - `core/graph/graph_builder.py`: graph topology, conditional edges, parallel branches
  - `core/graph/runner.py`: invoke/stream adapters used by entrypoints
  - `core/graph/checkpoint.py`: Postgres + in-memory checkpoint lifecycle
  - `core/graph/config.py`: runtime config + fail-fast validation
  - `core/graph/nodes/`: location, weather, POI, ranking, synthesis, fallback nodes
- `core/tools/osm_overpass_client.py`: OSM POI retrieval + failover endpoints
- `core/tools/openmeteo_client.py`: forecast + climate-normal fallback for distant dates
- `core/tools/opentripmap_client.py`: optional attractions fallback
- `agents/prompts/`: reusable system prompts for each agent

## Extending The System
- Add a new agent: create the agent class, add its prompt, then decorate with `@register_agent` from `core.agent_platform` (see existing files under `agents/`)
- Add a new provider: implement it in `llm_providers/` and wire it into `core/llm/wiring.py`
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
- All travel requests are executed by the LangGraph runtime in `core/graph/`.
- Weather + POI run as parallel graph branches and fan in to ranking → synthesis.
- Returns partial output if one provider fails (graceful degradation by node error policy).
- For dates beyond live forecast horizon, weather uses climate-normal fallback from historical data.
- Hotels/restaurants/attractions are prioritized by real phone availability when present.
- SSE endpoint `POST /ask/stream` emits: `location_resolved`, section-ready events, `final_message`, `done`.

## LangGraph Runtime Runbook
### Postgres setup (durable checkpointing)
1. Create the database/role:
   ```bash
   sudo -u postgres psql -c "CREATE ROLE travel WITH LOGIN PASSWORD 'travel';"
   sudo -u postgres psql -c "CREATE DATABASE travel_agent OWNER travel;"
   ```
2. Set `LANGGRAPH_CHECKPOINT_DSN` in `.env` to the resulting DSN.
3. On first startup the runtime calls `PostgresSaver.setup()` which creates the
   required checkpoint tables automatically.

### Startup and checkpoint mode
- If `LANGGRAPH_CHECKPOINT_DSN` is set, the runtime uses **Postgres** (tables created on first `setup()`).
- If the DSN is **unset** and `LANGGRAPH_ALLOW_NO_CHECKPOINT` is not `0`, the runtime defaults to an **in-memory** checkpointer (one-time warning in logs) so `python3 run.py` works without Postgres.
- Set `LANGGRAPH_ALLOW_NO_CHECKPOINT=0` to **require** a DSN (fail fast when Postgres is not configured).
- If a DSN is set but Postgres is unreachable, `open_checkpointer` can fall back to in-memory only when `LANGGRAPH_ALLOW_NO_CHECKPOINT=1`.

### Failure modes and recovery
- Per-node timeouts (`TRAVEL_TOOL_TIMEOUT_SECONDS`) bound external API calls.
- Graph-global per-step timeout (`TRAVEL_GLOBAL_TIMEOUT_SECONDS`) is enforced
  via LangGraph `step_timeout` as an overall guardrail.
- Each graph run has a `run_id` and `thread_id` written to logs and history files;
  use `thread_id` to resume an interrupted travel computation by re-invoking the
  graph with the same `thread_id` (Postgres checkpointer required).
- When all sections fail, the `fallback_response` node returns a deterministic
  structured response so users still receive useful guidance.

### Observability
- Node-level structured logs include `run_id`, `thread_id`, `node`, `duration_ms`.
- `final_state["timings_ms"]` returns per-node timings for the run.
- Web `/ask` records `run_id` and `thread_id` in the per-request history JSON.
