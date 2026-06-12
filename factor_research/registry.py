from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class FactorSpec:
    name: str
    category: str
    expected_direction: str
    dependencies: tuple[str, ...]
    description: str
    labels: tuple[str, ...] = ("label_10d_t1", "label_20d_t1")
    enabled: bool = True

    @property
    def direction_sign(self) -> int | None:
        return {"positive": 1, "negative": -1}.get(self.expected_direction)


FACTOR_SPECS = [
    FactorSpec(
        name="ret_5",
        category="momentum",
        expected_direction="watch",
        dependencies=("$close",),
        description="5-day return; mainly used to diagnose short-term trend or reversal exposure.",
    ),
    FactorSpec(
        name="ret_10",
        category="momentum",
        expected_direction="watch",
        dependencies=("$close",),
        description="10-day return; medium short-term momentum diagnostic.",
    ),
    FactorSpec(
        name="ret_20",
        category="momentum",
        expected_direction="watch",
        dependencies=("$close",),
        description="20-day return; medium-term momentum and drawdown exposure diagnostic.",
    ),
    FactorSpec(
        name="rev_5",
        category="reversal",
        expected_direction="positive",
        dependencies=("$close",),
        description="Negative 5-day return; short-term reversal score.",
    ),
    FactorSpec(
        name="std_20",
        category="risk",
        expected_direction="negative",
        dependencies=("$close",),
        description="20-day return volatility; lower volatility is expected to be better.",
    ),
    FactorSpec(
        name="amplitude_20",
        category="risk",
        expected_direction="negative",
        dependencies=("$high", "$low", "$close"),
        description="20-day average intraday range; lower range is expected to be better.",
    ),
    FactorSpec(
        name="amount_mean_20",
        category="liquidity",
        expected_direction="watch",
        dependencies=("$amount",),
        description="20-day average trading amount; primarily a tradability and exposure diagnostic.",
    ),
    FactorSpec(
        name="amount_std_20",
        category="liquidity",
        expected_direction="watch",
        dependencies=("$amount",),
        description="20-day trading amount volatility; liquidity stability diagnostic.",
    ),
    FactorSpec(
        name="volume_ratio_5_20",
        category="liquidity",
        expected_direction="watch",
        dependencies=("$volume",),
        description="5-day volume average divided by 20-day volume average.",
    ),
    FactorSpec(
        name="corr_ret_volume_20",
        category="price_volume",
        expected_direction="watch",
        dependencies=("$close", "$volume"),
        description="20-day rolling correlation between daily return and volume.",
    ),
]


def enabled_specs(labels: list[str] | tuple[str, ...] | None = None) -> list[FactorSpec]:
    specs = [spec for spec in FACTOR_SPECS if spec.enabled]
    if labels is None:
        return specs
    label_set = set(labels)
    return [spec for spec in specs if label_set & set(spec.labels)]


def registry_frame(specs: list[FactorSpec] | None = None) -> pd.DataFrame:
    rows = []
    for spec in specs or FACTOR_SPECS:
        row = asdict(spec)
        row["dependencies"] = ",".join(spec.dependencies)
        row["labels"] = ",".join(spec.labels)
        rows.append(row)
    return pd.DataFrame(rows)


def spec_map(specs: list[FactorSpec] | None = None) -> dict[str, FactorSpec]:
    return {spec.name: spec for spec in specs or FACTOR_SPECS}
