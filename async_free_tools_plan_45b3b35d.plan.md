---
name: Async Free Tools Plan
overview: Design a global, zero-cost tool-augmented travel pipeline using OSM/Open-Meteo/OpenTripMap, with async fan-out and streaming partial results, while keeping room for later LangGraph adoption.
todos:
  - id: tool-clients
    content: Create free tool clients for Overpass, Open-Meteo, and optional OpenTripMap fallback
    status: completed
  - id: travel-orchestrator
    content: Implement async travel pipeline with parallel tool fan-out and normalized section outputs
    status: completed
  - id: streaming-interface
    content: Add web SSE and CLI progressive rendering for partial section updates
    status: completed
  - id: phone-priority
    content: Add ranking and filtering rules prioritizing entries with real phone tags
    status: completed
  - id: cache-and-timeouts
    content: Add section-level caching plus per-tool/global timeout budgets
    status: completed
  - id: langgraph-ready-contract
    content: Define state contracts to allow later LangGraph migration without entrypoint changes
    status: completed
isProject: false
---

# Async Free Travel Tools Plan

## Objectives
- Add free external tools for weather, hotels/restaurants (with phone when available), and attractions.
- Run tool calls concurrently to minimize latency.
- Stream partial results to the user as each tool finishes.
- Keep current architecture compatible with an optional future LangGraph migration.

## Chosen Constraints
- Data stack: `osm_only` (no paid APIs, no mandatory API keys).
- Scope: global.

## Tooling Strategy (Free)
- **Geocoding / place resolution**: keep existing resolver in [core/location_resolver.py](/home/tnc/projects/AI/Travel_agent/core/location_resolver.py), backed by Nominatim/Photon.
- **Hotels & restaurants (+ phone)**: add Overpass queries over OSM (`tourism=hotel`, `amenity=restaurant`) and extract `contact:phone`/`phone` tags when present.
- **Weather**: integrate Open-Meteo forecast endpoint using resolved `lat/lon`.
- **Attractions**: primary via OSM Overpass (`tourism=attraction`, `historic=*`, `museum=*`), optional fallback via OpenTripMap free endpoints when OSM density is weak.

## Architecture Changes
- Add tool clients:
  - [core/tools/osm_overpass_client.py](/home/tnc/projects/AI/Travel_agent/core/tools/osm_overpass_client.py)
  - [core/tools/openmeteo_client.py](/home/tnc/projects/AI/Travel_agent/core/tools/openmeteo_client.py)
  - [core/tools/opentripmap_client.py](/home/tnc/projects/AI/Travel_agent/core/tools/opentripmap_client.py) (optional fallback)
- Add domain orchestrator:
  - [core/travel_pipeline.py](/home/tnc/projects/AI/Travel_agent/core/travel_pipeline.py)
  - Owns async fan-out/fan-in, timeout policy, retries, normalization, and ranking.
- Keep entrypoints thin:
  - [ui/app.py](/home/tnc/projects/AI/Travel_agent/ui/app.py)
  - [main.py](/home/tnc/projects/AI/Travel_agent/main.py)
  - Replace direct travel generation call with one pipeline call.

## Async + Streaming Design
- Use `asyncio.gather` (or task group) to launch in parallel:
  - weather task
  - hotels task
  - restaurants task
  - attractions task
- Emit incremental updates as tasks complete:
  - Web: SSE endpoint (e.g. `/ask/stream`) that streams `location_resolved`, then `weather_ready`, `hotels_ready`, `restaurants_ready`, `attractions_ready`, then `final_ready`.
  - CLI: print progressive sections as each task returns.
- Final assistant synthesis starts as soon as minimum viable sections are ready (weather + at least one POI section), then updates when late sections arrive.

## Phone Number Requirement Handling
- Source phone fields from OSM tags in priority order:
  - `contact:phone`
  - `phone`
- If missing, mark explicitly as unavailable (never hallucinate phone numbers).
- Rank venues with phone present higher than those without phone.

## Performance Rules
- Per-tool timeout budget (e.g. 4-8s) and global SLA budget (e.g. 12-15s).
- Reuse existing location cache and add result caches per section:
  - weather cache by `lat/lon+date`
  - places cache by `lat/lon+radius+category`
- Return partial response even if one provider fails.

## LangGraph Readiness (Optional Later)
- Keep pipeline APIs state-oriented (`TravelContext` + `SectionResults`) so migration is straightforward.
- If workflow complexity grows (more tools, retries, branch logic, human-in-loop), replace orchestrator internals with LangGraph nodes without changing entrypoints.

## Rollout Phases
1. Add free tool clients and normalized schemas.
2. Implement async orchestrator returning structured section payloads.
3. Add streaming transport in web and progressive output in CLI.
4. Add ranking/phone-priority logic and section caches.
5. Add optional OpenTripMap fallback + observability.

## Acceptance Criteria
- Travel request returns weather/hotels/restaurants/attractions via tools (not pure LLM-only guesses).
- Hotel/restaurant results include real phone numbers when available from source data.
- End-to-end latency improved via parallel execution and partial streaming.
- System still works in degraded mode when one tool times out.