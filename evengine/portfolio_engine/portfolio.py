"""Deterministic portfolio update and metric helpers."""

from __future__ import annotations

from evengine.portfolio_engine.types import PortfolioMetrics, PortfolioState
from evengine.trade_execution_sim.types import TradePnL


def update_portfolio(
    state: PortfolioState,
    trade_pnl: TradePnL,
) -> PortfolioState:
    """Return an updated portfolio state after applying one trade PnL event."""

    updated_balance: float = state.balance + trade_pnl.pnl
    updated_pnl_history: list[float] = [*state.pnl_history, trade_pnl.pnl]
    updated_wins: int = state.wins + (1 if trade_pnl.pnl > 0.0 else 0)
    updated_losses: int = state.losses + (1 if trade_pnl.pnl < 0.0 else 0)
    return PortfolioState(
        balance=updated_balance,
        trades=state.trades + 1,
        wins=updated_wins,
        losses=updated_losses,
        pnl_history=updated_pnl_history,
    )



def _infer_initial_balance(state: PortfolioState) -> float:
    """Infer initial balance from current balance and accumulated PnL history."""

    return state.balance - sum(state.pnl_history)



def _compute_max_drawdown(state: PortfolioState) -> float:
    """Compute deterministic maximum drawdown from inferred equity evolution."""

    if not state.pnl_history:
        return 0.0

    initial_balance: float = _infer_initial_balance(state)
    equity: float = initial_balance
    peak: float = equity
    max_drawdown: float = 0.0

    for pnl in state.pnl_history:
        equity += pnl
        if equity > peak:
            peak = equity
        if peak > 0.0:
            drawdown: float = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

    return max_drawdown



def compute_portfolio_metrics(state: PortfolioState) -> PortfolioMetrics:
    """Compute aggregate deterministic portfolio metrics from a portfolio state."""

    total_pnl: float = sum(state.pnl_history)
    initial_balance: float = _infer_initial_balance(state)
    roi: float = total_pnl / initial_balance if initial_balance != 0.0 else 0.0
    win_rate: float = state.wins / state.trades if state.trades > 0 else 0.0
    max_drawdown: float = _compute_max_drawdown(state)
    return PortfolioMetrics(
        total_pnl=total_pnl,
        roi=roi,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
    )
