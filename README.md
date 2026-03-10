# EVEngine

EVEngine is a deterministic research prototype for event-market data collection, signal generation, risk gating, backtesting, and paper-trading experiments.

## Disclaimer

This repository is for research and prototyping only. It is not production-ready and is not suitable for unattended live trading, exchange connectivity, or real-money use.

Recent hardening work improved validation, exposure controls, and settlement handling, but the repository still lacks the operational controls required for production deployment.

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

## Running Tests

```bash
python3 -m unittest discover -s tests
```

## Known Limitations

- The live anomaly path still relies on a simple rolling market-derived reference; it is a safer prototype implementation, not a calibrated external pricing model.
- There is no order manager, exchange connector, persistent position store, or operational monitoring stack.
- Snapshot persistence is file-based JSONL and is not suitable for concurrent or large-scale ingestion.
- Automated test coverage exists but remains narrow and focused on the recent remediation pass.
- No CI workflow is committed in the repository yet, so there is no public test badge to expose.

## Roadmap

- Add reproducible Python project metadata and a minimal CI workflow for test execution.
- Introduce explicit external reference/model inputs for live-path evaluation instead of relying on rolling market-only projections.
- Add persistent position and order-state management with replayable state transitions.
- Replace JSONL snapshot storage with a durable backend appropriate for concurrent ingestion and replay.
- Expand tests from unit coverage to integration, replay, and stress scenarios.
