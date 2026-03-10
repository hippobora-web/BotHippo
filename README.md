# EVEngine

[![CI](https://github.com/hippobora-web/BotHippo/actions/workflows/ci.yml/badge.svg)](https://github.com/hippobora-web/BotHippo/actions/workflows/ci.yml)

EVEngine is a deterministic research prototype for event-market data collection, signal generation, risk gating, backtesting, and paper-trading experiments.

## Disclaimer

This repository is for research and prototyping only. It is not production-ready and is not suitable for unattended live trading, exchange connectivity, or real-money use.

Recent hardening work improved validation, exposure controls, and settlement handling, but the repository still lacks the operational controls required for production deployment.

## Installation

EVEngine currently targets Python 3.9 and uses a minimal `pyproject.toml`-based setup.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

## Quick Start

Run the current regression tests:

```bash
python -m unittest discover -s tests
```

Run the deterministic local smoke path using the built-in mock adapter:

```bash
python -m evengine.cli.collect_market_data --adapter mock --n 1
```

The smoke command writes a local snapshot under `data/market_data/snapshots/`.

### Current Test Coverage

The current regression tests validate a narrow but high-value subset of invariants:

- chronological observation enrichment without lookahead
- strict rejection when critical identifiers or decision inputs are missing
- exposure-cap enforcement at decision time
- odds-aware settled PnL and no realized PnL for unresolved trades

## Architecture

### Main Modules

- `market_data/`: snapshot collection, normalization, storage, and dataset export helpers.
- `live_adapters/`: conversion of raw price events into chronological rolling observations.
- `market_scanner/` and `market_signals/`: anomaly detection and simple market-path signal helpers.
- `core/` and `decision_pipeline/`: shared fair-value, signal, risk, and trade-intent logic.
- `pipeline/`: compatibility wrapper over the shared decision core for legacy strategy callers.
- `strategy/`, `backtesting/`, `paper_trading/`: offline strategy evaluation and settled paper-trading helpers.
- `live_paper_trading/` and `orchestrator/`: batch-style evaluation flows for unresolved and optionally settled live-like data.
- `analytics/`: performance summaries and deterministic portfolio metrics.
- `agents/`: lightweight external research-agent helpers and schemas.

### Data Flow

1. Raw market data enters through `market_data/` or `live_adapters/`.
2. `live_adapters/` builds chronological observations using only previously seen market points.
3. `market_scanner/` detects probability divergences and converts them into shared `DecisionInput` objects.
4. `decision_pipeline/` applies fair-value estimation, signal generation, risk gating, and trade-intent construction.
5. Trade intents are consumed by backtesting, paper-trading, or live batch runners, and summarized by `analytics/`.

## Current Capabilities

- Deterministic market snapshot collection with normalization and JSONL export helpers.
- Shared decision pipeline with strict rejection of missing critical identifiers and inputs.
- Exposure-aware risk approval using `current_exposure + proposed_size <= max_total_exposure`.
- Odds-aware settled PnL in offline backtesting and paper-trading flows.
- Live batch evaluation that avoids synthetic settlement and only realizes PnL when real outcomes are supplied.
- Compatibility support for the legacy `pipeline/` entrypoints through the shared decision core.
- Basic unit regression coverage for recent safety hardening.

## Known Limitations

- The live anomaly path still relies on a simple rolling market-derived reference; it is a safer prototype implementation, not a calibrated external pricing model.
- There is no order manager, exchange connector, persistent position store, or operational monitoring stack.
- Snapshot persistence is file-based JSONL and is not suitable for concurrent or large-scale ingestion.
- Automated test coverage exists but remains narrow and focused on the recent remediation pass.
- CI coverage is intentionally minimal and currently validates only installation, unit tests, and a deterministic local smoke path.

## Roadmap

- Lock and document a contributor workflow beyond the current minimal editable-install setup.
- Introduce explicit external reference/model inputs for live-path evaluation instead of relying on rolling market-only projections.
- Add persistent position and order-state management with replayable state transitions.
- Replace JSONL snapshot storage with a durable backend appropriate for concurrent ingestion and replay.
- Expand tests from unit coverage to integration, replay, and stress scenarios.
