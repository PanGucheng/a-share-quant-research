from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha101_source import (  # noqa: E402
    Alpha101SourceConfig,
    compute_alpha101_features,
    mask_raw_to_pit_membership,
    to_wind_wide,
)
from factor_research.factor_library import BASE_FIELDS  # noqa: E402
from factor_universe_v2.alpha101_canonical import (  # noqa: E402
    compute_canonical_alpha101_features,
)
from factor_universe_v2.historical_data import statement_event_timeline  # noqa: E402
from research_validation.feature_matrix import build_pit_key_grid  # noqa: E402
from research_validation.historical_engineering import (  # noqa: E402
    canonical_hash,
    compare_matrix_overlap,
    file_sha256,
)
from research_validation.overlap_lineage import (  # noqa: E402
    causal_kama_frame,
    exact_or_close_counts,
    partition_set_identity,
    project_to_keys,
    replace_factor_columns,
)


KEYS = ["datetime", "instrument"]
LEGACY_ALPHA_BY_PARTITION = {
    "alpha101_001": [
        "kunquant_alpha101_alpha015",
        "kunquant_alpha101_alpha017",
    ],
    "alpha101_002": [
        "kunquant_alpha101_alpha034",
        "kunquant_alpha101_alpha038",
        "kunquant_alpha101_alpha050",
        "kunquant_alpha101_alpha062",
    ],
    "alpha101_003": [
        "kunquant_alpha101_alpha077",
        "kunquant_alpha101_alpha078",
        "kunquant_alpha101_alpha085",
        "kunquant_alpha101_alpha098",
    ],
}
CANONICAL_ALPHA = [
    "kunquant_alpha101_alpha050_canonical_vwap_v2",
    "kunquant_alpha101_alpha062_canonical_vwap_v2",
    "kunquant_alpha101_alpha077_canonical_vwap_v2",
    "kunquant_alpha101_alpha078_canonical_vwap_v2",
    "kunquant_alpha101_alpha098_canonical_vwap_v2",
]
KAMA_FACTOR = "ta_momentum_kama"
KCP_FACTOR = "ta_volatility_kcp"
ALPHA_FACTORS = [
    factor for factors in LEGACY_ALPHA_BY_PARTITION.values() for factor in factors
] + CANONICAL_ALPHA
FUNDAMENTAL_FACTORS = [
    "mature_gross_profitability",
    "mature_operating_profitability",
    "mature_return_on_assets",
    "mature_book_leverage",
    "mature_current_ratio",
    "mature_cash_ratio",
    "mature_operating_cashflow_to_assets",
    "mature_cashflow_quality",
    "mature_accruals_to_assets",
    "mature_asset_growth_yoy",
    "mature_revenue_growth_yoy",
    "mature_net_income_growth_yoy",
    "mature_cashflow_to_sales",
    "mature_gross_margin",
    "mature_net_margin",
    "mature_book_to_market_pit",
    "mature_earnings_to_price_pit",
    "mature_sales_to_price_pit",
    "mature_cashflow_to_price_pit",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def load_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(path)


def _qlib(config: dict[str, Any]):
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    return D


def _normalize_intervals(path: Path) -> pd.DataFrame:
    intervals = pd.read_csv(path)
    intervals["instrument"] = intervals["instrument"].astype(str).str.upper()
    intervals["start_date"] = pd.to_datetime(intervals["start_date"])
    intervals["end_date"] = pd.to_datetime(intervals["end_date"])
    return intervals


def _source_config(
    config: dict[str, Any],
    names: list[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> Alpha101SourceConfig:
    return Alpha101SourceConfig(
        provider_uri=str(resolve(config["provider_uri"])),
        market="point_in_time",
        start=str(start.date()),
        end=str(end.date()),
        max_instruments=None,
        source_local_path=resolve(config["alpha101_source_path"]),
        source_commit="overlap-lineage-resolution-v1",
        source_file="tests/KunTestUtil/ref_alpha101.py",
        source_module="KunTestUtil.ref_alpha101.Alphas",
        license="Apache-2.0",
        selected_smoke_factors=tuple(names),
        metadata_catalog=resolve(config["alpha101_metadata_catalog"]),
        catalog_stage="overlap_lineage_resolution_v1",
        catalog_enabled=True,
        catalog_runnable=True,
        labels=(),
        output_dir=resolve(config["runtime_dir"]),
    )


def _rank_safe_alpha(
    config: dict[str, Any],
    masked: pd.DataFrame,
    keys: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    eligibility = to_wind_wide(masked)["S_DQ_CLOSE"].notna()
    legacy_names = sorted(
        factor for factors in LEGACY_ALPHA_BY_PARTITION.values() for factor in factors
    )
    legacy = compute_alpha101_features(
        _source_config(config, legacy_names, start, end),
        masked,
        rank_eligibility=eligibility,
    )
    legacy = project_to_keys(legacy, keys, legacy_names)
    registry_names = [
        factor.removeprefix("kunquant_alpha101_").removesuffix("_canonical_vwap_v2")
        for factor in CANONICAL_ALPHA
    ]
    canonical = compute_canonical_alpha101_features(
        masked,
        registry_names=registry_names,
        source_local_path=resolve(config["alpha101_source_path"]),
        rank_eligibility=eligibility,
    )
    canonical = project_to_keys(canonical, keys, CANONICAL_ALPHA)
    result = {"canonical": canonical}
    for partition_id, names in LEGACY_ALPHA_BY_PARTITION.items():
        result[partition_id] = legacy[[*KEYS, *names]]
    return result


def _calculation_input(
    config: dict[str, Any],
    keys: pd.DataFrame,
    intervals: pd.DataFrame,
    full_calendar: pd.DatetimeIndex,
    D: Any,
) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    start = pd.to_datetime(keys["datetime"]).min()
    end = pd.to_datetime(keys["datetime"]).max()
    first = int(full_calendar.searchsorted(start))
    warmup = full_calendar[
        max(0, first - int(config["alpha_warmup_trading_days"]))
    ]
    symbols = sorted(keys["instrument"].astype(str).str.upper().unique())
    fields = list(dict.fromkeys([*BASE_FIELDS, "$vwap"]))
    raw = D.features(
        symbols,
        fields,
        start_time=warmup,
        end_time=end,
        freq="day",
    ).reset_index()
    raw["datetime"] = pd.to_datetime(raw["datetime"])
    raw["instrument"] = raw["instrument"].astype(str).str.upper()
    membership_calendar = full_calendar[
        (full_calendar >= warmup) & (full_calendar <= end)
    ]
    membership_keys = build_pit_key_grid(intervals, membership_calendar)
    masked = mask_raw_to_pit_membership(
        raw,
        membership_keys,
        membership_start=intervals["start_date"].min(),
    )
    return masked, warmup, end


def materialize_kama(config: dict[str, Any]) -> Path:
    runtime = resolve(config["runtime_dir"])
    path = runtime / "stateful" / "causal_kama.parquet"
    receipt_path = path.with_suffix(".receipt.json")
    intervals = _normalize_intervals(resolve(config["extended_universe_intervals"]))
    identity = {
        "provider_uri": resolve(config["provider_uri"]).as_posix(),
        "interval_sha256": file_sha256(resolve(config["extended_universe_intervals"])),
        "start": config["long_history_start_date"],
        "end": config["overlap_end_date"],
        "implementation": "causal_kama_v1_no_np_roll",
    }
    if path.is_file() and receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            receipt.get("input_identity") == canonical_hash(identity)
            and receipt.get("output_sha256") == file_sha256(path)
        ):
            return path
    D = _qlib(config)
    symbols = sorted(intervals["instrument"].unique())
    raw = D.features(
        symbols,
        ["$close"],
        start_time=config["long_history_start_date"],
        end_time=config["overlap_end_date"],
        freq="day",
    ).reset_index()
    corrected = causal_kama_frame(raw)
    _atomic_parquet(corrected, path)
    receipt_path.write_text(
        json.dumps(
            {
                "input_identity": canonical_hash(identity),
                "output_sha256": file_sha256(path),
                "row_count": len(corrected),
                "instrument_count": int(corrected["instrument"].nunique()),
                "start": str(corrected["datetime"].min().date()),
                "end": str(corrected["datetime"].max().date()),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _partition_row(
    parent: pd.Series,
    path: Path,
    *,
    correction_status: str,
) -> dict[str, Any]:
    return {
        **parent.to_dict(),
        "partition_path": path.as_posix(),
        "output_sha256": file_sha256(path),
        "output_size_bytes": path.stat().st_size,
        "parent_partition_path": str(parent["partition_path"]),
        "parent_output_sha256": str(parent["output_sha256"]),
        "correction_status": correction_status,
        "implementation_version": (
            "pit_rank_scope_v1+causal_kama_v1"
            if correction_status != "parent_reference"
            else "inherited_parent"
        ),
    }


def _materialize_scope(
    config: dict[str, Any],
    *,
    scope: str,
    years: list[int] | None,
) -> None:
    if scope not in {"historical", "overlap"}:
        raise ValueError(scope)
    manifest_path = resolve(
        config[
            "parent_historical_partition_manifest"
            if scope == "historical"
            else "parent_overlap_partition_manifest"
        ]
    )
    parent = pd.read_csv(manifest_path)
    if "year" not in parent:
        parent["year"] = 2021
    selected = sorted(parent["year"].astype(int).unique())
    if years:
        selected = [year for year in selected if year in set(years)]
    runtime = resolve(config["runtime_dir"])
    composed_path = runtime / f"{scope}_partition_manifest.csv"
    intervals = _normalize_intervals(resolve(config["extended_universe_intervals"]))
    D = _qlib(config)
    full_calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["long_history_start_date"],
            end_time=config["overlap_end_date"],
            freq="day",
        )
    )
    kama_path = materialize_kama(config)
    for year in selected:
        year_parent = parent.loc[parent["year"].astype(int).eq(year)].copy()
        year_manifest_path = runtime / scope / str(year) / "partition_manifest.csv"
        if year_manifest_path.is_file():
            cached = pd.read_csv(year_manifest_path)
            if len(cached) == len(year_parent) and cached.apply(
                lambda row: Path(str(row["partition_path"])).is_file()
                and file_sha256(Path(str(row["partition_path"])))
                == str(row["output_sha256"]),
                axis=1,
            ).all():
                print(f"{scope} {year} cache hit", flush=True)
                continue
        key_row = year_parent.loc[year_parent["partition_id"].eq("alpha101_001")]
        if key_row.empty:
            raise ValueError(f"missing alpha101_001 keys for {scope} {year}")
        keys = pd.read_parquet(key_row.iloc[0]["partition_path"], columns=KEYS)
        keys["datetime"] = pd.to_datetime(keys["datetime"])
        keys["instrument"] = keys["instrument"].astype(str).str.upper()
        masked, warmup, end = _calculation_input(
            config, keys, intervals, full_calendar, D
        )
        corrected = _rank_safe_alpha(config, masked, keys, warmup, end)
        kama = pd.read_parquet(
            kama_path,
            filters=[
                ("datetime", ">=", keys["datetime"].min()),
                ("datetime", "<=", keys["datetime"].max()),
                ("instrument", "in", sorted(keys["instrument"].unique())),
            ],
        )
        corrected["ta_001"] = project_to_keys(kama, keys, [KAMA_FACTOR])
        replacement_map = {
            **LEGACY_ALPHA_BY_PARTITION,
            "canonical": CANONICAL_ALPHA,
            "ta_001": [KAMA_FACTOR],
        }
        rows: list[dict[str, Any]] = []
        for _, item in year_parent.iterrows():
            partition_id = str(item["partition_id"])
            parent_path = Path(str(item["partition_path"]))
            if partition_id not in replacement_map:
                rows.append(
                    _partition_row(
                        item,
                        parent_path,
                        correction_status="parent_reference",
                    )
                )
                continue
            names = replacement_map[partition_id]
            target = runtime / scope / str(year) / f"{partition_id}.parquet"
            parent_frame = pd.read_parquet(parent_path)
            output = replace_factor_columns(
                parent_frame,
                corrected[partition_id],
                names,
            )
            _atomic_parquet(output, target)
            rows.append(
                _partition_row(
                    item,
                    target,
                    correction_status="corrected_versioned_implementation",
                )
            )
        year_rows = pd.DataFrame(rows)
        year_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_manifest = year_manifest_path.with_suffix(".tmp.csv")
        year_rows.sort_values(["year", "partition_id"], kind="stable").to_csv(
            temporary_manifest, index=False
        )
        temporary_manifest.replace(year_manifest_path)
        print(f"{scope} {year} corrected", flush=True)
    year_manifests = sorted((runtime / scope).glob("*/partition_manifest.csv"))
    if year_manifests:
        composed = pd.concat(
            [pd.read_csv(path) for path in year_manifests], ignore_index=True
        ).sort_values(["year", "partition_id"], kind="stable")
        temporary_composed = composed_path.with_suffix(".tmp.csv")
        composed.to_csv(temporary_composed, index=False)
        temporary_composed.replace(composed_path)


def _load_partition_values(
    manifest: pd.DataFrame,
    partition_id: str,
    names: list[str],
    *,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    row = manifest.loc[manifest["partition_id"].eq(partition_id)]
    if len(row) != 1:
        raise ValueError(f"expected one {partition_id} partition, got {len(row)}")
    frame = pd.read_parquet(row.iloc[0]["partition_path"], columns=[*KEYS, *names])
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    if start is not None and end is not None:
        frame = frame.loc[frame["datetime"].between(start, end)]
    return frame


def _statement_window_evidence(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    codes = ["300094_SZ", "002217_SZ"]
    for lineage, root_key in (
        ("frozen_parent", "old_statement_root"),
        ("extended", "extended_statement_root"),
    ):
        root = resolve(config[root_key])
        frames = {
            api: pd.concat(
                [pd.read_parquet(root / api / f"{code}.parquet") for code in codes],
                ignore_index=True,
            )
            for api in ("income", "balancesheet", "cashflow")
        }
        events, _ = statement_event_timeline(
            frames["income"], frames["balancesheet"], frames["cashflow"]
        )
        for instrument in ("SZ300094", "SZ002217"):
            part = events.loc[events["instrument"].eq(instrument)]
            rows.append(
                {
                    "lineage": lineage,
                    "instrument": instrument,
                    "event_count": len(part),
                    "first_information_available_date": part[
                        "information_available_date"
                    ].min(),
                    "first_report_period": part["report_period"].min(),
                    "has_prior_total_assets_before_overlap": bool(
                        part.loc[
                            part["information_available_date"].le(
                                pd.Timestamp(config["overlap_start_date"])
                            ),
                            "prior_total_assets",
                        ]
                        .notna()
                        .any()
                    ),
                }
            )
    return pd.DataFrame(rows)


def finalize(config_path: Path, config: dict[str, Any]) -> None:
    runtime = resolve(config["runtime_dir"])
    output = resolve(config["output_dir"])
    report = resolve(config["report_dir"])
    output.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)
    historical = pd.read_csv(runtime / "historical_partition_manifest.csv")
    overlap_manifest = pd.read_csv(runtime / "overlap_partition_manifest.csv")
    parent_historical = pd.read_csv(resolve(config["parent_historical_partition_manifest"]))
    frozen = pd.read_csv(resolve(config["frozen_partition_manifest"]))
    if len(historical) != len(parent_historical):
        raise ValueError("corrected historical manifest does not cover every parent partition")
    integrity = historical.apply(
        lambda row: Path(str(row["partition_path"])).is_file()
        and file_sha256(Path(str(row["partition_path"]))) == str(row["output_sha256"]),
        axis=1,
    )
    if not integrity.all():
        raise ValueError("corrected historical partition integrity failed")
    overlap_rows: list[pd.DataFrame] = []
    for _, item in overlap_manifest.iterrows():
        match = frozen.loc[frozen["partition_id"].eq(item["partition_id"])]
        if match.empty:
            continue
        names = str(item["factors"]).split(",")
        left = pd.read_parquet(item["partition_path"], columns=[*KEYS, *names])
        right = pd.read_parquet(match.iloc[0]["partition_path"], columns=[*KEYS, *names])
        right["datetime"] = pd.to_datetime(right["datetime"])
        right = right.loc[
            right["datetime"].between(
                pd.Timestamp(config["overlap_start_date"]),
                pd.Timestamp(config["overlap_end_date"]),
            )
        ]
        overlap_rows.append(compare_matrix_overlap(left, right, names))
    overlap = pd.concat(overlap_rows, ignore_index=True)
    overlap.to_csv(report / "matrix_overlap_validation.csv", index=False)

    old_overlap = pd.read_csv(resolve(config["old_overlap_validation"]))
    old_bad = set(
        old_overlap.loc[old_overlap["value_difference_count"].gt(0), "factor"].astype(str)
    )
    decision_rows: list[dict[str, Any]] = []
    new_by_factor = overlap.set_index("factor")
    for factor in sorted(old_bad):
        difference_count = int(new_by_factor.loc[factor, "value_difference_count"])
        if factor in ALPHA_FACTORS:
            root_cause = (
                "frozen full-horizon column axis plus upstream fillna-before-rank "
                "reactivated lifecycle-ineligible instruments"
            )
            semantics = "rank only the dated PIT eligible cross-section at every rank operator"
            action = "correct extension with versioned PIT-rank implementation; preserve frozen parent"
            category = "frozen_parent_implementation_bug"
            risk = "upstream formulas remain vendor-derived; rank scope is project-enforced"
        elif factor == KAMA_FACTOR:
            root_cause = (
                "upstream TA KAMA uses np.roll lag initialization, so prefix state reads the supplied series end"
            )
            semantics = "causal lag and one continuous recursive state from the declared history anchor"
            action = "correct extension with causal KAMA v1; preserve frozen parent"
            category = "frozen_and_parent_extension_implementation_bug"
            risk = "state before the 2000-01-04 anchor is unavailable"
        elif factor == KCP_FACTOR:
            root_cause = "same signed infinities were misclassified by the old overlap comparator"
            semantics = "same signed infinity is lineage-equal but remains non-finite for qualification"
            action = "fix comparator; retain existing factor qualification block"
            category = "overlap_comparator_bug"
            risk = "factor remains excluded from research-usable representation due non-finite values"
        elif factor in FUNDAMENTAL_FACTORS:
            root_cause = (
                "frozen parent statement endpoint began in 2018; extension recovered earlier public "
                "events and prior-year bases"
            )
            semantics = "latest public revision with information_available_date <= decision date"
            action = "preserve extension and accept versioned source-window residual"
            category = "explained_upstream_statement_window_residual"
            risk = "practical PIT is not a provider-vintage archive"
        else:
            root_cause = "unclassified"
            semantics = "unresolved"
            action = "quarantine"
            category = "unresolved"
            risk = "unresolved lineage"
        decision_rows.append(
            {
                "factor": factor,
                "root_cause_category": category,
                "root_cause": root_cause,
                "authoritative_semantics": semantics,
                "action": action,
                "resolved": category != "unresolved",
                "remaining_risk": risk,
                "old_value_difference_count": int(
                    old_overlap.set_index("factor").loc[factor, "value_difference_count"]
                ),
                "new_value_difference_count": difference_count,
            }
        )
    decisions = pd.DataFrame(decision_rows)
    decisions.to_csv(report / "factor_lineage_decisions.csv", index=False)
    _statement_window_evidence(config).to_csv(
        report / "fundamental_statement_window_evidence.csv", index=False
    )

    parent_overlap = pd.read_csv(resolve(config["parent_overlap_partition_manifest"]))
    correction_rows: list[dict[str, Any]] = []
    for partition_id, names in {
        **LEGACY_ALPHA_BY_PARTITION,
        "canonical": CANONICAL_ALPHA,
        "ta_001": [KAMA_FACTOR],
    }.items():
        before = _load_partition_values(parent_overlap, partition_id, names)
        after = _load_partition_values(overlap_manifest, partition_id, names)
        joined = before.merge(after, on=KEYS, suffixes=("_parent", "_corrected"))
        for name in names:
            correction_rows.append(
                {
                    "factor": name,
                    **exact_or_close_counts(
                        joined[f"{name}_parent"], joined[f"{name}_corrected"]
                    ),
                }
            )
    pd.DataFrame(correction_rows).to_csv(
        report / "parent_correction_validation.csv", index=False
    )

    state_path = runtime / "stateful" / "causal_kama.parquet"
    state_checks: list[dict[str, Any]] = []
    for _, item in historical.loc[historical["partition_id"].eq("ta_001")].iterrows():
        left = pd.read_parquet(item["partition_path"], columns=[*KEYS, KAMA_FACTOR])
        right = pd.read_parquet(
            state_path,
            filters=[
                ("datetime", ">=", pd.to_datetime(left["datetime"]).min()),
                ("datetime", "<=", pd.to_datetime(left["datetime"]).max()),
                ("instrument", "in", sorted(left["instrument"].unique())),
            ],
        )
        aligned = left[KEYS].merge(right, on=KEYS, how="left", validate="one_to_one")
        counts = exact_or_close_counts(left[KAMA_FACTOR], aligned[KAMA_FACTOR])
        state_checks.append({"year": int(item["year"]), **counts})
    state_validation = pd.DataFrame(state_checks)
    state_validation.to_csv(report / "causal_kama_state_validation.csv", index=False)
    state_pass = bool(state_validation["difference_count"].eq(0).all())

    historical.to_csv(output / "partition_manifest.csv", index=False)
    overlap_manifest.to_csv(output / "overlap_partition_manifest.csv", index=False)
    matrix_id = partition_set_identity(historical)
    exact_count = int(overlap["value_difference_count"].eq(0).sum())
    explained_count = int(
        overlap.loc[overlap["value_difference_count"].gt(0), "factor"].isin(
            decisions.loc[decisions["resolved"], "factor"]
        ).sum()
    )
    quarantine_count = int((~decisions["resolved"]).sum())
    parent_manifest = json.loads(resolve(config["parent_manifest"]).read_text(encoding="utf-8"))
    manifest = {
        "schema_version": 1,
        "stage_id": config["stage_id"],
        "artifact_status": "lineage_resolved" if quarantine_count == 0 else "quarantined",
        "extended_matrix_generated": True,
        "extended_matrix_id": matrix_id,
        "parent_extended_matrix_id": parent_manifest["extended_matrix_id"],
        "parent_partial_extension_overwritten": False,
        "historical_partition_count": len(historical),
        "corrected_partition_count": int(
            historical["correction_status"].eq("corrected_versioned_implementation").sum()
        ),
        "parent_referenced_partition_count": int(
            historical["correction_status"].eq("parent_reference").sum()
        ),
        "partition_integrity_pass": bool(integrity.all()),
        "causal_kama_state_pass": state_pass,
        "practical_pit_pass": bool(parent_manifest["practical_pit_pass"]),
        "historical_universe_overlap_pass": bool(
            parent_manifest["historical_universe_overlap_pass"]
        ),
        "continuous_parent_state_pass": bool(parent_manifest["continuous_state_pass"]),
        "overlap_factor_count": len(overlap),
        "overlap_exact_factor_count": exact_count,
        "overlap_explained_factor_count": explained_count,
        "overlap_quarantined_factor_count": quarantine_count,
        "overlap_unexplained_factor_count": int(
            len(overlap)
            - exact_count
            - explained_count
            - quarantine_count
        ),
        "overlap_value_difference_count": int(overlap["value_difference_count"].sum()),
        "overlap_key_set_pass": bool(
            overlap["extended_only_key_count"].eq(0).all()
            and overlap["frozen_only_key_count"].eq(0).all()
        ),
        "overlap_exact_value_pass": bool(overlap["value_difference_count"].eq(0).all()),
        "overlap_lineage_resolved": quarantine_count == 0,
        "dataset_protocol_redesign_input_ready": quarantine_count == 0
        and bool(integrity.all())
        and state_pass,
        "factor_universe_v2_definitions_changed": False,
        "frozen_matrix_changed": False,
        "research_protocol_redesign_started": False,
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "formal_structured_ml_competition_started": False,
        "model_outcomes_read": False,
        "config_sha256": file_sha256(config_path),
    }
    manifest["manifest_identity"] = canonical_hash(manifest)
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lineage_summary = (
        decisions.groupby("root_cause_category", as_index=False)
        .agg(
            factor_count=("factor", "size"),
            old_value_difference_count=("old_value_difference_count", "sum"),
            new_value_difference_count=("new_value_difference_count", "sum"),
            resolved=("resolved", "all"),
        )
        .sort_values("root_cause_category")
    )
    lineage_summary.to_csv(report / "root_cause_summary.csv", index=False)
    report_text = f"""# Extended Matrix Overlap Lineage Resolution V1

> 状态：`{manifest['artifact_status']}`。旧 frozen Matrix 与旧 `partial_extension` 均保持 byte-immutable；未读取模型 outcomes，未启动 Structured ML 或 Research Protocol redesign。

## 最终结论

- New Extended Matrix identity: `{matrix_id}`
- Parent Extended Matrix identity: `{manifest['parent_extended_matrix_id']}`
- Historical partitions: `{len(historical)}`（corrected `{manifest['corrected_partition_count']}`；parent references `{manifest['parent_referenced_partition_count']}`）
- Overlap factors: `{len(overlap)}`
- Exact / explained / quarantined: `{exact_count}` / `{explained_count}` / `{quarantine_count}`
- Key-set pass: `{manifest['overlap_key_set_pass']}`
- Exact-value pass against frozen parent: `{manifest['overlap_exact_value_pass']}`（不以复制旧 bug 为目标）
- All old mismatches explained: `{manifest['overlap_lineage_resolved']}`

## Root causes

```text
{lineage_summary.to_string(index=False)}
```

### Alpha101

15 个 Alpha101 mismatch 具有同一主因：冻结计算的全区间列轴包含未来才出现的股票，而上游部分公式会先把结构性 NaN 填为 0/1，再执行横截面 rank；因此 raw mask 被中间 fillna 取消，早期横截面依赖未来 instrument axis。新实现不改公式，只在每个 rank operator 前重新施加当日 PIT eligibility。

### TA

`ta_momentum_kama` 的上游实现使用 `np.roll` 生成滞后，序列开头读取序列末尾，递归状态随后持续传播。新实现采用因果 diff、明确的 `2000-01-04` state anchor 和跨年连续缓存。`ta_volatility_kcp` 两边是相同 `-inf`；旧 comparator 误报，同号 infinity 现按 lineage-equal 处理，但该因子继续沿用既有 non-finite qualification block。

### Fundamental PIT

19 个 factor 的 residual 只涉及 `SZ300094` 的 overlap 前两日和 `SZ002217` 的同比基期。旧父 artifact 的 statement endpoint 从 2018 开始；扩展抓取从 2008 开始，恢复了当时已经公开的旧事件和 prior-year base。PIT 规则、same-day ordering 与 no-future contract 未发现错误，因此保留 extension 值并记录 source-window provenance。

## Validation

- Partition integrity: `{manifest['partition_integrity_pass']}`
- Causal KAMA state/cache equality: `{manifest['causal_kama_state_pass']}`
- Parent continuous-state checks retained: `{manifest['continuous_parent_state_pass']}`
- Practical PIT checks retained: `{manifest['practical_pit_pass']}`
- Historical universe overlap retained: `{manifest['historical_universe_overlap_pass']}`
- Quarantine: `{quarantine_count}`

逐因子决策见 `factor_lineage_decisions.csv`；新 overlap 数值审计见 `matrix_overlap_validation.csv`；Fundamental source-window 证据见 `fundamental_statement_window_evidence.csv`。

## 下一阶段条件

从 overlap lineage 条件看，新的 versioned Extended Matrix 已可作为 Dataset / Research Protocol redesign 的正式输入：`{manifest['dataset_protocol_redesign_input_ready']}`。这不等于已启动下一阶段，也不授权读取模型结果或训练模型；后续必须显式绑定上述新 identity，并继续尊重 frozen qualification（包括 KCP 的既有 block）。

## Governance

Factor Universe V2 definitions、Research Protocol、Strategy V1、Forward Track、旧 frozen Matrix 与旧 partial-extension artifact 均未改变；Structured ML/model/portfolio 工作未启动。
"""
    (report / "REPORT.md").write_text(report_text, encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve Extended Matrix overlap lineage and build a versioned correction."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/extended_matrix_overlap_lineage_resolution_v1.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=("kama", "historical", "overlap", "finalize", "all"),
        default="all",
    )
    parser.add_argument("--years", nargs="*", type=int)
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = load_config(config_path)
    if args.stage in {"kama", "all"}:
        materialize_kama(config)
    if args.stage in {"historical", "all"}:
        _materialize_scope(config, scope="historical", years=args.years)
    if args.stage in {"overlap", "all"}:
        _materialize_scope(config, scope="overlap", years=[2021])
    if args.stage in {"finalize", "all"}:
        finalize(config_path, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
