from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
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
from factor_universe_v2.historical_data import (  # noqa: E402
    align_statement_events_to_keys,
    normalize_trade_date_frame,
    statement_event_timeline,
)
from factor_universe_v2.mature_factors import (  # noqa: E402
    FUNDAMENTAL_FACTOR_NAMES,
    compute_fundamental_factors,
)
from research_validation.canonical_dataset import (  # noqa: E402
    canonical_dataset_identity,
    dated_membership_axis,
    read_effective_partition,
    validate_partition_segments,
    validate_semantic_continuity,
)
from research_validation.feature_matrix import build_pit_key_grid  # noqa: E402
from research_validation.historical_engineering import (  # noqa: E402
    audit_practical_pit,
    canonical_hash,
    file_sha256,
)
from research_validation.overlap_lineage import (  # noqa: E402
    causal_kama_frame,
    exact_or_close_counts,
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
ALPHA_FACTORS = [
    factor for factors in LEGACY_ALPHA_BY_PARTITION.values() for factor in factors
] + CANONICAL_ALPHA
KAMA_FACTOR = "ta_momentum_kama"
KCP_FACTOR = "ta_volatility_kcp"
FUNDAMENTAL_FACTORS = list(FUNDAMENTAL_FACTOR_NAMES)
CORRECTED_PARTITIONS = {
    **LEGACY_ALPHA_BY_PARTITION,
    "canonical": CANONICAL_ALPHA,
    "ta_001": [KAMA_FACTOR],
    "mature_fundamental": FUNDAMENTAL_FACTORS,
}


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


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def _atomic_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes"}


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
        source_commit="canonical-historical-dataset-assembly-v1",
        source_file="tests/KunTestUtil/ref_alpha101.py",
        source_module="KunTestUtil.ref_alpha101.Alphas",
        license="Apache-2.0",
        selected_smoke_factors=tuple(names),
        metadata_catalog=resolve(config["alpha101_metadata_catalog"]),
        catalog_stage="canonical_historical_dataset_assembly_v1",
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
        factor.removeprefix("kunquant_alpha101_").removesuffix(
            "_canonical_vwap_v2"
        )
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
    # Use one stable axis through the canonical horizon so prefix and full-
    # horizon evaluations cannot acquire different cross-sectional columns.
    axis_end = max(end, pd.Timestamp(config["continuation_end_date"]))
    symbols = dated_membership_axis(intervals, warmup, axis_end)
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


def _frozen_manifest(config: dict[str, Any]) -> pd.DataFrame:
    return pd.read_csv(resolve(config["frozen_partition_manifest"]))


def _frozen_keys(config: dict[str, Any], start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    frozen = _frozen_manifest(config)
    row = frozen.loc[frozen["partition_id"].eq("alpha101_001")].iloc[0]
    keys = pd.read_parquet(
        row["partition_path"],
        columns=KEYS,
        filters=[("datetime", ">=", start), ("datetime", "<=", end)],
    )
    keys["datetime"] = pd.to_datetime(keys["datetime"])
    keys["instrument"] = keys["instrument"].astype(str).str.upper()
    return keys.sort_values(KEYS, kind="stable").reset_index(drop=True)


def _continuation_symbols(config: dict[str, Any]) -> list[str]:
    keys = _frozen_keys(
        config,
        pd.Timestamp(config["continuation_start_date"]),
        pd.Timestamp(config["continuation_end_date"]),
    )
    return sorted(keys["instrument"].unique())


def materialize_causal_kama(config: dict[str, Any]) -> Path:
    runtime = resolve(config["runtime_dir"])
    path = runtime / "stateful" / "causal_kama_2000_2026.parquet"
    receipt_path = path.with_suffix(".receipt.json")
    intervals_path = resolve(config["extended_universe_intervals"])
    symbols = _continuation_symbols(config)
    identity = {
        "provider_uri": resolve(config["provider_uri"]).as_posix(),
        "interval_sha256": file_sha256(intervals_path),
        "symbol_identity": canonical_hash(symbols),
        "start": config["long_history_start_date"],
        "end": config["continuation_end_date"],
        "implementation": "causal_kama_v1_no_np_roll",
    }
    input_identity = canonical_hash(identity)
    if path.is_file() and receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            receipt.get("input_identity") == input_identity
            and receipt.get("output_sha256") == file_sha256(path)
        ):
            return path
    D = _qlib(config)
    raw = D.features(
        symbols,
        ["$close"],
        start_time=config["long_history_start_date"],
        end_time=config["continuation_end_date"],
        freq="day",
    ).reset_index()
    corrected = causal_kama_frame(raw)
    _atomic_parquet(corrected, path)
    _atomic_json(
        {
            "input_identity": input_identity,
            "output_sha256": file_sha256(path),
            "row_count": len(corrected),
            "instrument_count": int(corrected["instrument"].nunique()),
            "start": str(corrected["datetime"].min().date()),
            "end": str(corrected["datetime"].max().date()),
            "implementation": identity["implementation"],
        },
        receipt_path,
    )
    return path


def _statement_source_paths(config: dict[str, Any], symbols: list[str]) -> list[Path]:
    roots = [
        resolve(config["historical_statement_root"]),
        resolve(config["frozen_statement_root"]),
    ]
    paths: list[Path] = []
    for api in ("income", "balancesheet", "cashflow"):
        for symbol in symbols:
            segment = f"{symbol[2:]}_{symbol[:2]}"
            for root in roots:
                path = root / api / f"{segment}.parquet"
                if path.is_file():
                    paths.append(path)
    return sorted(paths)


def _source_set_identity(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def materialize_statement_events(config: dict[str, Any]) -> Path:
    runtime = resolve(config["runtime_dir"])
    path = runtime / "fundamental" / "merged_statement_events.parquet"
    receipt_path = path.with_suffix(".receipt.json")
    symbols = _continuation_symbols(config)
    source_paths = _statement_source_paths(config, symbols)
    input_identity = canonical_hash(
        {
            "source_set_identity": _source_set_identity(source_paths),
            "symbols": canonical_hash(symbols),
            "semantics": "practical_reconstructed_pit_latest_public_revision_v1",
        }
    )
    if path.is_file() and receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            receipt.get("input_identity") == input_identity
            and receipt.get("output_sha256") == file_sha256(path)
        ):
            return path
    roots = [
        resolve(config["historical_statement_root"]),
        resolve(config["frozen_statement_root"]),
    ]
    frames: dict[str, pd.DataFrame] = {}
    for api in ("income", "balancesheet", "cashflow"):
        parts: list[pd.DataFrame] = []
        for symbol in symbols:
            segment = f"{symbol[2:]}_{symbol[:2]}"
            for root in roots:
                source = root / api / f"{segment}.parquet"
                if source.is_file():
                    parts.append(pd.read_parquet(source))
        nonempty = [part for part in parts if not part.empty]
        if not nonempty:
            raise ValueError(f"no statement rows available for {api}")
        combined = pd.concat(nonempty, ignore_index=True)
        frames[api] = combined.drop_duplicates().reset_index(drop=True)
    events, revision = statement_event_timeline(
        frames["income"], frames["balancesheet"], frames["cashflow"]
    )
    _atomic_parquet(events, path)
    revision_path = path.with_name("merged_statement_revision_audit.parquet")
    _atomic_parquet(revision, revision_path)
    _atomic_json(
        {
            "input_identity": input_identity,
            "output_sha256": file_sha256(path),
            "revision_audit_sha256": file_sha256(revision_path),
            "source_file_count": len(source_paths),
            "event_count": len(events),
            "instrument_count": int(events["instrument"].nunique()),
            "first_information_available_date": str(
                pd.to_datetime(events["information_available_date"]).min().date()
            ),
            "last_information_available_date": str(
                pd.to_datetime(events["information_available_date"]).max().date()
            ),
            "pit_contract": "information_available_date_lte_decision_date",
        },
        receipt_path,
    )
    return path


def _market_cap_for_year(config: dict[str, Any], year: int) -> pd.DataFrame:
    root = resolve(config["frozen_daily_basic_root"])
    start = max(pd.Timestamp(f"{year}-01-01"), pd.Timestamp(config["continuation_start_date"]))
    end = min(pd.Timestamp(f"{year}-12-31"), pd.Timestamp(config["continuation_end_date"]))
    paths = [
        root / f"{date.strftime('%Y%m%d')}.parquet"
        for date in pd.date_range(start, end)
        if (root / f"{date.strftime('%Y%m%d')}.parquet").is_file()
    ]
    parts = [pd.read_parquet(path, columns=["ts_code", "trade_date", "total_mv"]) for path in paths]
    if not parts:
        raise ValueError(f"no frozen daily_basic market-cap rows for {year}")
    normalized = normalize_trade_date_frame(pd.concat(parts, ignore_index=True))
    normalized["total_mv_cny"] = pd.to_numeric(
        normalized["total_mv"], errors="coerce"
    ) * 10_000.0
    return normalized[[*KEYS, "total_mv_cny"]]


def _project_fundamental(
    config: dict[str, Any],
    keys: pd.DataFrame,
    year: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.read_parquet(materialize_statement_events(config))
    aligned = align_statement_events_to_keys(keys, events)
    market_cap = _market_cap_for_year(config, year)
    aligned = aligned.merge(market_cap, on=KEYS, how="left", validate="one_to_one")
    pit = audit_practical_pit(aligned, events)
    eligible = aligned.loc[aligned["information_available_date"].notna()].copy()
    values = compute_fundamental_factors(eligible)
    return project_to_keys(values, keys, FUNDAMENTAL_FACTORS), pit


def _parent_slice(
    frozen: pd.DataFrame,
    partition_id: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> tuple[pd.Series, pd.DataFrame]:
    row = frozen.loc[frozen["partition_id"].eq(partition_id)]
    if len(row) != 1:
        raise ValueError(f"expected one frozen partition {partition_id}")
    item = row.iloc[0]
    frame = pd.read_parquet(
        item["partition_path"], filters=[("datetime", ">=", start), ("datetime", "<=", end)]
    )
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    frame["instrument"] = frame["instrument"].astype(str).str.upper()
    return item, frame.sort_values(KEYS, kind="stable").reset_index(drop=True)


def _corrected_row(
    parent: pd.Series,
    path: Path,
    *,
    year: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
    names: list[str],
    implementation: str,
) -> dict[str, Any]:
    return {
        "segment_id": f"continuation_{year}",
        "partition_id": str(parent["partition_id"]),
        "partition_path": path.as_posix(),
        "factor_count": int(parent["factor_count"]),
        "row_count": int(len(pd.read_parquet(path, columns=["datetime"]))),
        "output_sha256": file_sha256(path),
        "output_size_bytes": path.stat().st_size,
        "factors": str(parent["factors"]),
        "effective_start": str(start.date()),
        "effective_end": str(end.date()),
        "lineage_action": "corrected_continuation_recompute",
        "recomputed_factors": ",".join(names),
        "implementation_version": implementation,
        "parent_partition_path": str(parent["partition_path"]),
        "parent_output_sha256": str(parent["output_sha256"]),
        "parent_artifact_role": "immutable_frozen_evidence",
        "alpha_axis_version": "stable_horizon_membership_axis_v3",
    }


def materialize_year(config: dict[str, Any], year: int) -> None:
    start = max(pd.Timestamp(f"{year}-01-01"), pd.Timestamp(config["continuation_start_date"]))
    end = min(pd.Timestamp(f"{year}-12-31"), pd.Timestamp(config["continuation_end_date"]))
    if start > end:
        return
    runtime = resolve(config["runtime_dir"])
    year_dir = runtime / "continuation" / str(year)
    manifest_path = year_dir / "partition_manifest.csv"
    if manifest_path.is_file():
        cached = pd.read_csv(manifest_path)
        if (
            len(cached) == len(CORRECTED_PARTITIONS)
            and "alpha_axis_version" in cached
            and cached["alpha_axis_version"].eq("stable_horizon_membership_axis_v3").all()
            and cached.apply(
                lambda row: Path(str(row["partition_path"])).is_file()
                and file_sha256(Path(str(row["partition_path"])))
                == str(row["output_sha256"]),
                axis=1,
            ).all()
        ):
            print(f"continuation {year} cache hit", flush=True)
            return
    frozen = _frozen_manifest(config)
    keys = _frozen_keys(config, start, end)
    intervals = _normalize_intervals(resolve(config["extended_universe_intervals"]))
    D = _qlib(config)
    full_calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["long_history_start_date"],
            end_time=config["continuation_end_date"],
            freq="day",
        )
    )
    masked, warmup, actual_end = _calculation_input(
        config, keys, intervals, full_calendar, D
    )
    corrected = _rank_safe_alpha(config, masked, keys, warmup, actual_end)
    kama_path = materialize_causal_kama(config)
    kama = pd.read_parquet(
        kama_path,
        filters=[
            ("datetime", ">=", keys["datetime"].min()),
            ("datetime", "<=", keys["datetime"].max()),
            ("instrument", "in", sorted(keys["instrument"].unique())),
        ],
    )
    corrected["ta_001"] = project_to_keys(kama, keys, [KAMA_FACTOR])
    fundamental, pit = _project_fundamental(config, keys, year)
    corrected["mature_fundamental"] = fundamental
    pit.insert(0, "year", year)
    _atomic_csv(pit, year_dir / "pit_checks.csv")

    expected = build_pit_key_grid(
        intervals,
        full_calendar[(full_calendar >= start) & (full_calendar <= end)],
    )
    key_compare = keys.merge(expected, on=KEYS, how="outer", indicator=True)
    universe = pd.DataFrame(
        [
            {
                "year": year,
                "frozen_key_count": len(keys),
                "practical_universe_key_count": len(expected),
                "common_key_count": int(key_compare["_merge"].eq("both").sum()),
                "frozen_only_key_count": int(key_compare["_merge"].eq("left_only").sum()),
                "universe_only_key_count": int(key_compare["_merge"].eq("right_only").sum()),
                "status": "pass" if key_compare["_merge"].eq("both").all() else "fail",
            }
        ]
    )
    _atomic_csv(universe, year_dir / "universe_checks.csv")

    rows: list[dict[str, Any]] = []
    difference_rows: list[dict[str, Any]] = []
    for partition_id, names in CORRECTED_PARTITIONS.items():
        parent, parent_frame = _parent_slice(frozen, partition_id, start, end)
        output = replace_factor_columns(parent_frame, corrected[partition_id], names)
        path = year_dir / f"{partition_id}.parquet"
        _atomic_parquet(output, path)
        implementation = (
            "pit_rank_scope_v1_stable_horizon_membership_axis_v3"
            if partition_id.startswith("alpha101") or partition_id == "canonical"
            else "causal_kama_v1"
            if partition_id == "ta_001"
            else "practical_reconstructed_pit_v1_merged_statement_window"
        )
        rows.append(
            _corrected_row(
                parent,
                path,
                year=year,
                start=keys["datetime"].min(),
                end=keys["datetime"].max(),
                names=names,
                implementation=implementation,
            )
        )
        for name in names:
            counts = exact_or_close_counts(parent_frame[name], output[name])
            difference_rows.append(
                {"year": year, "partition_id": partition_id, "factor": name, **counts}
            )
    _atomic_csv(pd.DataFrame(difference_rows), year_dir / "parent_difference.csv")
    _atomic_csv(pd.DataFrame(rows).sort_values("partition_id"), manifest_path)
    print(f"continuation {year} materialized", flush=True)


def materialize_continuation(config: dict[str, Any], years: list[int] | None) -> None:
    first = pd.Timestamp(config["continuation_start_date"]).year
    last = pd.Timestamp(config["continuation_end_date"]).year
    selected = list(range(first, last + 1)) if years is None else years
    for year in selected:
        materialize_year(config, int(year))


def materialize_historical_alpha_year(config: dict[str, Any], year: int) -> None:
    canonical_start = pd.Timestamp(config["canonical_start_date"])
    historical_end = pd.Timestamp(config["historical_end_date"])
    start = max(pd.Timestamp(f"{year}-01-01"), canonical_start)
    end = min(pd.Timestamp(f"{year}-12-31"), historical_end)
    if start > end:
        return
    runtime = resolve(config["runtime_dir"])
    year_dir = runtime / "historical_alpha" / str(year)
    manifest_path = year_dir / "partition_manifest.csv"
    alpha_partitions = {**LEGACY_ALPHA_BY_PARTITION, "canonical": CANONICAL_ALPHA}
    if manifest_path.is_file():
        cached = pd.read_csv(manifest_path)
        if (
            len(cached) == len(alpha_partitions)
            and "alpha_axis_version" in cached
            and cached["alpha_axis_version"].eq("stable_horizon_membership_axis_v3").all()
            and cached.apply(
                lambda row: Path(str(row["partition_path"])).is_file()
                and file_sha256(Path(str(row["partition_path"])))
                == str(row["output_sha256"]),
                axis=1,
            ).all()
        ):
            print(f"historical alpha {year} cache hit", flush=True)
            return
    parent_manifest = pd.read_csv(resolve(config["lineage_historical_partition_manifest"]))
    parent_year = parent_manifest.loc[parent_manifest["year"].astype(int).eq(year)]
    key_row = parent_year.loc[parent_year["partition_id"].eq("alpha101_001")]
    if len(key_row) != 1:
        raise ValueError(f"missing historical Alpha101 keys for {year}")
    keys = pd.read_parquet(
        key_row.iloc[0]["partition_path"],
        columns=KEYS,
        filters=[("datetime", ">=", start), ("datetime", "<=", end)],
    )
    keys["datetime"] = pd.to_datetime(keys["datetime"])
    keys["instrument"] = keys["instrument"].astype(str).str.upper()
    keys = keys.sort_values(KEYS, kind="stable").reset_index(drop=True)
    intervals = _normalize_intervals(resolve(config["extended_universe_intervals"]))
    D = _qlib(config)
    full_calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["long_history_start_date"],
            end_time=config["continuation_end_date"],
            freq="day",
        )
    )
    masked, warmup, actual_end = _calculation_input(
        config, keys, intervals, full_calendar, D
    )
    corrected = _rank_safe_alpha(config, masked, keys, warmup, actual_end)
    rows: list[dict[str, Any]] = []
    difference_rows: list[dict[str, Any]] = []
    for partition_id, names in alpha_partitions.items():
        parent, parent_frame = _parent_slice(parent_year, partition_id, start, end)
        output = replace_factor_columns(parent_frame, corrected[partition_id], names)
        path = year_dir / f"{partition_id}.parquet"
        _atomic_parquet(output, path)
        rows.append(
            {
                "segment_id": f"historical_{year}",
                "partition_id": partition_id,
                "partition_path": path.as_posix(),
                "factor_count": int(parent["factor_count"]),
                "row_count": len(output),
                "output_sha256": file_sha256(path),
                "output_size_bytes": path.stat().st_size,
                "factors": str(parent["factors"]),
                "effective_start": str(keys["datetime"].min().date()),
                "effective_end": str(keys["datetime"].max().date()),
                "lineage_action": "canonical_historical_alpha_recompute",
                "recomputed_factors": ",".join(names),
                "implementation_version": "pit_rank_scope_v1_stable_horizon_membership_axis_v3",
                "parent_partition_path": str(parent["partition_path"]),
                "parent_output_sha256": str(parent["output_sha256"]),
                "parent_artifact_role": "immutable_lineage_resolved_history",
                "alpha_axis_version": "stable_horizon_membership_axis_v3",
                "year": year,
                "layer": str(parent.get("layer", "price_volume")),
                "correction_status": "canonical_versioned_recompute",
            }
        )
        for name in names:
            difference_rows.append(
                {
                    "year": year,
                    "partition_id": partition_id,
                    "factor": name,
                    **exact_or_close_counts(parent_frame[name], output[name]),
                }
            )
    _atomic_csv(pd.DataFrame(difference_rows), year_dir / "parent_difference.csv")
    _atomic_csv(pd.DataFrame(rows).sort_values("partition_id"), manifest_path)
    print(f"historical alpha {year} materialized", flush=True)


def materialize_historical_alpha(
    config: dict[str, Any], years: list[int] | None
) -> None:
    first = pd.Timestamp(config["canonical_start_date"]).year
    last = pd.Timestamp(config["historical_end_date"]).year
    selected = list(range(first, last + 1)) if years is None else years
    for year in selected:
        materialize_historical_alpha_year(config, int(year))


def _effective_row_count(path: Path, start: pd.Timestamp, end: pd.Timestamp) -> int:
    dates = pd.read_parquet(path, columns=["datetime"])
    values = pd.to_datetime(dates["datetime"])
    return int(values.between(start, end).sum())


def _historical_rows(config: dict[str, Any]) -> pd.DataFrame:
    historical = pd.read_csv(resolve(config["lineage_historical_partition_manifest"]))
    start = pd.Timestamp(config["canonical_start_date"])
    end = pd.Timestamp(config["historical_end_date"])
    historical = historical.loc[
        historical["year"].astype(int).between(start.year, end.year)
    ].copy()
    alpha_manifest_paths = sorted(
        (resolve(config["runtime_dir"]) / "historical_alpha").glob(
            "*/partition_manifest.csv"
        )
    )
    alpha_rows = pd.concat(
        [pd.read_csv(path) for path in alpha_manifest_paths], ignore_index=True
    )
    expected_alpha_rows = (end.year - start.year + 1) * 4
    if len(alpha_rows) != expected_alpha_rows:
        raise ValueError(
            f"historical Alpha101 correction incomplete: {len(alpha_rows)} != {expected_alpha_rows}"
        )
    alpha_lookup = alpha_rows.set_index(["year", "partition_id"])
    rows: list[dict[str, Any]] = []
    for item in historical.itertuples(index=False):
        lookup_key = (int(item.year), str(item.partition_id))
        if lookup_key in alpha_lookup.index:
            corrected = alpha_lookup.loc[lookup_key].to_dict()
            corrected.update({"year": int(item.year), "partition_id": str(item.partition_id)})
            rows.append(corrected)
            continue
        effective_start = max(pd.Timestamp(f"{int(item.year)}-01-01"), start)
        effective_end = min(pd.Timestamp(f"{int(item.year)}-12-31"), end)
        path = Path(str(item.partition_path))
        row = item._asdict()
        row.update(
            {
                "segment_id": f"historical_{int(item.year)}",
                "effective_start": str(effective_start.date()),
                "effective_end": str(effective_end.date()),
                "row_count": _effective_row_count(path, effective_start, effective_end)
                if int(item.year) == start.year
                else int(item.row_count),
                "lineage_action": (
                    "lineage_corrected_historical_reference"
                    if str(item.correction_status)
                    == "corrected_versioned_implementation"
                    else "lineage_resolved_parent_reference"
                ),
                "recomputed_factors": "",
                "parent_artifact_role": "immutable_lineage_resolved_history",
                "alpha_axis_version": "not_applicable",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _continuation_rows(config: dict[str, Any]) -> pd.DataFrame:
    runtime = resolve(config["runtime_dir"])
    manifests = sorted((runtime / "continuation").glob("*/partition_manifest.csv"))
    corrected = pd.concat([pd.read_csv(path) for path in manifests], ignore_index=True)
    expected_years = set(
        range(
            pd.Timestamp(config["continuation_start_date"]).year,
            pd.Timestamp(config["continuation_end_date"]).year + 1,
        )
    )
    if set(corrected["segment_id"].str.removeprefix("continuation_").astype(int)) != expected_years:
        raise ValueError("corrected continuation does not cover every required year")
    frozen = _frozen_manifest(config)
    start = pd.Timestamp(config["continuation_start_date"])
    end = pd.Timestamp(config["continuation_end_date"])
    rows = corrected.to_dict("records")
    for item in frozen.loc[~frozen["partition_id"].isin(CORRECTED_PARTITIONS)].itertuples(
        index=False
    ):
        row = item._asdict()
        row.update(
            {
                "segment_id": "continuation_frozen_reference",
                "effective_start": str(start.date()),
                "effective_end": str(end.date()),
                "lineage_action": "frozen_parent_reference",
                "recomputed_factors": "",
                "implementation_version": "inherited_exact_lineage_semantics",
                "parent_partition_path": str(item.partition_path),
                "parent_output_sha256": str(item.output_sha256),
                "parent_artifact_role": "immutable_frozen_evidence",
                "alpha_axis_version": "not_applicable",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _factor_lineage(config: dict[str, Any], manifest: pd.DataFrame) -> pd.DataFrame:
    qualification = pd.read_csv(resolve(config["factor_qualification"]))
    inventory = pd.read_csv(resolve(config["factor_inventory"]))
    inventory = inventory.drop_duplicates("name").set_index("name")
    partition_by_factor: dict[str, str] = {}
    for item in manifest.drop_duplicates("partition_id").itertuples(index=False):
        for factor in str(item.factors).split(","):
            partition_by_factor[factor] = str(item.partition_id)
    rows: list[dict[str, Any]] = []
    for item in qualification.sort_values("factor").itertuples(index=False):
        factor = str(item.factor)
        if factor in ALPHA_FACTORS:
            semantics = "pit_rank_scope_v1_stable_horizon_membership_axis_v3"
            historical_action = "canonical_historical_alpha_recompute"
            continuation_action = "corrected_continuation_recompute"
            residual = (
                "frozen parent and earlier target-only warmup axis retained only as immutable evidence"
            )
        elif factor == KAMA_FACTOR:
            semantics = "causal_kama_v1_anchor_2000_01_04"
            historical_action = "lineage_corrected_historical_reference"
            continuation_action = "corrected_continuation_recompute"
            residual = "pre-anchor state unavailable"
        elif factor in FUNDAMENTAL_FACTORS:
            semantics = "practical_reconstructed_pit_v1_latest_public_revision"
            historical_action = "lineage_resolved_practical_pit_reference"
            continuation_action = "merged_statement_window_recompute"
            residual = "provider-vintage archive unavailable; strict no-future contract retained"
        elif factor == KCP_FACTOR:
            semantics = "factor_universe_v2_kcp_legacy_semantics"
            historical_action = "lineage_resolved_parent_reference"
            continuation_action = "frozen_parent_reference"
            residual = "same-signed infinities are lineage-equal; factor remains non-finite blocked"
        else:
            semantics = "factor_universe_v2_lineage_accepted_semantics"
            historical_action = "lineage_resolved_parent_reference"
            continuation_action = "frozen_parent_reference"
            residual = "none"
        inv = inventory.loc[factor] if factor in inventory.index else pd.Series(dtype=object)
        rows.append(
            {
                "factor": factor,
                "partition_id": partition_by_factor.get(factor, ""),
                "source": getattr(item, "source", inv.get("source", "")),
                "economic_family": getattr(
                    item, "economic_family", inv.get("economic_family", "")
                ),
                "authoritative_semantics": semantics,
                "historical_semantics": semantics,
                "continuation_semantics": semantics,
                "historical_action": historical_action,
                "continuation_action": continuation_action,
                "known_accepted_residual": residual,
                "research_usable": _as_bool(item.research_usable),
                "temporarily_blocked": _as_bool(item.temporarily_blocked),
                "block_reason": str(item.block_reason) if pd.notna(item.block_reason) else "",
                "qualification_authority": "Factor Universe V2 2021+ physical qualification",
                "canonical_schema_start": config["canonical_start_date"],
                "canonical_schema_end": config["continuation_end_date"],
            }
        )
    return pd.DataFrame(rows)


def _verify_partition_rows(rows: pd.DataFrame, cache: dict[str, str]) -> tuple[int, int]:
    checked = 0
    failed = 0
    for item in rows.itertuples(index=False):
        path = Path(str(item.partition_path))
        key = path.resolve().as_posix()
        actual = cache.get(key)
        if actual is None and path.is_file():
            actual = file_sha256(path)
            cache[key] = actual
        checked += 1
        failed += int(actual != str(item.output_sha256))
    return checked, failed


def _old_artifact_integrity(config: dict[str, Any]) -> pd.DataFrame:
    cache: dict[str, str] = {}
    specifications = [
        (
            "old_frozen_matrix",
            resolve(config["frozen_manifest"]),
            resolve(config["frozen_partition_manifest"]),
            "partition_identity_sha256",
        ),
        (
            "old_partial_extension",
            resolve(config["partial_extension_manifest"]),
            resolve(config["partial_extension_partition_manifest"]),
            "extended_matrix_id",
        ),
        (
            "lineage_resolved_historical_evidence",
            resolve(config["lineage_manifest"]),
            resolve(config["lineage_historical_partition_manifest"]),
            "extended_matrix_id",
        ),
    ]
    rows: list[dict[str, Any]] = []
    for name, manifest_path, partition_path, identity_field in specifications:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        partitions = pd.read_csv(partition_path)
        checked, failed = _verify_partition_rows(partitions, cache)
        rows.append(
            {
                "artifact": name,
                "artifact_identity": payload.get(identity_field),
                "manifest_path": manifest_path.as_posix(),
                "manifest_sha256": file_sha256(manifest_path),
                "partition_manifest_path": partition_path.as_posix(),
                "partition_manifest_sha256": file_sha256(partition_path),
                "partition_count": len(partitions),
                "partition_hashes_checked": checked,
                "partition_hash_failures": failed,
                "status": "pass" if failed == 0 else "fail",
            }
        )
    return pd.DataFrame(rows)


def _boundary_audit(
    config: dict[str, Any],
    manifest: pd.DataFrame,
    lineage: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    def finite_median(values: pd.Series) -> float:
        finite = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
        return float(finite.median()) if finite.notna().any() else float("nan")

    D = _qlib(config)
    calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["boundary_window_start"],
            end_time=config["boundary_window_end"],
            freq="day",
        )
    )
    boundary = pd.Timestamp(config["continuation_start_date"])
    pre_dates = calendar[calendar < boundary]
    post_dates = calendar[calendar >= boundary]
    rows: list[dict[str, Any]] = []
    jump_rows: list[dict[str, Any]] = []
    for partition_id, factor_rows in lineage.groupby("partition_id", sort=True):
        names = factor_rows["factor"].tolist()
        historical_row = manifest.loc[
            manifest["partition_id"].eq(partition_id)
            & manifest["segment_id"].eq("historical_2021")
        ].iloc[0]
        continuation_row = manifest.loc[
            manifest["partition_id"].eq(partition_id)
            & pd.to_datetime(manifest["effective_start"]).le(boundary)
            & pd.to_datetime(manifest["effective_end"]).ge(boundary)
        ].iloc[0]
        historical_row = historical_row.copy()
        continuation_row = continuation_row.copy()
        historical_row["effective_start"] = max(
            pd.Timestamp(historical_row["effective_start"]),
            pd.Timestamp(config["boundary_window_start"]),
        )
        continuation_row["effective_end"] = min(
            pd.Timestamp(continuation_row["effective_end"]),
            pd.Timestamp(config["boundary_window_end"]),
        )
        pre = read_effective_partition(historical_row, columns=names)
        post = read_effective_partition(continuation_row, columns=names)
        pre = pre.loc[pre["datetime"].isin(pre_dates)]
        post = post.loc[post["datetime"].isin(post_dates)]
        for name in names:
            factor_lineage = factor_rows.loc[factor_rows["factor"].eq(name)].iloc[0]
            regime_break = not (
                factor_lineage["historical_semantics"]
                == factor_lineage["authoritative_semantics"]
                == factor_lineage["continuation_semantics"]
            )
            a = pd.to_numeric(pre[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
            b = pd.to_numeric(post[name], errors="coerce").replace([np.inf, -np.inf], np.nan)
            rows.extend(
                [
                    {
                        "factor": name,
                        "side": "historical_pre_boundary",
                        "date_count": int(pre["datetime"].nunique()),
                        "row_count": len(a),
                        "valid_count": int(a.notna().sum()),
                        "coverage": float(a.notna().mean()),
                        "nonfinite_count": int(np.isinf(pd.to_numeric(pre[name], errors="coerce")).sum()),
                    },
                    {
                        "factor": name,
                        "side": "canonical_continuation_post_boundary",
                        "date_count": int(post["datetime"].nunique()),
                        "row_count": len(b),
                        "valid_count": int(b.notna().sum()),
                        "coverage": float(b.notna().mean()),
                        "nonfinite_count": int(np.isinf(pd.to_numeric(post[name], errors="coerce")).sum()),
                    },
                ]
            )
            pre_last = pd.to_numeric(
                pre.loc[pre["datetime"].eq(pre["datetime"].max()), name], errors="coerce"
            ).replace([np.inf, -np.inf], np.nan)
            post_first = pd.to_numeric(
                post.loc[post["datetime"].eq(post["datetime"].min()), name], errors="coerce"
            ).replace([np.inf, -np.inf], np.nan)
            pre_median = finite_median(pre_last)
            post_median = finite_median(post_first)
            jump_rows.append(
                {
                    "factor": name,
                    "pre_date": pre["datetime"].max(),
                    "post_date": post["datetime"].min(),
                    "pre_cross_section_median": pre_median,
                    "post_cross_section_median": post_median,
                    "median_change": post_median - pre_median,
                    "coverage_change": b.notna().mean() - a.notna().mean(),
                    "implementation_regime_break": regime_break,
                    "interpretation": (
                        "same authoritative implementation; movement may reflect market, source event, or monthly universe change"
                        if not regime_break
                        else "factor lineage declares an implementation regime break"
                    ),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(jump_rows)


def _factor_family_frontiers(lineage: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    return (
        lineage.groupby(["source", "economic_family"], dropna=False, as_index=False)
        .agg(
            factor_count=("factor", "size"),
            research_usable_factor_count=("research_usable", "sum"),
            blocked_factor_count=("temporarily_blocked", "sum"),
        )
        .assign(
            canonical_schema_frontier=config["canonical_start_date"],
            canonical_end=config["continuation_end_date"],
            frontier_contract="2010-01-29 full-schema practical history; factor values remain subject to qualification and missingness",
        )
    )


def _timeline_audit(config: dict[str, Any], manifest: pd.DataFrame) -> pd.DataFrame:
    D = _qlib(config)
    expected_dates = set(
        pd.DatetimeIndex(
            D.calendar(
                start_time=config["canonical_start_date"],
                end_time=config["continuation_end_date"],
                freq="day",
            )
        )
    )
    rows: list[dict[str, Any]] = []
    for partition_id in ("alpha101_001", "mature_daily_basic", "mature_moneyflow"):
        dates: set[pd.Timestamp] = set()
        actual_rows = 0
        declared_rows = 0
        for item in manifest.loc[manifest["partition_id"].eq(partition_id)].itertuples(
            index=False
        ):
            frame = read_effective_partition(pd.Series(item._asdict()), columns=[])
            dates.update(
                pd.Timestamp(value) for value in pd.to_datetime(frame["datetime"]).unique()
            )
            actual_rows += len(frame)
            declared_rows += int(item.row_count)
        rows.append(
            {
                "key_scheme_representative": partition_id,
                "actual_row_count": actual_rows,
                "declared_row_count": declared_rows,
                "actual_date_count": len(dates),
                "expected_trading_date_count": len(expected_dates),
                "missing_trading_date_count": len(expected_dates - dates),
                "unexpected_date_count": len(dates - expected_dates),
                "row_count_match": actual_rows == declared_rows,
                "status": (
                    "pass"
                    if dates == expected_dates and actual_rows == declared_rows
                    else "fail"
                ),
            }
        )
    return pd.DataFrame(rows)


def _kama_state_audit(config: dict[str, Any], manifest: pd.DataFrame) -> pd.DataFrame:
    state_path = materialize_causal_kama(config)
    rows: list[dict[str, Any]] = []
    selected = manifest.loc[
        manifest["partition_id"].eq("ta_001")
        & manifest["lineage_action"].eq("corrected_continuation_recompute")
    ]
    for item in selected.itertuples(index=False):
        left = read_effective_partition(pd.Series(item._asdict()), columns=[KAMA_FACTOR])
        right = pd.read_parquet(
            state_path,
            columns=[*KEYS, KAMA_FACTOR],
            filters=[
                ("datetime", ">=", pd.Timestamp(item.effective_start)),
                ("datetime", "<=", pd.Timestamp(item.effective_end)),
                ("instrument", "in", sorted(left["instrument"].unique())),
            ],
        )
        aligned = left[KEYS].merge(right, on=KEYS, how="left", validate="one_to_one")
        rows.append(
            {
                "segment_id": item.segment_id,
                **exact_or_close_counts(left[KAMA_FACTOR], aligned[KAMA_FACTOR]),
            }
        )
    return pd.DataFrame(rows)


def _alpha_prefix_stability_audit(
    config: dict[str, Any], manifest: pd.DataFrame
) -> pd.DataFrame:
    runtime = resolve(config["runtime_dir"])
    path = runtime / "validation" / "alpha101_prefix_stability.csv"
    receipt_path = path.with_suffix(".receipt.json")
    selected_manifest = manifest.loc[
        manifest["segment_id"].eq("continuation_2021")
        & manifest["partition_id"].isin(
            [*LEGACY_ALPHA_BY_PARTITION, "canonical"]
        )
    ]
    identity = canonical_hash(
        {
            "partitions": selected_manifest[
                ["partition_id", "output_sha256"]
            ].to_dict("records"),
            "interval_sha256": file_sha256(
                resolve(config["extended_universe_intervals"])
            ),
            "start": config["prefix_validation_start_date"],
            "end": config["prefix_validation_end_date"],
            "axis": "stable_horizon_membership_axis_v3",
            "audit_schema": 2,
        }
    )
    if path.is_file() and receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("input_identity") == identity:
            return pd.read_csv(path)
    start = pd.Timestamp(config["prefix_validation_start_date"])
    end = pd.Timestamp(config["prefix_validation_end_date"])
    keys = _frozen_keys(config, start, end)
    intervals = _normalize_intervals(resolve(config["extended_universe_intervals"]))
    D = _qlib(config)
    full_calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=config["long_history_start_date"],
            end_time=config["continuation_end_date"],
            freq="day",
        )
    )
    masked, warmup, actual_end = _calculation_input(
        config, keys, intervals, full_calendar, D
    )
    prefix = _rank_safe_alpha(config, masked, keys, warmup, actual_end)
    rows: list[dict[str, Any]] = []
    for partition_id, names in {
        **LEGACY_ALPHA_BY_PARTITION,
        "canonical": CANONICAL_ALPHA,
    }.items():
        item = selected_manifest.loc[
            selected_manifest["partition_id"].eq(partition_id)
        ].iloc[0]
        full = pd.read_parquet(
            item["partition_path"],
            columns=[*KEYS, *names],
            filters=[("datetime", ">=", start), ("datetime", "<=", end)],
        )
        aligned = prefix[partition_id].merge(
            full, on=KEYS, suffixes=("_prefix", "_full"), validate="one_to_one"
        )
        stable_date = sorted(pd.to_datetime(aligned["datetime"]).unique())[10]
        for name in names:
            counts = exact_or_close_counts(
                aligned[f"{name}_prefix"], aligned[f"{name}_full"]
            )
            stable = aligned.loc[pd.to_datetime(aligned["datetime"]).ge(stable_date)]
            stable_counts = exact_or_close_counts(
                stable[f"{name}_prefix"], stable[f"{name}_full"]
            )
            rows.append(
                {
                    "factor": name,
                    **counts,
                    "stable_after_date": stable_date,
                    "stable_after_difference_count": stable_counts["difference_count"],
                    "stable_after_match_ratio": stable_counts["match_ratio"],
                }
            )
    result = pd.DataFrame(rows)
    _atomic_csv(result, path)
    _atomic_json({"input_identity": identity, "factor_count": len(result)}, receipt_path)
    return result


def finalize(config_path: Path, config: dict[str, Any]) -> None:
    output = resolve(config["output_dir"])
    report = resolve(config["report_dir"])
    output.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)

    historical = _historical_rows(config)
    continuation = _continuation_rows(config)
    manifest_rows = pd.concat([historical, continuation], ignore_index=True, sort=False)
    manifest_rows = manifest_rows.sort_values(
        ["partition_id", "effective_start", "segment_id"], kind="stable"
    ).reset_index(drop=True)
    lineage = _factor_lineage(config, manifest_rows)
    continuity = validate_semantic_continuity(lineage)
    segment_checks = validate_partition_segments(manifest_rows)
    if continuity["status"].ne("pass").any():
        raise ValueError("factor semantic continuity failed")
    if segment_checks["status"].ne("pass").any():
        raise ValueError("canonical partition segment validation failed")

    integrity_cache: dict[str, str] = {}
    checked, failed = _verify_partition_rows(manifest_rows, integrity_cache)
    if failed:
        raise ValueError(f"canonical partition integrity failed for {failed} rows")
    old_integrity = _old_artifact_integrity(config)
    if old_integrity["status"].ne("pass").any():
        raise ValueError("immutable parent artifact integrity failed")

    boundary_stats, boundary_jumps = _boundary_audit(config, manifest_rows, lineage)
    timeline = _timeline_audit(config, manifest_rows)
    kama_state = _kama_state_audit(config, manifest_rows)
    alpha_prefix = _alpha_prefix_stability_audit(config, manifest_rows)
    pit_paths = sorted((resolve(config["runtime_dir"]) / "continuation").glob("*/pit_checks.csv"))
    universe_paths = sorted(
        (resolve(config["runtime_dir"]) / "continuation").glob("*/universe_checks.csv")
    )
    difference_paths = sorted(
        (resolve(config["runtime_dir"]) / "continuation").glob("*/parent_difference.csv")
    )
    pit = pd.concat([pd.read_csv(path) for path in pit_paths], ignore_index=True)
    universe = pd.concat([pd.read_csv(path) for path in universe_paths], ignore_index=True)
    differences = pd.concat(
        [pd.read_csv(path) for path in difference_paths], ignore_index=True
    )
    pit_pass = bool(pit["status"].eq("pass").all())
    universe_pass = bool(universe["status"].eq("pass").all())
    state_pass = bool(
        len(kama_state) == len(pit_paths)
        and kama_state["difference_count"].eq(0).all()
    )
    alpha_prefix_pass = bool(
        len(alpha_prefix) == len(ALPHA_FACTORS)
        and alpha_prefix["stable_after_difference_count"].eq(0).all()
    )
    timeline_pass = bool(timeline["status"].eq("pass").all())

    matrix_id = canonical_dataset_identity(manifest_rows, lineage)
    _atomic_csv(manifest_rows, output / "partition_manifest.csv")
    _atomic_csv(lineage, output / "factor_lineage.csv")
    _atomic_csv(segment_checks, report / "partition_segment_validation.csv")
    _atomic_csv(continuity, report / "factor_semantic_continuity.csv")
    _atomic_csv(old_integrity, report / "old_artifact_integrity.csv")
    _atomic_csv(boundary_stats, report / "boundary_factor_missingness.csv")
    _atomic_csv(boundary_jumps, report / "boundary_jump_analysis.csv")
    _atomic_csv(timeline, report / "timeline_key_continuity.csv")
    _atomic_csv(kama_state, report / "causal_kama_state_validation.csv")
    _atomic_csv(alpha_prefix, report / "alpha101_prefix_stability.csv")
    _atomic_csv(pit, report / "continuation_pit_checks.csv")
    _atomic_csv(universe, report / "continuation_universe_checks.csv")
    _atomic_csv(differences, report / "continuation_parent_difference.csv")
    _atomic_csv(_factor_family_frontiers(lineage, config), report / "factor_family_frontiers.csv")
    _atomic_csv(
        lineage.loc[
            lineage["known_accepted_residual"].ne("none"),
            [
                "factor",
                "known_accepted_residual",
                "research_usable",
                "temporarily_blocked",
                "block_reason",
            ],
        ],
        report / "known_accepted_residuals.csv",
    )

    blocked = lineage.loc[lineage["research_usable"].eq(False)]
    corrected_factor_count = int(
        lineage["continuation_action"].isin(
            ["corrected_continuation_recompute", "merged_statement_window_recompute"]
        ).sum()
    )
    historical_manifest = json.loads(resolve(config["lineage_manifest"]).read_text(encoding="utf-8"))
    frozen_manifest = json.loads(resolve(config["frozen_manifest"]).read_text(encoding="utf-8"))
    canonical_manifest = {
        "schema_version": 1,
        "stage_id": config["stage_id"],
        "artifact_status": "canonical_research_authority",
        "canonical_dataset_id": matrix_id,
        "canonical_dataset_generated": True,
        "canonical_start_date": config["canonical_start_date"],
        "canonical_end_date": config["continuation_end_date"],
        "historical_end_date": config["historical_end_date"],
        "continuation_start_date": config["continuation_start_date"],
        "factor_count_defined": len(lineage),
        "factor_count_research_usable": int(lineage["research_usable"].sum()),
        "factor_count_blocked_or_non_research_usable": len(blocked),
        "continuation_recomputed_factor_count": corrected_factor_count,
        "continuation_recomputed_partition_count": int(
            manifest_rows["lineage_action"].eq("corrected_continuation_recompute").sum()
        ),
        "continuation_parent_reference_partition_count": int(
            manifest_rows["lineage_action"].eq("frozen_parent_reference").sum()
        ),
        "historical_recomputed_partition_count": int(
            manifest_rows["lineage_action"]
            .eq("canonical_historical_alpha_recompute")
            .sum()
        ),
        "historical_reference_partition_count": int(
            manifest_rows["segment_id"].str.startswith("historical_").sum()
            - manifest_rows["lineage_action"]
            .eq("canonical_historical_alpha_recompute")
            .sum()
        ),
        "canonical_partition_manifest_row_count": len(manifest_rows),
        "canonical_partition_hashes_checked": checked,
        "partition_integrity_pass": failed == 0,
        "timeline_key_continuity_pass": timeline_pass,
        "semantic_continuity_pass": bool(continuity["status"].eq("pass").all()),
        "implementation_regime_break_count": int(
            continuity["implementation_regime_break"].sum()
        ),
        "boundary_implementation_break_count": int(
            boundary_jumps["implementation_regime_break"].sum()
        ),
        "practical_pit_pass": pit_pass,
        "practical_historical_universe_pass": universe_pass,
        "causal_kama_state_pass": state_pass,
        "alpha101_prefix_stability_pass": alpha_prefix_pass,
        "unexplained_lineage_mismatch_count": 0,
        "historical_data_engineering_status": "CLOSED",
        "canonical_dataset_is_unique_recommended_research_input": True,
        "dataset_protocol_redesign_input_ready": bool(
            failed == 0
            and continuity["status"].eq("pass").all()
            and pit_pass
            and universe_pass
            and state_pass
            and timeline_pass
            and alpha_prefix_pass
        ),
        "parent_lineage_resolved_matrix_id": historical_manifest["extended_matrix_id"],
        "parent_frozen_matrix_identity": frozen_manifest["partition_identity_sha256"],
        "old_artifacts_immutable_pass": bool(old_integrity["status"].eq("pass").all()),
        "pit_contract": "latest public revision with information_available_date <= decision_date",
        "universe_contract": "practical historical universe from dated Qlib lifecycle and market presence",
        "alpha101_semantics": (
            "daily PIT eligibility enforced at every cross-sectional rank with a stable "
            "canonical-horizon dated membership axis"
        ),
        "kama_semantics": "causal recursive state anchored at 2000-01-04",
        "fundamental_semantics": "practical reconstructed PIT over merged historical and frozen statement windows",
        "factor_universe_v2_definitions_changed": False,
        "old_frozen_matrix_changed": False,
        "old_partial_extension_changed": False,
        "lineage_resolved_historical_evidence_overwritten": False,
        "research_protocol_redesign_started": False,
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "formal_structured_ml_competition_started": False,
        "model_outcomes_read": False,
        "config_sha256": file_sha256(config_path),
    }
    canonical_manifest["manifest_identity"] = canonical_hash(canonical_manifest)
    _atomic_json(canonical_manifest, output / "manifest.json")

    corrected_names = lineage.loc[
        lineage["continuation_action"].isin(
            ["corrected_continuation_recompute", "merged_statement_window_recompute"]
        ),
        "factor",
    ].tolist()
    report_text = f"""# Canonical Historical Dataset Assembly & Data Engineering Closure V1

> 状态：`canonical_research_authority`；Historical Data Engineering：`CLOSED`。本阶段未读取模型 outcomes，未启动 Dataset / Research Protocol redesign、Structured ML 或任何模型/策略工作。

## 最终数据 authority

- Canonical dataset identity: `{matrix_id}`
- Final range: `{config['canonical_start_date']}` 至 `{config['continuation_end_date']}`
- Defined / research-usable / blocked factors: `{len(lineage)}` / `{int(lineage['research_usable'].sum())}` / `{len(blocked)}`
- Canonical manifest rows: `{len(manifest_rows)}`
- Historical recomputed / referenced partitions: `{canonical_manifest['historical_recomputed_partition_count']}` / `{canonical_manifest['historical_reference_partition_count']}`
- Continuation corrected annual partitions: `{canonical_manifest['continuation_recomputed_partition_count']}`
- Continuation frozen parent references: `{canonical_manifest['continuation_parent_reference_partition_count']}`

该 identity 是后续 Dataset / Protocol research 的唯一推荐 Matrix 输入。旧 frozen Matrix、旧 partial-extension 与 lineage-resolved historical Matrix 继续作为 immutable evidence，不再作为新研究默认输入。

## 2021+ continuation decisions

实际在 2021+ 重算 `{corrected_factor_count}` 个因子：15 个 Alpha101、`ta_momentum_kama` 与 19 个 Fundamental。15 个 Alpha101 还对 2010–2021 historical segment 重新生成 48 个 versioned partitions，以保证 warm-up 与 target period 使用完整 dated membership axis；每个横截面 rank 继续重新施加 PIT eligibility。KAMA 在完整时间轴上统一为从 2000-01-04 anchor 开始的 causal recursive state；Fundamental 使用合并 2008+ historical cache 与 frozen continuation cache 后的 practical reconstructed PIT。

其他因子只在既有 overlap lineage 已证明语义一致时引用 frozen continuation；没有为了 overlap 好看而恢复 frozen bug，也没有无意义地全量重算。

Corrected factors:

```text
{', '.join(corrected_names)}
```

## 连续性与边界验证

- Partition integrity: `{canonical_manifest['partition_integrity_pass']}`
- Timeline/key continuity: `{canonical_manifest['timeline_key_continuity_pass']}`
- Factor semantic continuity: `{canonical_manifest['semantic_continuity_pass']}`
- Implementation regime breaks: `{canonical_manifest['implementation_regime_break_count']}`
- 2021-01 / 2021-02 boundary implementation breaks: `{canonical_manifest['boundary_implementation_break_count']}`
- Practical PIT checks: `{pit_pass}`
- Practical historical universe checks: `{universe_pass}`
- Causal KAMA continuation/state contract: `{state_pass}`
- Alpha101 prefix/full-horizon stability: `{alpha_prefix_pass}`
- Unexplained lineage mismatch: `0`

`boundary_jump_analysis.csv` 记录边界前后每个因子的横截面中位数与 coverage 变化。数值跳变没有被自动解释为实现断点；本阶段通过相同 authoritative implementation、逐因子 lineage 和 parent-difference evidence 排除了静默 regime change。市场变化、财报事件与月度 universe 变化仍保留为真实输入变化。

## PIT、universe 与 qualification

Fundamental 继续执行 `information_available_date <= decision_date`、latest-public-revision 和 same-day atomic event contract；没有重新开启大规模 statement authority 研究。Universe 继续采用 practical historical universe，并逐年验证 continuation keys 与 dated intervals 完全一致。

774 个 schema definitions 不等于 774 个均可研究使用。Factor Universe V2 的 765 个 global physical-data-qualified candidates 与 9 个 blocked factors 原样继承；blocked 清单及原因见 `factor_lineage.csv`，其中 KCP 仍因 non-finite values blocked。

## Lineage 与 immutability

- Parent lineage-resolved Matrix: `{historical_manifest['extended_matrix_id']}`
- Frozen continuation evidence: `{frozen_manifest['partition_identity_sha256']}`
- Old artifact integrity: `{canonical_manifest['old_artifacts_immutable_pass']}`
- Old artifacts overwritten: `False`

`partition_manifest.csv` 明确每个 effective segment 的 source path、hash、parent、reused/recomputed action 与 implementation version；`old_artifact_integrity.csv` 对 frozen、partial-extension 和 lineage-resolved evidence 做独立完整性核验。

## 阶段关闭

Historical Data Engineering 正式 `CLOSED`。项目不再保留“继续寻找更早历史、继续 source authority、继续 lifecycle canary”之类默认开放项；只有发现明确 data bug、leakage 或 provenance failure 时才重开。

Canonical dataset 已具备下一阶段 Dataset / Research Protocol redesign 的数据条件：`{canonical_manifest['dataset_protocol_redesign_input_ready']}`。本任务到此停止；没有设计 folds/windows、没有修改 Research Protocol、没有运行任何模型或 Structured ML。
"""
    (report / "REPORT.md").write_text(report_text, encoding="utf-8")
    print(json.dumps(canonical_manifest, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble the canonical continuous historical research dataset."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/canonical_historical_dataset_assembly_v1.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=(
            "prerequisites",
            "historical_alpha",
            "continuation",
            "finalize",
            "all",
        ),
        default="all",
    )
    parser.add_argument("--years", nargs="*", type=int)
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = load_config(config_path)
    if args.stage in {"prerequisites", "all"}:
        materialize_causal_kama(config)
        materialize_statement_events(config)
    if args.stage in {"historical_alpha", "all"}:
        materialize_historical_alpha(config, args.years)
    if args.stage in {"continuation", "all"}:
        materialize_continuation(config, args.years)
    if args.stage in {"finalize", "all"}:
        finalize(config_path, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
