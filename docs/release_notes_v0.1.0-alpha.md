# v0.1.0-alpha Draft

## Suggested GitHub Metadata

Suggested repository description:

`Deterministic research prototype for event-market data collection, decision-pipeline experiments, and paper-trading evaluation.`

Suggested GitHub topics:

- `python`
- `research-prototype`
- `event-markets`
- `market-data`
- `decision-engine`
- `backtesting`
- `paper-trading`
- `quant-research`

These settings are repository metadata, not versioned source. Set them in the GitHub UI or via the GitHub API after review.

## Draft Release Title

`v0.1.0-alpha: public research prototype baseline`

## Draft Release Notes

First public alpha release of BotHippo / EVEngine as a research prototype.

Included in this release:

- deterministic market snapshot collection and JSONL export helpers
- shared decision pipeline with strict validation for critical identifiers and inputs
- chronological observation enrichment without lookahead in the live-path adapter layer
- exposure-aware risk approval using `current_exposure + proposed_size <= max_total_exposure`
- settlement-aware and odds-aware PnL handling in paper-trading and execution simulation
- targeted regression coverage for core decision, persistence, and state-sequencing invariants
- minimal reproducible setup with `pyproject.toml`, README install steps, and basic GitHub Actions CI

Known limitations:

- research prototype only; not production-ready and not suitable for real-money deployment
- live anomaly detection still uses a simple rolling market-derived reference, not a calibrated external pricing model
- persistence is append-only JSONL and is not suitable for concurrent ingestion or large-scale runtime use
- CI and automated test coverage remain intentionally narrow
