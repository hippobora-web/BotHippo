"""Safe adapter for optional integration with a real quant engine."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Callable

from evengine.agents.config import REAL_QUANT_ENGINE_IMPORT_PATH, USE_REAL_QUANT_ENGINE
from evengine.agents.schemas import QuantAgentMetadata, QuantDecision


_LAST_REAL_ENGINE_STATUS: str = "real_engine_native_unavailable"
_LAST_REAL_ENGINE_SOURCE: str = ""

_NATIVE_REAL_ENGINE_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("evengine.runner", "run_decision_engine"),
    ("evengine.runner", "run_decision"),
    ("evengine.runner", "run"),
    ("evengine.signals.runner", "run_decision_engine"),
    ("evengine.signals.runner", "run_decision"),
    ("evengine.signals.runner", "run"),
    ("evengine.signals.fusion", "run_decision_engine"),
    ("evengine.signals.fusion", "run_fusion"),
    ("evengine.signals.decision", "run_decision"),
)


def _set_status(status: str, source: str = "") -> None:
    """Persist adapter status for downstream fallback classification."""

    global _LAST_REAL_ENGINE_STATUS
    global _LAST_REAL_ENGINE_SOURCE
    _LAST_REAL_ENGINE_STATUS = status
    _LAST_REAL_ENGINE_SOURCE = source


def get_last_real_engine_status() -> str:
    """Return last adapter status for quant fallback reasoning."""

    return _LAST_REAL_ENGINE_STATUS


def _parse_import_path(import_path: str) -> tuple[str, str] | None:
    """Parse import path in `module:function` or `module.function` format."""

    path: str = import_path.strip()
    if not path:
        return None

    if ":" in path:
        module_name, callable_name = path.split(":", 1)
    else:
        module_name, sep, callable_name = path.rpartition(".")
        if not sep:
            return None

    module_name = module_name.strip()
    callable_name = callable_name.strip()
    if not module_name or not callable_name:
        return None
    return module_name, callable_name


def _load_callable(module_name: str, callable_name: str) -> Callable[..., Any] | None:
    """Load a callable from module path defensively."""

    try:
        module = import_module(module_name)
    except Exception:
        return None

    candidate: Any = getattr(module, callable_name, None)
    return candidate if callable(candidate) else None


def _load_native_real_quant_callable() -> Callable[..., Any] | None:
    """Try loading a repository-native real quant callable."""

    saw_native_module: bool = False
    for module_name, callable_name in _NATIVE_REAL_ENGINE_CANDIDATES:
        try:
            module = import_module(module_name)
        except Exception:
            continue

        saw_native_module = True
        candidate: Any = getattr(module, callable_name, None)
        if callable(candidate):
            _set_status("real_engine_native_available", "native")
            return candidate

    if saw_native_module:
        _set_status("real_engine_native_incompatible", "native")
    else:
        _set_status("real_engine_native_unavailable", "native")
    return None


def _load_env_real_quant_callable() -> Callable[..., Any] | None:
    """Try loading a real quant callable from configured import path."""

    parsed_path: tuple[str, str] | None = _parse_import_path(REAL_QUANT_ENGINE_IMPORT_PATH)
    if parsed_path is None:
        if _LAST_REAL_ENGINE_STATUS not in {
            "real_engine_native_unavailable",
            "real_engine_native_incompatible",
        }:
            _set_status("real_engine_import_unavailable", "env")
        return None

    module_name, callable_name = parsed_path
    candidate: Callable[..., Any] | None = _load_callable(module_name, callable_name)
    if candidate is None:
        _set_status("real_engine_import_unavailable", "env")
        return None

    _set_status("real_engine_import_available", "env")
    return candidate


def load_real_quant_callable() -> Callable[..., Any] | None:
    """Load real quant callable with native-first then env-path fallback."""

    if not USE_REAL_QUANT_ENGINE:
        _set_status("real_engine_disabled")
        return None

    native_candidate: Callable[..., Any] | None = _load_native_real_quant_callable()
    if native_candidate is not None:
        return native_candidate

    env_candidate: Callable[..., Any] | None = _load_env_real_quant_callable()
    if env_candidate is not None:
        return env_candidate

    return None


def _to_float(value: Any) -> float | None:
    """Convert value to float when possible."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_str_list(value: Any) -> list[str]:
    """Normalize potential flags payload into list of strings."""

    if isinstance(value, str):
        stripped: str = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped: str = item.strip()
                if stripped:
                    result.append(stripped)
        return result
    return []


def _pick(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return first non-null value among candidate keys."""

    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _normalize_decision(payload: dict[str, Any]) -> str | None:
    """Extract and normalize decision label."""

    decision_value: Any = _pick(payload, ("decision", "action", "verdict", "status"))
    if decision_value is None and "bettable" in payload:
        bettable: Any = payload.get("bettable")
        if isinstance(bettable, bool):
            return "BET" if bettable else "REJECT"
        if isinstance(bettable, (int, float)):
            return "BET" if bool(bettable) else "REJECT"

    if not isinstance(decision_value, str):
        return None

    normalized: str = decision_value.strip().upper()
    mapping: dict[str, str] = {
        "NO_BET": "REJECT",
        "PASS": "WATCH",
        "SKIP": "WATCH",
    }
    normalized = mapping.get(normalized, normalized)
    return normalized if normalized in {"BET", "WATCH", "REJECT"} else None


def _build_real_metadata(payload: dict[str, Any]) -> QuantAgentMetadata:
    """Build QuantAgentMetadata from real-engine payload."""

    raw_metadata: Any = _pick(payload, ("metadata", "quant_metadata"))
    if isinstance(raw_metadata, QuantAgentMetadata):
        metadata: QuantAgentMetadata = raw_metadata
        if metadata.engine_mode and metadata.used_real_engine == 1 and metadata.fallback_reason == "":
            return metadata

    if isinstance(raw_metadata, dict):
        try:
            metadata = QuantAgentMetadata(**raw_metadata)
            if metadata.engine_mode and metadata.used_real_engine == 1 and metadata.fallback_reason == "":
                return metadata
        except Exception:
            pass

    baseline_quality: Any = _pick(payload, ("baseline_quality",))
    coverage_level: Any = _pick(payload, ("coverage_level",))
    extra_flags: list[str] = _to_str_list(_pick(payload, ("extra_flags", "flags")))

    return QuantAgentMetadata(
        engine_mode="real",
        used_real_engine=1,
        fallback_reason="",
        baseline_quality=str(baseline_quality) if baseline_quality is not None else "",
        coverage_level=str(coverage_level) if coverage_level is not None else "",
        extra_flags=extra_flags,
    )


def _coerce_payload_to_quant_decision(
    *,
    payload: dict[str, Any],
    event_id: str,
    market_snapshot: Any,
) -> QuantDecision | None:
    """Coerce dict payload into QuantDecision with safe derivations."""

    decision: str | None = _normalize_decision(payload)
    if decision is None:
        return None

    implied_probability: float | None = _to_float(
        _pick(payload, ("implied_probability", "implied_prob", "market_implied_probability"))
    )
    market_implied: float | None = _to_float(getattr(market_snapshot, "implied_probability", None))
    if implied_probability is None:
        implied_probability = market_implied

    model_probability: float | None = _to_float(
        _pick(
            payload,
            (
                "model_probability",
                "model_prob",
                "fair_probability",
                "fair_prob",
                "probability",
            ),
        )
    )
    edge: float | None = _to_float(_pick(payload, ("edge", "expected_edge", "value_edge")))
    ev: float | None = _to_float(_pick(payload, ("ev", "expected_value", "value")))

    odds: float | None = _to_float(getattr(market_snapshot, "odds", None))

    if model_probability is None and implied_probability is not None and edge is not None:
        model_probability = implied_probability + edge
    if model_probability is None and ev is not None and odds not in (None, 0.0):
        model_probability = (ev + 1.0) / float(odds)
    if model_probability is None:
        return None

    model_probability = max(0.01, min(0.99, model_probability))

    if implied_probability is None:
        if edge is not None:
            implied_probability = model_probability - edge
        else:
            implied_probability = market_implied if market_implied is not None else model_probability

    if edge is None:
        edge = model_probability - implied_probability
    if ev is None:
        if odds is None:
            return None
        ev = (odds * model_probability) - 1.0

    metadata: QuantAgentMetadata = _build_real_metadata(payload)

    return QuantDecision(
        event_id=str(_pick(payload, ("event_id",)) or event_id),
        decision=decision,
        model_probability=model_probability,
        implied_probability=implied_probability,
        edge=edge,
        ev=ev,
        metadata=metadata,
    )


def _coerce_real_output_to_quant_decision(
    *,
    raw_result: Any,
    event_id: str,
    market_snapshot: Any,
) -> QuantDecision | None:
    """Coerce arbitrary real-engine output into QuantDecision."""

    if isinstance(raw_result, QuantDecision):
        decision: QuantDecision = raw_result
        if decision.metadata is None:
            decision = decision.model_copy(
                update={
                    "metadata": QuantAgentMetadata(
                        engine_mode="real",
                        used_real_engine=1,
                        fallback_reason="",
                    )
                }
            )
        return decision

    payload: dict[str, Any] | None = None
    if isinstance(raw_result, dict):
        payload = raw_result
    elif hasattr(raw_result, "model_dump") and callable(getattr(raw_result, "model_dump")):
        try:
            dumped: Any = raw_result.model_dump()
            if isinstance(dumped, dict):
                payload = dumped
        except Exception:
            payload = None
    elif hasattr(raw_result, "__dict__"):
        try:
            candidate: Any = vars(raw_result)
            if isinstance(candidate, dict):
                payload = candidate
        except Exception:
            payload = None

    if payload is None:
        return None

    return _coerce_payload_to_quant_decision(
        payload=payload,
        event_id=event_id,
        market_snapshot=market_snapshot,
    )


def _execute_quant_callable(
    *,
    quant_callable: Callable[..., Any],
    source: str,
    event_id: str,
    market_snapshot: Any,
    quant_features: Any,
) -> QuantDecision | None:
    """Execute one quant callable and coerce result to QuantDecision."""

    try:
        raw_result: Any = quant_callable(
            event_id=event_id,
            market_snapshot=market_snapshot,
            quant_features=quant_features,
        )
    except TypeError:
        if source == "native":
            _set_status("real_engine_native_incompatible", "native")
        else:
            _set_status("real_engine_execution_failed", source)
        return None
    except Exception:
        _set_status("real_engine_execution_failed", source)
        return None

    decision: QuantDecision | None = _coerce_real_output_to_quant_decision(
        raw_result=raw_result,
        event_id=event_id,
        market_snapshot=market_snapshot,
    )
    if decision is None:
        _set_status("real_engine_invalid_output", source)
        return None

    _set_status("real_engine_used", source)
    return decision


def run_real_quant_if_available(
    *,
    event_id: str,
    market_snapshot: Any,
    quant_features: Any,
) -> QuantDecision | None:
    """Run real quant engine when configured and return a validated decision."""

    quant_callable: Callable[..., Any] | None = load_real_quant_callable()
    if quant_callable is None:
        return None

    initial_source: str = _LAST_REAL_ENGINE_SOURCE
    decision: QuantDecision | None = _execute_quant_callable(
        quant_callable=quant_callable,
        source=initial_source or "unknown",
        event_id=event_id,
        market_snapshot=market_snapshot,
        quant_features=quant_features,
    )
    if decision is not None:
        return decision

    if initial_source == "native" and _LAST_REAL_ENGINE_STATUS in {
        "real_engine_native_incompatible",
        "real_engine_invalid_output",
    }:
        env_callable: Callable[..., Any] | None = _load_env_real_quant_callable()
        if env_callable is not None:
            return _execute_quant_callable(
                quant_callable=env_callable,
                source="env",
                event_id=event_id,
                market_snapshot=market_snapshot,
                quant_features=quant_features,
            )

    return None
