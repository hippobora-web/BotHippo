# Changelog

All notable changes to this repository should be documented in this file.

## 2026-03-10

### Public Hardening Release

Commit: `26ec7b0` (`chore: harden research prototype for public release`)

- added strict shared-core validation for missing critical identifiers, probabilities, confidence, liquidity, and exposure inputs
- removed lookahead from the live observation enrichment path by processing market events chronologically
- corrected exposure approval to account for `current_exposure + proposed_size`
- stopped synthetic settlement in live/orchestrator flows and limited realized PnL to explicitly settled outcomes
- made offline paper-trading and backtesting PnL odds-aware
- routed legacy `pipeline/` execution through the shared `decision_pipeline/` source of truth
- replaced raw payload `print` calls with structured redacted logging in the agent supervisor
- added targeted regression tests and a public-facing README suitable for a research prototype
