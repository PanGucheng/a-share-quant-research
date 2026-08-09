from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from data_source_audit.normalizers import normalize_baostock


class NotReady(RuntimeError):
    """The upstream daily payload is not published yet; retry is safe."""


def load_frozen_universe(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Frozen Strategy V1 universe is missing: {path}")
    instruments = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        symbol = line.split("\t", 1)[0].strip().upper()
        if symbol.startswith(("SH6", "SZ0", "SZ3")):
            instruments.append(symbol)
    if not instruments:
        raise ValueError("Frozen Strategy V1 universe is empty")
    return sorted(set(instruments))


def validate_baostock_target(
    raw: pd.DataFrame,
    target: date,
    expected: list[str],
    min_coverage: float,
) -> dict[str, object]:
    if raw.empty:
        raise NotReady(f"BaoStock has not published {target.isoformat()} daily bars")
    normalized = normalize_baostock(raw)
    day = normalized.loc[normalized["date"].eq(pd.Timestamp(target))].copy()
    required = [
        "price_raw_open",
        "price_raw_high",
        "price_raw_low",
        "price_raw_close",
        "volume_shares",
        "amount_cny",
    ]
    complete = day[required].notna().all(axis=1) & day["is_trading"].astype(bool)
    covered = set(day.loc[complete, "instrument"])
    trading = set(day.loc[day["is_trading"].astype(bool), "instrument"])
    required_set = set(expected)
    missing_fields_while_trading = set(
        day.loc[
            day["is_trading"].astype(bool) & ~day[required].notna().all(axis=1),
            "instrument",
        ]
    ).intersection(required_set)
    coverage = len(covered.intersection(expected)) / len(expected) if expected else 0.0
    if coverage < min_coverage:
        raise NotReady(
            f"BaoStock {target.isoformat()} coverage {coverage:.2%} "
            f"is below {min_coverage:.2%}"
        )
    return {
        "expected_instruments": len(expected),
        "complete_instruments": len(covered.intersection(expected)),
        "normal_trading_instruments": len(trading.intersection(required_set)),
        "suspended_or_nontrading_instruments": len(required_set - trading),
        "missing_ohlcva_while_trading": len(missing_fields_while_trading),
        "coverage": coverage,
        "ohlcva_complete": not missing_fields_while_trading,
    }


def compatibility_smoke(
    fallback_daily: pd.DataFrame,
    community: pd.DataFrame,
    fallback_features: pd.DataFrame,
    community_features: pd.DataFrame,
) -> dict[str, object]:
    raw_columns = [
        "raw_open",
        "raw_high",
        "raw_low",
        "raw_close",
        "raw_volume",
        "raw_amount",
        "factor",
    ]
    raw = fallback_daily[["symbol", *raw_columns]].merge(
        community[["symbol", *raw_columns]],
        on="symbol",
        suffixes=("_bao", "_community"),
        validate="one_to_one",
    )
    raw_failures = {}
    for column in raw_columns:
        left = pd.to_numeric(raw[f"{column}_bao"], errors="coerce").to_numpy(float)
        right = pd.to_numeric(raw[f"{column}_community"], errors="coerce").to_numpy(float)
        atol = (
            0.02
            if column.startswith("raw_") and column not in {"raw_volume", "raw_amount"}
            else 1e-6
        )
        ok = np.isclose(left, right, rtol=1e-5, atol=atol, equal_nan=True)
        raw_failures[column] = int((~ok).sum())
    feature_names = [
        c for c in fallback_features if c not in {"datetime", "instrument"}
    ]
    feature = fallback_features.merge(
        community_features,
        on=["datetime", "instrument"],
        suffixes=("_bao", "_community"),
        validate="one_to_one",
    )
    factor_failure_count = 0
    for name in feature_names:
        left = pd.to_numeric(feature[f"{name}_bao"], errors="coerce").to_numpy(float)
        right = pd.to_numeric(
            feature[f"{name}_community"],
            errors="coerce",
        ).to_numpy(float)
        factor_failure_count += int(
            (~np.isclose(left, right, rtol=1e-5, atol=1e-6, equal_nan=True)).sum()
        )
    passed = not any(raw_failures.values()) and factor_failure_count == 0
    return {
        "status": "pass" if passed else "blocked_material_difference",
        "common_raw_instruments": len(raw),
        "raw_failure_counts": raw_failures,
        "common_feature_rows": len(feature),
        "feature_value_failure_count": factor_failure_count,
    }
