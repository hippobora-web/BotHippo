"""Deterministic fixed-interval runtime loop for live paper trading."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, is_dataclass
from importlib import import_module
import time
from typing import Any

from evengine.runtime.types import RuntimeConfig, RuntimeResult


_EVENT_INPUT_FIELDS: tuple[str, ...] = (
    "event_id",
    "sport",
    "competition",
    "home_team",
    "away_team",
    "market_type",
    "selection",
    "odds",
    "bookmaker",
    "timestamp",
)

_PIPELINE_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("evengine.runner", "run_live_paper_trading_pipeline"),
    ("evengine.runner", "run_live_paper_pipeline"),
    ("evengine.paper_trading.runner", "run_live_paper_trading_pipeline"),
    ("evengine.paper_trading.runner", "run_live_paper_pipeline"),
)


def _load_callable(module_name: str, callable_name: str) -> Callable[..., Any] | None:
    """Load a callable defensively from a module path."""

    try:
        module = import_module(module_name)
    except Exception:
        return None

    candidate: Any = getattr(module, callable_name, None)
    return candidate if callable(candidate) else None


def _load_live_paper_pipeline() -> Callable[[list[Any]], Any] | None:
    """Return a repository-native live paper pipeline when one exists."""

    for module_name, callable_name in _PIPELINE_CANDIDATES:
        candidate = _load_callable(module_name, callable_name)
        if candidate is not None:
            return candidate
    return None


def _get_value(payload: Any, *names: str) -> Any:
    """Read the first present field from a mapping or object."""

    for name in names:
        if isinstance(payload, Mapping) and name in payload:
            return payload[name]
        if hasattr(payload, name):
            return getattr(payload, name)
    return None


def _coerce_float(value: Any) -> float | None:
    """Convert a runtime metric to float when possible."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    """Convert a runtime metric to int when possible."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_payload(raw_price: Any) -> dict[str, Any]:
    """Normalize raw provider output into a dict-like payload."""

    if isinstance(raw_price, Mapping):
        return dict(raw_price)

    model_dump = getattr(raw_price, "model_dump", None)
    if callable(model_dump):
        dumped: Any = model_dump()
        if isinstance(dumped, Mapping):
            return dict(dumped)

    if is_dataclass(raw_price):
        return asdict(raw_price)

    payload: dict[str, Any] = {}
    for field_name in _EVENT_INPUT_FIELDS:
        if hasattr(raw_price, field_name):
            payload[field_name] = getattr(raw_price, field_name)
    return payload


def _coerce_event_input(raw_price: Any) -> Any:
    """Convert a raw provider item into the repository EventInput schema."""

    from evengine.agents.schemas import EventInput

    if isinstance(raw_price, EventInput):
        return raw_price

    payload: dict[str, Any] = _to_payload(raw_price)
    missing_fields: list[str] = [field_name for field_name in _EVENT_INPUT_FIELDS if field_name not in payload]
    if missing_fields:
        missing: str = ", ".join(missing_fields)
        raise ValueError(f"raw price payload is missing EventInput fields: {missing}")

    event_payload: dict[str, Any] = {field_name: payload[field_name] for field_name in _EVENT_INPUT_FIELDS}
    return EventInput(**event_payload)


def _trade_totals_from_ticket(ticket: Any) -> tuple[int, float]:
    """Extract deterministic trade count and pnl from one ticket-like output."""

    explicit_pnl: float | None = _coerce_float(
        _get_value(ticket, "pnl", "profit_loss", "realized_pnl", "expected_pnl", "total_pnl")
    )
    explicit_trades: int | None = _coerce_int(
        _get_value(ticket, "total_trades", "trade_count", "trades", "n_trades")
    )
    if explicit_pnl is not None and explicit_trades is not None:
        return explicit_trades, explicit_pnl

    allowed_value: Any = _get_value(ticket, "risk_allowed", "allowed", "executed", "filled")
    decision_value: Any = _get_value(ticket, "decision", "action")

    is_trade: bool
    if allowed_value is not None:
        is_trade = bool(allowed_value)
    elif isinstance(decision_value, str):
        is_trade = decision_value.strip().upper() == "BET"
    else:
        is_trade = False

    if not is_trade:
        return 0, 0.0

    if explicit_pnl is not None:
        return 1, explicit_pnl

    stake: float | None = _coerce_float(
        _get_value(ticket, "recommended_stake_eur", "stake_eur", "stake", "stake_amount")
    )
    ev: float | None = _coerce_float(_get_value(ticket, "ev", "expected_value"))
    if stake is not None and ev is not None:
        return 1, stake * ev

    return 1, 0.0


def _totals_from_pipeline_output(output: Any) -> tuple[int, float]:
    """Reduce pipeline output to aggregate trade count and pnl."""

    if output is None:
        return 0, 0.0

    aggregate_trades: int | None = _coerce_int(_get_value(output, "total_trades", "trade_count", "n_trades"))
    aggregate_pnl: float | None = _coerce_float(
        _get_value(output, "total_pnl", "pnl", "profit_loss", "realized_pnl", "expected_pnl")
    )
    if aggregate_trades is not None and aggregate_pnl is not None:
        return aggregate_trades, aggregate_pnl

    nested_results: Any = _get_value(output, "tickets", "trade_results", "results", "trades")
    if isinstance(nested_results, Iterable) and not isinstance(nested_results, (str, bytes, Mapping)):
        total_trades: int = 0
        total_pnl: float = 0.0
        for item in nested_results:
            item_trades, item_pnl = _totals_from_pipeline_output(item)
            total_trades += item_trades
            total_pnl += item_pnl
        return total_trades, total_pnl

    if isinstance(output, tuple) and len(output) == 2:
        maybe_trades: int | None = _coerce_int(output[0])
        maybe_pnl: float | None = _coerce_float(output[1])
        if maybe_trades is not None and maybe_pnl is not None:
            return maybe_trades, maybe_pnl

    if isinstance(output, Iterable) and not isinstance(output, (str, bytes, Mapping)):
        total_trades = 0
        total_pnl = 0.0
        for item in output:
            item_trades, item_pnl = _totals_from_pipeline_output(item)
            total_trades += item_trades
            total_pnl += item_pnl
        return total_trades, total_pnl

    return _trade_totals_from_ticket(output)


def _run_supervisor_cycle(raw_prices: list[Any]) -> tuple[int, float]:
    """Run the checked-in agent supervisor once for each raw market price."""

    from evengine.agents.supervisor import run_pipeline

    total_trades: int = 0
    total_pnl: float = 0.0
    for raw_price in raw_prices:
        ticket_output: Any = run_pipeline(_coerce_event_input(raw_price))
        item_trades, item_pnl = _trade_totals_from_ticket(ticket_output)
        total_trades += item_trades
        total_pnl += item_pnl
    return total_trades, total_pnl


def _run_live_paper_cycle(raw_prices: list[Any]) -> tuple[int, float]:
    """Run one live paper-trading cycle and normalize its aggregates."""

    pipeline = _load_live_paper_pipeline()
    if pipeline is None:
        return _run_supervisor_cycle(raw_prices)
    return _totals_from_pipeline_output(pipeline(raw_prices))


def _normalize_prices(raw_prices: Any) -> list[Any]:
    """Normalize provider output to a concrete list."""

    if raw_prices is None:
        return []
    if isinstance(raw_prices, list):
        return raw_prices
    return list(raw_prices)


def run_runtime_loop(
    config: RuntimeConfig,
    raw_price_provider: Callable[[], list[Any]],
) -> RuntimeResult:
    """Continuously run the live paper-trading pipeline at fixed intervals."""

    if not callable(raw_price_provider):
        raise TypeError("raw_price_provider must be callable")

    cycles_run: int = 0
    total_trades: int = 0
    total_pnl: float = 0.0

    while config.max_cycles is None or cycles_run < config.max_cycles:
        raw_prices: list[Any] = _normalize_prices(raw_price_provider())
        if not raw_prices:
            break

        cycle_trades, cycle_pnl = _run_live_paper_cycle(raw_prices)
        cycles_run += 1
        total_trades += cycle_trades
        total_pnl += cycle_pnl

        if config.max_cycles is not None and cycles_run >= config.max_cycles:
            break
        time.sleep(config.interval_seconds)

    return RuntimeResult(
        cycles_run=cycles_run,
        total_trades=total_trades,
        total_pnl=total_pnl,
    )
