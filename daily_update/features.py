from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from daily_update.provider import _load_raw
from factor_research.alpha101_source import (
    Alpha101SourceConfig,
    compute_alpha101_features,
)
from factor_research.factor_library import add_basic_factors
from factor_research.ta_source import TaSourceConfig, compute_ta_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREPROCESSING = (
    PROJECT_ROOT
    / "outputs/prospective_forward_candidate_v1/runtime/current/model/"
    "forward_candidate_preprocessing.json"
)
ALPHA158_TABLE = (
    PROJECT_ROOT
    / "outputs/alpha158_expression_frame_v1/full158_main_research/expression_table.csv"
)
ALPHA360_TABLE = (
    PROJECT_ROOT
    / "outputs/alpha360_expression_frame_v1/batch358/expression_table.csv"
)


def _expression_features(
    provider: Path,
    instruments: list[str],
    target: date,
    names: list[str],
) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    tables = pd.concat(
        [pd.read_csv(ALPHA158_TABLE), pd.read_csv(ALPHA360_TABLE)],
        ignore_index=True,
    )
    selected = tables.set_index("catalog_name").loc[names]
    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    data = (
        D.features(
            instruments,
            selected["expression"].tolist(),
            start_time=target.isoformat(),
            end_time=target.isoformat(),
            freq="day",
        )
        .rename(columns=dict(zip(selected["expression"], names)))
        .reset_index()
    )
    data["instrument"] = data["instrument"].astype(str).str.upper()
    return data[["datetime", "instrument", *names]]


def compute_frozen_snapshot(
    provider: Path,
    target: date,
    instruments: list[str],
    warmup_calendar_days: int = 450,
) -> pd.DataFrame:
    feature_names = list(
        json.loads(PREPROCESSING.read_text(encoding="utf-8"))["feature_names"]
    )
    expression_names = [
        name
        for name in feature_names
        if name.startswith(("alpha158_", "alpha360_"))
    ]
    alpha_names = [
        name for name in feature_names if name.startswith("kunquant_alpha101_")
    ]
    ta_names = [name for name in feature_names if name.startswith("ta_")]
    start = target - timedelta(days=warmup_calendar_days)
    raw = _load_raw(provider, instruments, start, target)
    target_key = pd.Timestamp(target)

    expression = _expression_features(provider, instruments, target, expression_names)
    basics = add_basic_factors(raw.copy())
    basics = basics.loc[
        basics["datetime"].eq(target_key),
        [
            "datetime",
            "instrument",
            "amount_cv_20",
            "amount_mean_20",
            "corr_ret_amount_20",
        ],
    ]

    alpha_config = Alpha101SourceConfig(
        provider_uri=str(provider),
        market="frozen_strategy_v1",
        start=start.isoformat(),
        end=target.isoformat(),
        max_instruments=None,
        source_local_path=PROJECT_ROOT / "tmp/reference_repos/KunQuant",
        source_commit="d4b9e61f729df347730aa921b539b9df3c3fe36d",
        source_file="tests/KunTestUtil/ref_alpha101.py",
        source_module="KunTestUtil.ref_alpha101.Alphas",
        license="Apache-2.0",
        selected_smoke_factors=tuple(alpha_names),
        metadata_catalog=(
            PROJECT_ROOT
            / "outputs/factor_catalog_alpha101_v1/"
            "kunquant_alpha101_catalog_metadata.yaml"
        ),
        catalog_stage="frozen_strategy_v1",
        catalog_enabled=True,
        catalog_runnable=True,
        labels=(),
        output_dir=PROJECT_ROOT / "outputs/daily_data_update_v1/runtime",
    )
    alpha = compute_alpha101_features(alpha_config, raw)
    alpha = alpha.loc[
        alpha["datetime"].eq(target_key),
        ["datetime", "instrument", *alpha_names],
    ]

    ta_config = TaSourceConfig(
        provider_uri=str(provider),
        market="frozen_strategy_v1",
        start=start.isoformat(),
        end=target.isoformat(),
        max_instruments=None,
        source_local_path=PROJECT_ROOT / "tmp/reference_repos/ta",
        source_commit="a890410710a6e483c9ba08da7f3dd5089e4b9dff",
        source_file="ta/wrapper.py",
        source_function="add_all_ta_features",
        license="MIT",
        colprefix="ta_",
        fillna=False,
        vectorized=False,
        exclude_prefixes=(
            "ta_trend_visual_ichimoku",
            "ta_others_",
            "ta_volume_vpt",
            "ta_volume_nvi",
        ),
        selected_smoke_factors=tuple(ta_names),
        catalog_stage="frozen_strategy_v1",
        catalog_enabled=True,
        catalog_runnable=True,
        labels=(),
        output_dir=PROJECT_ROOT / "outputs/daily_data_update_v1/runtime",
    )
    ohlcv = raw.rename(
        columns={
            "$open": "open",
            "$high": "high",
            "$low": "low",
            "$close": "close",
            "$volume": "volume",
        }
    )
    ta = compute_ta_features(ta_config, ohlcv)
    ta = ta.loc[
        ta["datetime"].eq(target_key),
        ["datetime", "instrument", *ta_names],
    ]

    snapshot = expression.merge(
        basics,
        on=["datetime", "instrument"],
        how="outer",
        validate="one_to_one",
    )
    snapshot = snapshot.merge(
        alpha,
        on=["datetime", "instrument"],
        how="outer",
        validate="one_to_one",
    )
    snapshot = snapshot.merge(
        ta,
        on=["datetime", "instrument"],
        how="outer",
        validate="one_to_one",
    )
    snapshot = (
        snapshot[["datetime", "instrument", *feature_names]]
        .sort_values("instrument")
        .reset_index(drop=True)
    )
    if list(snapshot.columns) != ["datetime", "instrument", *feature_names]:
        raise ValueError("Frozen Strategy V1 feature order changed")
    if snapshot.empty or snapshot[feature_names].notna().sum(axis=1).eq(0).any():
        raise ValueError("Frozen Strategy V1 snapshot contains an all-NaN row")
    return snapshot
