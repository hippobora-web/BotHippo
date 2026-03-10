"""Deterministic backtest engine connecting strategy and paper-trading layers."""

from __future__ import annotations

from evengine.backtesting.backtest_types import BacktestResult
from evengine.paper_trading.portfolio import PaperPortfolio
from evengine.paper_trading.simulator import simulate_trades
from evengine.paper_trading.trade_types import TradeDecision, TradeResult
from evengine.strategy.strategy_engine import run_strategy_dataset
from evengine.strategy.strategy_types import StrategyDecision, StrategyInput


def _to_trade_decision(decision: StrategyDecision) -> TradeDecision:
    """Convert a strategy decision into a paper-trading decision."""

    return TradeDecision(
        asset_class=decision.asset_class,
        decision=decision.decision,
        size=decision.size,
        edge=decision.edge,
        entry_probability=decision.market_implied_probability,
    )


def run_backtest(
    dataset_rows: list[StrategyInput],
    outcomes: list[bool],
    initial_balance: float,
) -> BacktestResult:
    """Run a deterministic backtest over strategy inputs and boolean outcomes."""

    strategy_decisions: list[StrategyDecision] = run_strategy_dataset(dataset_rows)
    trade_decisions: list[TradeDecision] = [_to_trade_decision(decision) for decision in strategy_decisions]
    trade_results: list[TradeResult] = simulate_trades(trade_decisions, outcomes)

    portfolio = PaperPortfolio(starting_balance=initial_balance)
    for trade_result in trade_results:
        portfolio.apply_trade(trade_result)

    n_trades: int = sum(1 for decision in trade_decisions if decision.decision == "bet")
    n_wins: int = sum(
        1
        for decision, result in zip(trade_decisions, trade_results)
        if decision.decision == "bet" and result.outcome
    )
    n_losses: int = sum(
        1
        for decision, result in zip(trade_decisions, trade_results)
        if decision.decision == "bet" and not result.outcome
    )

    return BacktestResult(
        final_balance=portfolio.balance,
        total_pnl=portfolio.compute_total_pnl(),
        n_trades=n_trades,
        n_wins=n_wins,
        n_losses=n_losses,
        equity_curve=portfolio.compute_equity_curve(),
    )
