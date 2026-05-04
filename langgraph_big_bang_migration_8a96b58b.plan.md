---
name: LangGraph Big Bang Migration
overview: Replace the current async travel orchestrator with a LangGraph-first runtime in one coordinated rollout, using Postgres checkpointing for durable state and resumability. Keep CLI/web contracts stable while removing superseded orchestration code.
todos:
  - id: deps-config
    content: Add LangGraph + Postgres dependencies and runtime config contract
    status: pending
  - id: state-contracts
    content: Define TravelGraphState and node IO contracts with typed schemas
    status: pending
  - id: build-graph
    content: Implement graph nodes, parallel branches, conditional edges, and checkpointer wiring
    status: pending
  - id: migrate-entrypoints
    content: Switch main.py and ui/app.py travel flow to graph invoke/stream adapters
    status: pending
  - id: remove-legacy
    content: Delete legacy orchestration file(s) and prune dead references
    status: pending
  - id: ops-docs
    content: Update README with deployment/runbook for Postgres-backed LangGraph runtime
    status: pending
isProject: false
---

# LangGraph Big-Bang Implementation Plan

## Scope And Target State
- Replace current orchestration in [core/travel_pipeline.py](/home/tnc/projects/AI/Travel_agent/core/travel_pipeline.py) with a LangGraph graph runtime that owns tool fan-out, retries, timeout policy, partial failure handling, and event emissions.
- Keep external behavior stable for [main.py](/home/tnc/projects/AI/Travel_agent/main.py) and [ui/app.py](/home/tnc/projects/AI/Travel_agent/ui/app.py) (same travel UX), but route all travel execution through graph invoke/stream APIs.
- Use Postgres checkpointing from day one for durable graph state, resumability, and production incident recovery.

## Design Principles (Best Practice)
- **Single source of truth state**: define a typed `TravelGraphState` (input, resolved location, sections, errors, status, timestamps, trace metadata).
- **Deterministic node contracts**: each node reads/writes explicit state keys only; no hidden side effects.
- **Idempotent tool nodes**: external API calls wrapped with retry + timeout + circuit-friendly error mapping.
- **Observable by default**: node-level logs, graph run IDs, and consistent error taxonomy.
- **Entry-point stability**: keep CLI/web request handlers thin adapters around graph runtime.

## Target Architecture
- New graph package: `core/graph/`
  - `state.py`: Typed state schemas and enums.
  - `nodes/`: location resolution, weather, poi fetch, ranking, synthesis, fallback.
  - `graph_builder.py`: compiles graph with conditional edges and parallel branches.
  - `runner.py`: sync/async invoke wrappers and stream event adapters.
  - `checkpoint.py`: Postgres checkpointer wiring and lifecycle.
- Existing tool clients in `core/tools/` are reused (with minimal adapter layer if required).

## Implementation Phases

## Phase 1: Foundation And Dependencies
- Add LangGraph stack and Postgres driver dependencies.
- Introduce env config for graph runtime:
  - `LANGGRAPH_ENABLED=1`
  - `LANGGRAPH_CHECKPOINT_DSN=postgresql://...`
  - `LANGGRAPH_THREAD_TTL_*` (retention policy)
- Add migration-safe config validation at startup (fail fast if graph enabled but DSN missing).

## Phase 2: State + Node Contracts
- Define `TravelGraphState` and section payload types matching current `SectionResults` semantics.
- Map current flow behavior from [core/travel_flow.py](/home/tnc/projects/AI/Travel_agent/core/travel_flow.py) into nodes:
  - `ResolveLocationNode`
  - `NormalizeDateNode`
  - `FetchWeatherNode`
  - `FetchPOINode` (combined OSM + OpenTripMap fallback)
  - `RankAndFilterNode` (phone-priority preserved)
  - `SynthesizeResponseNode`
  - `FallbackResponseNode`
- Define explicit node error policy (`retryable`, `non_retryable`, `timeout`, `provider_unavailable`).

## Phase 3: Graph Construction (Big-Bang)
- Build graph with parallel branches for weather and POI, then fan-in for synthesis.
- Add conditional transitions:
  - low-confidence location -> clarification response path;
  - missing sections -> fallback path;
  - partial section availability -> synthesis with available data.
- Compile graph with Postgres checkpointing enabled.

## Phase 4: Entrypoint Migration
- Replace travel execution path in [main.py](/home/tnc/projects/AI/Travel_agent/main.py) to call graph `invoke/stream` only.
- Replace travel execution path in [ui/app.py](/home/tnc/projects/AI/Travel_agent/ui/app.py):
  - `/ask` uses graph invoke;
  - `/ask/stream` maps graph events to SSE (`location_resolved`, section updates, final payload).
- Keep non-travel assistant routing unchanged.

## Phase 5: Observability, Reliability, Operations
- Add structured logging with `run_id`, `thread_id`, `node_name`, `duration_ms`, `provider`.
- Add timeout budgets at node layer and graph-global guardrails.
- Add startup health checks:
  - Postgres connectivity for checkpoint store;
  - optional degraded startup mode if checkpoint unavailable (explicitly configured).
- Document operator runbook in README for DSN setup, failure modes, restart/resume behavior.

## Phase 6: Replacement And Deletions (Required)
- **Delete superseded orchestrator implementation** once graph path is verified:
  - [core/travel_pipeline.py](/home/tnc/projects/AI/Travel_agent/core/travel_pipeline.py)
- **Refactor and shrink** [core/travel_flow.py](/home/tnc/projects/AI/Travel_agent/core/travel_flow.py):
  - remove direct asyncio orchestration hooks tied to old pipeline;
  - keep only adapter helpers needed by entrypoints, or replace file entirely with `graph` runner adapters.
- Remove obsolete env keys tied only to old pipeline implementation, after README/env migration.

## Rollout Strategy (Big-Bang Safe Cutover)
- Implement graph runtime behind temporary internal toggle in development.
- Run shadow comparisons locally (old vs new outputs) for representative destinations/dates.
- Cut over default path to graph and remove old orchestrator in same release branch.
- Keep a short rollback window via git revert of the migration commit if production incident occurs.

## Acceptance Criteria
- All travel requests are executed through LangGraph runtime only.
- Postgres checkpointing is active and graph runs are resumable.
- `/ask` and `/ask/stream` preserve user-facing behavior with improved traceability.
- Degraded mode still returns useful partial/fallback responses.
- Legacy orchestration file(s) are removed, and no dead code references remain.

## Main Files To Add/Change
- Add: [core/graph/state.py](/home/tnc/projects/AI/Travel_agent/core/graph/state.py)
- Add: [core/graph/graph_builder.py](/home/tnc/projects/AI/Travel_agent/core/graph/graph_builder.py)
- Add: [core/graph/runner.py](/home/tnc/projects/AI/Travel_agent/core/graph/runner.py)
- Add: [core/graph/checkpoint.py](/home/tnc/projects/AI/Travel_agent/core/graph/checkpoint.py)
- Add: `core/graph/nodes/*.py`
- Update: [main.py](/home/tnc/projects/AI/Travel_agent/main.py)
- Update: [ui/app.py](/home/tnc/projects/AI/Travel_agent/ui/app.py)
- Update: [core/travel_flow.py](/home/tnc/projects/AI/Travel_agent/core/travel_flow.py)
- Delete: [core/travel_pipeline.py](/home/tnc/projects/AI/Travel_agent/core/travel_pipeline.py)
- Update: [README.md](/home/tnc/projects/AI/Travel_agent/README.md)
- Update: [requirements.txt](/home/tnc/projects/AI/Travel_agent/requirements.txt)