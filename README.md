# BotHippo

## Disclaimer

BotHippo is a research prototype. It is not production-ready, is not safe for unattended live trading, and should not be used to place real-money wagers or orders without a full production hardening pass.

The current codebase is designed to be explicit about missing data and unresolved outcomes:

- Missing critical identifiers or decision inputs now produce `reject` decisions.
- Live and orchestration flows no longer invent synthetic settlement outcomes.
- Legacy `pipeline/*` entrypoints now delegate to the shared `decision_pipeline/*` core so there is one decision source of truth.

## Architecture Overview

The repository is organized as a small deterministic research engine:

- `market_data/`: snapshot collection, storage, normalization, and dataset export helpers.
- `live_adapters/` and `market_scanner/`: raw market-price conversion, rolling observation enrichment, and anomaly detection.
- `core/` and `decision_pipeline/`: shared fair-value, signal, risk, and trade-intent logic.
- `pipeline/`: compatibility wrapper around the shared decision core for older strategy callers.
- `strategy/`, `backtesting/`, `paper_trading/`: offline research and backtest helpers.
- `live_paper_trading/` and `orchestrator/`: batch-style live research flows that can emit candidate trades and settle them only when real outcomes are supplied.
- `agents/`: external research-agent helpers and schema definitions.

## Prototype Safety Notes

- Market observations are processed chronologically and use only previously seen prices for rolling reference generation.
- Exposure approval now requires `current_exposure + proposed_size <= max_total_exposure`.
- Odds-aware PnL uses stake-based decimal odds derived from market implied probability.
- Unsettled trades remain unresolved and do not contribute synthetic PnL.

## Running Tests

```bash
python3 -m unittest discover -s tests
```

## Current Limitations

- Live anomaly detection still uses a simple deterministic rolling price reference. It is safer than the prior lookahead implementation, but it is still a prototype signal model.
- There is no real order manager, exchange connector, persistent position store, or monitoring stack.
- Snapshot storage remains file-based JSONL and is not suitable for concurrent production ingestion.
