from __future__ import annotations

import pandas as pd

try:
    from qlib.contrib.strategy.order_generator import OrderGenWInteract
    from qlib.contrib.strategy.signal_strategy import WeightStrategyBase
except ImportError:  # pragma: no cover
    OrderGenWInteract = None  # type: ignore[assignment]
    WeightStrategyBase = object  # type: ignore[assignment,misc]


def equal_weight_targets(score: pd.Series | pd.DataFrame, top_k: int) -> dict[str, float]:
    if isinstance(score, pd.DataFrame):
        if score.shape[1] != 1:
            raise ValueError("target strategy accepts one score column")
        score = score.iloc[:, 0]
    clean = score.dropna().astype(float).sort_values(ascending=False, kind="stable")
    selected = clean.head(int(top_k))
    if selected.empty:
        return {}
    weight = 1.0 / len(selected)
    return {str(instrument): weight for instrument in selected.index}


class PeriodicEqualWeightSelector:
    """Freeze a Top-K target between deterministic execution-date rebalances."""

    def __init__(self, *, top_k: int, rebalance_interval: int) -> None:
        self.top_k = int(top_k)
        self.rebalance_interval = int(rebalance_interval)
        if self.rebalance_interval <= 0:
            raise ValueError("rebalance_interval must be positive")
        self.execution_dates: list[pd.Timestamp] = []
        self.last_target: dict[str, float] = {}

    def select(
        self, score: pd.Series | pd.DataFrame, execution_date: object
    ) -> dict[str, float] | None:
        normalized = pd.Timestamp(execution_date).normalize()
        if not self.execution_dates or self.execution_dates[-1] != normalized:
            self.execution_dates.append(normalized)
        step = len(self.execution_dates) - 1
        if not self.last_target or step % self.rebalance_interval == 0:
            self.last_target = equal_weight_targets(score, self.top_k)
            return dict(self.last_target)
        return None


class EqualWeightTargetStrategy(WeightStrategyBase):  # type: ignore[misc]
    def __init__(
        self,
        *,
        top_k: int,
        rebalance_interval: int = 1,
        **kwargs: object,
    ) -> None:
        if OrderGenWInteract is None:
            raise ImportError("pyqlib is required for EqualWeightTargetStrategy")
        self.top_k = int(top_k)
        self.rebalance_interval = int(rebalance_interval)
        if self.rebalance_interval <= 0:
            raise ValueError("rebalance_interval must be positive")
        self._selector = PeriodicEqualWeightSelector(
            top_k=self.top_k,
            rebalance_interval=self.rebalance_interval,
        )
        super().__init__(order_generator_cls_or_obj=OrderGenWInteract, **kwargs)

    def generate_target_weight_position(self, score: pd.Series, current: object, trade_start_time: object, trade_end_time: object) -> dict[str, float] | None:
        del current, trade_end_time
        return self._selector.select(score, trade_start_time)


def rebalance_execution_dates(
    execution_dates: pd.DatetimeIndex, interval: int
) -> pd.DatetimeIndex:
    """Return the frozen 0, N, 2N... execution-date schedule."""

    dates = pd.DatetimeIndex(execution_dates).normalize()
    if interval <= 0:
        raise ValueError("rebalance interval must be positive")
    if dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("execution dates must be unique and sorted")
    return dates[:: int(interval)]
