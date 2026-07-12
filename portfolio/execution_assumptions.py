from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionAssumptions:
    lot_size: int = 100
    buy_commission_rate: float = 0.0003
    sell_commission_rate: float = 0.0003
    sell_tax_rate: float = 0.001
    minimum_commission: float = 5.0
    slippage_bps: float = 10.0
    max_participation_rate: float = 0.05
    top_k: int = 50
    rebalance_every: int = 20
    initial_cash: float = 10_000_000.0
