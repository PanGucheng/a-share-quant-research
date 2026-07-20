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


class EqualWeightTargetStrategy(WeightStrategyBase):  # type: ignore[misc]
    def __init__(self, *, top_k: int, **kwargs: object) -> None:
        if OrderGenWInteract is None:
            raise ImportError("pyqlib is required for EqualWeightTargetStrategy")
        self.top_k = int(top_k)
        super().__init__(order_generator_cls_or_obj=OrderGenWInteract, **kwargs)

    def generate_target_weight_position(self, score: pd.Series, current: object, trade_start_time: object, trade_end_time: object) -> dict[str, float]:
        del current, trade_start_time, trade_end_time
        return equal_weight_targets(score, self.top_k)
