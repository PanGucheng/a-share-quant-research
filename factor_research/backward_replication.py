from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
import yaml

from research_validation.canonical_dataset import (
    canonical_dataset_identity,
    canonical_hash,
    read_effective_partition,
)


KEYS = ["datetime", "instrument"]
RECONCILIATION_STATUSES = {
    "consistent",
    "minor_drift",
    "material_data_semantic_change",
    "metric_definition_mismatch",
    "universe_not_comparable",
    "unsigned_feature",
    "insufficient_history",
    "not_comparable",
}
PORTABILITY_STATUSES = {
    "persistent",
    "weaker_early",
    "stronger_early",
    "recent_regime_concentrated",
    "direction_conflict",
    "insufficient_history",
    "unsigned_feature",
    "not_comparable",
}


@dataclass(frozen=True)
class Phase0Inputs:
    config: dict[str, Any]
    inventory: pd.DataFrame
    computation_universe: pd.DataFrame
    partition_manifest: pd.DataFrame
    factor_lineage: pd.DataFrame
    source_hashes: dict[str, str]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_phase0_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Phase 0 config must be a mapping")
    return payload


def _path(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def _require_file(root: Path, value: str, label: str) -> Path:
    candidate = _path(root, value)
    if not candidate.is_file():
        raise FileNotFoundError(f"missing required Phase 0 parent {label}: {candidate}")
    return candidate


def _verify_sha(path: Path, expected: str, label: str) -> str:
    observed = file_sha256(path)
    if observed != expected.lower():
        raise ValueError(
            f"{label} SHA256 mismatch: expected={expected.lower()} observed={observed}"
        )
    return observed


def _source_row(
    *,
    factor: str,
    old_source: str,
    old_context: str,
    old_role: str,
    old_direction: float | None,
    direction_status: str,
    direction_authority: str,
    source_path: Path,
    source_sha: str,
    old_cluster_id: str = "",
    old_is_representative: bool | None = None,
    old_order: int | None = None,
) -> dict[str, Any]:
    return {
        "factor": factor,
        "old_source": old_source,
        "old_context": old_context,
        "old_role": old_role,
        "old_direction": old_direction,
        "direction_status": direction_status,
        "direction_authority": direction_authority,
        "old_cluster_id": old_cluster_id,
        "old_is_representative": old_is_representative,
        "old_order": old_order,
        "source_path": source_path.as_posix(),
        "source_artifact_id_or_sha256": source_sha,
    }


def _validate_unique(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    duplicate = frame.duplicated(columns, keep=False)
    if duplicate.any():
        sample = frame.loc[duplicate, columns].head(5).to_dict("records")
        raise ValueError(f"duplicate {label} keys for {columns}: {sample}")


def _read_csv(path: Path, required: Iterable[str]) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{path} missing required columns: {missing}")
    return frame


def preflight_phase0(
    config: dict[str, Any],
    *,
    root: Path,
    factor_read_probe: Callable[[], None] | None = None,
) -> Phase0Inputs:
    """Verify every frozen parent and build inventories without reading factor values."""
    del factor_read_probe  # A probe exists for tests: this function must never invoke it.
    canonical_manifest_path = _require_file(
        root, config["canonical_manifest"], "canonical manifest"
    )
    partition_path = _require_file(root, config["partition_manifest"], "partition manifest")
    lineage_path = _require_file(root, config["factor_lineage"], "factor lineage")
    canonical_manifest = json.loads(canonical_manifest_path.read_text(encoding="utf-8"))
    expected_identity = str(config["canonical_dataset_id"])
    if canonical_manifest.get("canonical_dataset_id") != expected_identity:
        raise ValueError(
            "canonical manifest identity mismatch: "
            f"expected={expected_identity} observed={canonical_manifest.get('canonical_dataset_id')}"
        )
    partition_manifest = pd.read_csv(partition_path)
    factor_lineage = pd.read_csv(lineage_path)
    observed_identity = canonical_dataset_identity(partition_manifest, factor_lineage)
    if observed_identity != expected_identity:
        raise ValueError(
            f"canonical dataset identity mismatch: expected={expected_identity} "
            f"observed={observed_identity}"
        )

    source_hashes: dict[str, str] = {
        "canonical_manifest": file_sha256(canonical_manifest_path),
        "partition_manifest": file_sha256(partition_path),
        "factor_lineage": file_sha256(lineage_path),
    }
    strategy = config["strategy_v1"]
    freeze_path = _require_file(root, strategy["freeze"], "Strategy V1 freeze")
    preprocessing_path = _require_file(
        root, strategy["preprocessing"], "Strategy V1 preprocessing"
    )
    source_hashes["strategy_freeze"] = _verify_sha(
        freeze_path, strategy["freeze_sha256"], "Strategy V1 freeze"
    )
    source_hashes["strategy_preprocessing"] = _verify_sha(
        preprocessing_path,
        strategy["preprocessing_sha256"],
        "Strategy V1 preprocessing",
    )
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    preprocessing = json.loads(preprocessing_path.read_text(encoding="utf-8"))
    strategy_factors = [str(item) for item in preprocessing.get("feature_names", [])]
    if len(strategy_factors) != int(strategy["expected_count"]):
        raise ValueError(
            f"Strategy V1 factor count drift: expected={strategy['expected_count']} "
            f"observed={len(strategy_factors)}"
        )
    if len(strategy_factors) != len(set(strategy_factors)):
        raise ValueError("Strategy V1 feature_names contains duplicates")
    feature_hash = canonical_hash(strategy_factors)
    expected_feature_hash = str(strategy["expected_feature_order_sha256"])
    if feature_hash != expected_feature_hash or freeze.get("feature_order_sha256") != feature_hash:
        raise ValueError("Strategy V1 feature order identity mismatch")
    if freeze.get("factor_count") != len(strategy_factors):
        raise ValueError("Strategy V1 freeze factor_count disagrees with preprocessing")

    economic = config["economic"]
    economic_map_path = _require_file(root, economic["map"], "economic map")
    economic_manifest_path = _require_file(root, economic["manifest"], "economic manifest")
    literature_path = _require_file(root, economic["literature_map"], "literature map")
    source_hashes["economic_map"] = _verify_sha(
        economic_map_path, economic["map_sha256"], "economic map"
    )
    source_hashes["economic_manifest"] = _verify_sha(
        economic_manifest_path, economic["manifest_sha256"], "economic manifest"
    )
    source_hashes["literature_map"] = _verify_sha(
        literature_path, economic["literature_map_sha256"], "literature map"
    )
    economic_map = _read_csv(
        economic_map_path,
        ["factor", "research_role", "sleeve_id", "expected_direction", "mechanism"],
    )
    mature = economic_map.loc[
        economic_map["research_role"].eq(economic["membership_filter"])
    ].copy()
    if len(mature) != int(economic["expected_count"]) or mature["factor"].nunique() != len(mature):
        raise ValueError(
            f"mature economic factor count drift: expected={economic['expected_count']} "
            f"rows={len(mature)} unique={mature['factor'].nunique()}"
        )
    directions = pd.to_numeric(mature["expected_direction"], errors="coerce")
    if not directions.isin([-1, 1]).all():
        raise ValueError("mature economic factors require predeclared +/-1 directions")
    mature["expected_direction"] = directions.astype(int)

    stability = config["stability"]
    stability_paths = {
        key: _require_file(root, stability[key], f"stability {key}")
        for key in (
            "board",
            "direction_history",
            "window_metrics",
            "selection_history",
            "resolved_config",
            "date_assignments",
        )
    }
    source_hashes.update(
        {
            f"stability_{key}": _verify_sha(
                path, stability[f"{key}_sha256"], f"stability {key}"
            )
            for key, path in stability_paths.items()
        }
    )
    board = _read_csv(
        stability_paths["board"],
        ["outer_split_id", "factor", "frozen_direction", "stability_role"],
    )
    direction_history = _read_csv(
        stability_paths["direction_history"],
        ["outer_split_id", "inner_split_id", "factor", "frozen_direction"],
    )
    window_metrics = _read_csv(
        stability_paths["window_metrics"],
        ["outer_split_id", "inner_split_id", "factor", "frozen_direction"],
    )
    selection_history = _read_csv(
        stability_paths["selection_history"],
        ["outer_split_id", "inner_split_id", "factor", "selected", "selection_reason"],
    )
    _validate_unique(board, ["outer_split_id", "factor"], "stability board")
    _validate_unique(
        direction_history,
        ["outer_split_id", "inner_split_id", "factor"],
        "direction history",
    )
    _validate_unique(
        window_metrics,
        ["outer_split_id", "inner_split_id", "factor"],
        "window metrics",
    )
    _validate_unique(
        selection_history,
        ["outer_split_id", "inner_split_id", "factor"],
        "selection history",
    )

    clustering = config["clustering"]
    representative_path = _require_file(
        root, clustering["representatives"], "cluster representatives"
    )
    membership_path = _require_file(root, clustering["memberships"], "cluster memberships")
    source_hashes["cluster_representatives"] = _verify_sha(
        representative_path,
        clustering["representatives_sha256"],
        "cluster representatives",
    )
    source_hashes["cluster_memberships"] = _verify_sha(
        membership_path, clustering["memberships_sha256"], "cluster memberships"
    )
    representatives = _read_csv(
        representative_path,
        ["outer_split_id", "cluster_id", "factor", "is_representative"],
    )
    memberships = _read_csv(
        membership_path, ["outer_split_id", "factor", "cluster_id"]
    )
    _validate_unique(memberships, ["outer_split_id", "factor"], "cluster membership")

    computation = config["computation"]
    extras = computation.get("explicit_extras", [])
    if extras:
        for item in extras:
            if not item.get("frozen_source") or not item.get("non_performance_reason"):
                raise ValueError("every explicit extra needs frozen_source and non_performance_reason")
    extra_factors = [str(item["factor"]) for item in extras]
    if len(extra_factors) != len(set(extra_factors)):
        raise ValueError("explicit extras contain duplicate factors")
    mature_factors = mature["factor"].astype(str).tolist()
    union = sorted(set(strategy_factors) | set(mature_factors) | set(extra_factors))
    if len(union) != int(computation["expected_unique_count"]):
        raise ValueError(
            f"computation universe count drift: expected={computation['expected_unique_count']} "
            f"observed={len(union)}"
        )
    if canonical_hash(union) != str(computation["expected_union_sha256"]):
        raise ValueError("computation universe identity drift")

    usable = factor_lineage.copy()
    usable["factor"] = usable["factor"].astype(str)
    usable_names = set(
        usable.loc[usable["research_usable"].astype(str).str.lower().isin(["true", "1"]), "factor"]
    )
    missing_usable = sorted(set(union) - usable_names)
    if missing_usable:
        raise ValueError(f"computation factors absent from canonical usable lineage: {missing_usable}")
    partition_factors = set()
    for value in partition_manifest["factors"].dropna().astype(str):
        partition_factors.update(part.strip() for part in value.split(",") if part.strip())
    missing_partitions = sorted(set(union) - partition_factors)
    if missing_partitions:
        raise ValueError(f"computation factors absent from canonical partitions: {missing_partitions}")

    inventory_rows: list[dict[str, Any]] = []
    for order, factor in enumerate(strategy_factors, start=1):
        inventory_rows.append(
            _source_row(
                factor=factor,
                old_source="strategy_v1",
                old_context="frozen_feature_membership",
                old_role="model_feature_membership",
                old_direction=None,
                direction_status="unsigned_membership",
                direction_authority="unsigned_membership",
                old_order=order,
                source_path=preprocessing_path,
                source_sha=source_hashes["strategy_preprocessing"],
            )
        )
    for row in mature.itertuples(index=False):
        inventory_rows.append(
            _source_row(
                factor=str(row.factor),
                old_source="economic_v1",
                old_context=str(row.sleeve_id),
                old_role="selected_sleeve_member",
                old_direction=int(row.expected_direction),
                direction_status="signed",
                direction_authority="economic_predeclared",
                source_path=economic_map_path,
                source_sha=source_hashes["economic_map"],
            )
        )
    for row in board.itertuples(index=False):
        inventory_rows.append(
            _source_row(
                factor=str(row.factor),
                old_source="rolling_stability_board_v2",
                old_context=str(row.outer_split_id),
                old_role=str(row.stability_role),
                old_direction=int(row.frozen_direction),
                direction_status="signed",
                direction_authority="inherited_from_rolling_stability",
                source_path=stability_paths["board"],
                source_sha=source_hashes["stability_board"],
            )
        )
    for row in direction_history.itertuples(index=False):
        inventory_rows.append(
            _source_row(
                factor=str(row.factor),
                old_source="rolling_direction_history_v2",
                old_context=f"{row.outer_split_id}/{row.inner_split_id}",
                old_role="frozen_direction_record",
                old_direction=int(row.frozen_direction),
                direction_status="signed",
                direction_authority="inherited_from_rolling_stability",
                source_path=stability_paths["direction_history"],
                source_sha=source_hashes["stability_direction_history"],
            )
        )
    for row in window_metrics.itertuples(index=False):
        selected = str(getattr(row, "selected", "False")).lower() in {"true", "1"}
        inventory_rows.append(
            _source_row(
                factor=str(row.factor),
                old_source="rolling_window_metrics_v2",
                old_context=f"{row.outer_split_id}/{row.inner_split_id}",
                old_role=(
                    "selected" if selected else str(getattr(row, "selection_reason", "not_selected"))
                ),
                old_direction=int(row.frozen_direction),
                direction_status="signed",
                direction_authority="inherited_from_rolling_stability",
                source_path=stability_paths["window_metrics"],
                source_sha=source_hashes["stability_window_metrics"],
            )
        )
    for row in selection_history.itertuples(index=False):
        selected = str(row.selected).lower() in {"true", "1"}
        inventory_rows.append(
            _source_row(
                factor=str(row.factor),
                old_source="rolling_selection_history_v2",
                old_context=f"{row.outer_split_id}/{row.inner_split_id}",
                old_role="selected" if selected else str(row.selection_reason),
                old_direction=int(row.frozen_direction),
                direction_status="signed",
                direction_authority="inherited_from_rolling_stability",
                source_path=stability_paths["selection_history"],
                source_sha=source_hashes["stability_selection_history"],
            )
        )
    representative_keys = set(
        zip(
            representatives["outer_split_id"].astype(str),
            representatives["factor"].astype(str),
        )
    )
    for row in memberships.itertuples(index=False):
        inventory_rows.append(
            _source_row(
                factor=str(row.factor),
                old_source="factor_clustering_v2",
                old_context=str(row.outer_split_id),
                old_role="cluster_provenance",
                old_direction=None,
                direction_status="not_applicable",
                direction_authority="none",
                old_cluster_id=str(row.cluster_id),
                old_is_representative=(str(row.outer_split_id), str(row.factor))
                in representative_keys,
                source_path=membership_path,
                source_sha=source_hashes["cluster_memberships"],
            )
        )

    inventory = pd.DataFrame(inventory_rows)
    _validate_unique(inventory, ["factor", "old_source", "old_context"], "inventory")
    union_set = set(union)
    inventory["computation_included"] = inventory["factor"].isin(union_set)
    inventory["computation_inclusion_reason"] = np.where(
        inventory["factor"].isin(strategy_factors),
        "frozen_strategy_v1_membership",
        np.where(
            inventory["factor"].isin(mature_factors),
            "mature_economic_membership",
            np.where(inventory["factor"].isin(extra_factors), "explicit_frozen_extra", "provenance_only"),
        ),
    )
    inventory = inventory.sort_values(
        ["factor", "old_source", "old_context"], kind="stable"
    ).reset_index(drop=True)

    stable_directions = (
        board.loc[board["factor"].isin(union_set), ["factor", "frozen_direction"]]
        .groupby("factor")["frozen_direction"]
        .agg(lambda values: sorted(set(int(value) for value in values)))
    )
    economic_direction = mature.set_index("factor")["expected_direction"].to_dict()
    extra_map = {str(item["factor"]): item for item in extras}
    universe_rows = []
    for factor in union:
        stable = stable_directions.get(factor, [])
        if factor in economic_direction:
            direction = int(economic_direction[factor])
            status = "signed"
            authority = "economic_predeclared"
        elif len(stable) == 1:
            direction = int(stable[0])
            status = "signed"
            authority = "inherited_from_rolling_stability"
        else:
            direction = None
            status = "unsigned_membership"
            authority = "unsigned_membership"
        reasons = []
        if factor in strategy_factors:
            reasons.append("frozen_strategy_v1_membership")
        if factor in mature_factors:
            reasons.append("mature_economic_membership")
        if factor in extra_map:
            reasons.append(str(extra_map[factor]["non_performance_reason"]))
        universe_rows.append(
            {
                "factor": factor,
                "strategy_v1_member": factor in strategy_factors,
                "mature_economic_member": factor in mature_factors,
                "explicit_extra": factor in extra_map,
                "inclusion_source": "+".join(reasons),
                "inclusion_reason": "+".join(reasons),
                "old_context_count": int((inventory["factor"] == factor).sum()),
                "is_duplicate_across_sources": int((inventory["factor"] == factor).sum()) > 1,
                "requires_computation": True,
                "old_direction": direction,
                "direction_status": status,
                "direction_authority": authority,
            }
        )
    computation_universe = pd.DataFrame(universe_rows).sort_values("factor").reset_index(drop=True)
    _validate_unique(computation_universe, ["factor"], "computation universe")
    return Phase0Inputs(
        config=config,
        inventory=inventory,
        computation_universe=computation_universe,
        partition_manifest=partition_manifest,
        factor_lineage=factor_lineage,
        source_hashes=source_hashes,
    )


def build_period_calendar(config: dict[str, Any], *, root: Path) -> pd.DataFrame:
    calendar_path = _path(root, config["provider_uri"]) / "calendars" / "day.txt"
    if not calendar_path.is_file():
        raise FileNotFoundError(f"missing Qlib trading calendar: {calendar_path}")
    calendar = pd.DatetimeIndex(
        pd.to_datetime(calendar_path.read_text(encoding="utf-8").splitlines(), errors="raise")
    ).sort_values()
    canonical_end = max(pd.Timestamp(item["requested_end"]) for item in config["periods"])
    eligible = calendar[calendar <= canonical_end]
    horizon = int(config["label"]["entry_lag_trading_days"]) + int(
        config["label"]["holding_trading_days"]
    )
    if len(eligible) <= horizon:
        raise ValueError("calendar is too short for label maturity")
    maturity_cutoff = eligible[-horizon - 1]
    rows = []
    for item in config["periods"]:
        requested_start = pd.Timestamp(item["requested_start"])
        requested_end = pd.Timestamp(item["requested_end"])
        dates = eligible[
            (eligible >= requested_start)
            & (eligible <= requested_end)
            & (eligible <= maturity_cutoff)
        ]
        rows.append(
            {
                "period_id": item["period_id"],
                "requested_start": requested_start,
                "requested_end": requested_end,
                "actual_signal_start": dates.min() if len(dates) else pd.NaT,
                "actual_signal_end": dates.max() if len(dates) else pd.NaT,
                "eligible_date_count": len(dates),
                "label_maturity_cutoff": maturity_cutoff,
                "coverage_status": "eligible" if len(dates) else "insufficient_history",
            }
        )
    return pd.DataFrame(rows)


def enforce_label_maturity(
    labels: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    *,
    as_of_date: pd.Timestamp | str,
    horizon: int = 21,
) -> pd.DataFrame:
    required = {*KEYS, "label_20d_t1", "label_exit_date"}
    missing = sorted(required - set(labels.columns))
    if missing:
        raise ValueError(f"label frame missing columns: {missing}")
    as_of = pd.Timestamp(as_of_date)
    frame = labels.copy()
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="raise")
    frame["label_exit_date"] = pd.to_datetime(frame["label_exit_date"], errors="coerce")
    future = frame["label_20d_t1"].notna() & frame["label_exit_date"].gt(as_of)
    if future.any():
        raise ValueError("future-label access detected: label exit date exceeds as-of date")
    expected_cutoff = calendar[calendar <= as_of][-horizon - 1]
    illegal = frame["label_20d_t1"].notna() & frame["datetime"].gt(expected_cutoff)
    if illegal.any():
        raise ValueError("future-label access detected after maturity cutoff")
    return frame


def load_canonical_labels(config: dict[str, Any], *, root: Path) -> pd.DataFrame:
    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    provider = _path(root, config["provider_uri"])
    calendar = pd.DatetimeIndex(
        pd.to_datetime((provider / "calendars" / "day.txt").read_text().splitlines())
    )
    start = min(pd.Timestamp(item["requested_start"]) for item in config["periods"])
    end = max(pd.Timestamp(item["requested_end"]) for item in config["periods"])
    qlib.init(provider_uri=str(provider), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    close = D.features(
        D.instruments(config["market"]),
        ["$close"],
        start_time=start,
        end_time=end,
        freq="day",
    ).reset_index()
    close["datetime"] = pd.to_datetime(close["datetime"], errors="raise")
    close["instrument"] = close["instrument"].astype(str).str.upper()
    close = close.sort_values(KEYS, kind="stable")
    grouped = close.groupby("instrument", sort=False)["$close"]
    close["label_20d_t1"] = grouped.shift(-21) / grouped.shift(-1) - 1
    date_to_exit = pd.Series(calendar, index=calendar).shift(-21)
    close["label_exit_date"] = close["datetime"].map(date_to_exit)
    result = close[[*KEYS, "label_20d_t1", "label_exit_date"]]
    return enforce_label_maturity(result, calendar, as_of_date=end, horizon=21)


def daily_rank_ic(frame: pd.DataFrame, factors: list[str], *, min_count: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date, group in frame.groupby("datetime", sort=True):
        label = pd.to_numeric(group["label_20d_t1"], errors="coerce")
        for factor in factors:
            values = pd.DataFrame(
                {
                    "factor": pd.to_numeric(group[factor], errors="coerce"),
                    "label": label,
                }
            ).replace([np.inf, -np.inf], np.nan).dropna()
            if len(values) < min_count or values["factor"].nunique() < 2:
                continue
            value = values["factor"].corr(values["label"], method="spearman")
            if pd.notna(value):
                rows.append(
                    {
                        "datetime": date,
                        "factor": factor,
                        "raw_rank_ic": float(value),
                        "pair_count": len(values),
                    }
                )
    return pd.DataFrame(rows, columns=["datetime", "factor", "raw_rank_ic", "pair_count"])


def compute_union_daily_ic(
    inputs: Phase0Inputs,
    labels: pd.DataFrame,
    *,
    root: Path,
    factors: list[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    requested = inputs.computation_universe["factor"].tolist() if factors is None else factors
    if len(requested) != len(set(requested)):
        raise ValueError("metric engine received duplicate factors")
    allowlist = set(inputs.computation_universe["factor"])
    if not set(requested).issubset(allowlist):
        raise ValueError("metric engine received a factor outside the frozen computation universe")
    factor_to_partition: dict[str, str] = {}
    for row in inputs.partition_manifest.drop_duplicates("partition_id").itertuples(index=False):
        for factor in str(row.factors).split(","):
            if factor in allowlist:
                if factor in factor_to_partition:
                    raise ValueError(f"factor mapped to multiple canonical partitions: {factor}")
                factor_to_partition[factor] = str(row.partition_id)
    started = time.perf_counter()
    pieces: list[pd.DataFrame] = []
    partition_reads = 0
    peak_frame_bytes = 0
    for partition_id in sorted(set(factor_to_partition[factor] for factor in requested)):
        partition_factors = sorted(
            factor for factor in requested if factor_to_partition[factor] == partition_id
        )
        segments = inputs.partition_manifest.loc[
            inputs.partition_manifest["partition_id"].eq(partition_id)
        ].sort_values("effective_start")
        for segment in segments.to_dict("records"):
            segment["partition_path"] = str(_path(root, str(segment["partition_path"])))
            frame = read_effective_partition(segment, columns=partition_factors)
            partition_reads += 1
            peak_frame_bytes = max(peak_frame_bytes, int(frame.memory_usage(deep=True).sum()))
            merged = frame.merge(labels, on=KEYS, how="left", validate="one_to_one")
            piece = daily_rank_ic(
                merged,
                partition_factors,
                min_count=int(inputs.config["computation"]["min_cross_section_count"]),
            )
            if not piece.empty:
                pieces.append(piece)
    daily = (
        pd.concat(pieces, ignore_index=True)
        if pieces
        else pd.DataFrame(columns=["datetime", "factor", "raw_rank_ic", "pair_count"])
    )
    daily = daily.sort_values(["factor", "datetime"], kind="stable").reset_index(drop=True)
    _validate_unique(daily, ["factor", "datetime"], "daily IC")
    metadata = {
        "computed_factor_count": len(requested),
        "partition_read_count": partition_reads,
        "daily_ic_row_count": len(daily),
        "cache_hit_count": 0,
        "peak_factor_frame_bytes": peak_frame_bytes,
        "metric_runtime_seconds": round(time.perf_counter() - started, 3),
    }
    return daily, metadata


def aggregate_period_metrics(
    daily: pd.DataFrame,
    universe: pd.DataFrame,
    period_calendar: pd.DataFrame,
    *,
    min_valid_dates: int,
) -> pd.DataFrame:
    direction_map = universe.set_index("factor")["old_direction"].to_dict()
    status_map = universe.set_index("factor")["direction_status"].to_dict()
    rows = []
    for factor in universe["factor"]:
        factor_daily = daily.loc[daily["factor"].eq(factor)].copy()
        direction = direction_map[factor]
        for period in period_calendar.itertuples(index=False):
            values = factor_daily.loc[
                factor_daily["datetime"].between(period.actual_signal_start, period.actual_signal_end)
            ].copy()
            clean = values["raw_rank_ic"].dropna()
            sufficient = len(clean) >= min_valid_dates
            signed = status_map[factor] == "signed" and pd.notna(direction)
            directed = clean * float(direction) if signed else pd.Series(dtype=float)
            std = clean.std(ddof=1)
            rows.append(
                {
                    "factor": factor,
                    "period_id": period.period_id,
                    "requested_start": period.requested_start,
                    "requested_end": period.requested_end,
                    "actual_signal_start": values["datetime"].min() if len(values) else pd.NaT,
                    "actual_signal_end": values["datetime"].max() if len(values) else pd.NaT,
                    "eligible_date_count": int(period.eligible_date_count),
                    "label_maturity_cutoff": period.label_maturity_cutoff,
                    "valid_date_count": len(clean),
                    "valid_pair_count": int(values["pair_count"].sum()) if len(values) else 0,
                    "coverage": len(clean) / period.eligible_date_count
                    if period.eligible_date_count
                    else np.nan,
                    "mean_raw_rank_ic": float(clean.mean()) if sufficient else np.nan,
                    "median_raw_rank_ic": float(clean.median()) if sufficient else np.nan,
                    "rank_icir": float(clean.mean() / std)
                    if sufficient and pd.notna(std) and std > 0
                    else np.nan,
                    "positive_date_ratio": float((clean > 0).mean()) if sufficient else np.nan,
                    "frozen_direction_mean_rank_ic": float(directed.mean())
                    if sufficient and signed
                    else np.nan,
                    "frozen_direction_positive_date_ratio": float((directed > 0).mean())
                    if sufficient and signed
                    else np.nan,
                    "direction_consistency": float((directed > 0).mean())
                    if sufficient and signed
                    else np.nan,
                    "coverage_status": "sufficient" if sufficient else "insufficient_history",
                    "insufficient_history_reason": ""
                    if sufficient
                    else f"valid_dates_below_{min_valid_dates}",
                }
            )
    return pd.DataFrame(rows).sort_values(["factor", "period_id"]).reset_index(drop=True)


def reconcile_same_era(
    daily: pd.DataFrame,
    universe: pd.DataFrame,
    window_metrics: pd.DataFrame,
    date_assignments: pd.DataFrame,
    *,
    consistent_tolerance: float,
    minor_tolerance: float,
    min_valid_dates: int,
) -> pd.DataFrame:
    assignments = date_assignments.copy()
    assignments["datetime"] = pd.to_datetime(assignments["datetime"], errors="raise")
    _validate_unique(
        assignments,
        ["outer_split_id", "inner_split_id", "datetime"],
        "development date assignment",
    )
    universe_index = universe.set_index("factor")
    rows = []
    metrics = window_metrics.loc[window_metrics["factor"].isin(universe_index.index)]
    for old in metrics.itertuples(index=False):
        context_dates = assignments.loc[
            assignments["outer_split_id"].eq(old.outer_split_id)
            & assignments["inner_split_id"].eq(old.inner_split_id)
        ]
        for scope in ("train", "validation"):
            dates = context_dates.loc[context_dates["fold"].eq(scope), "datetime"]
            old_value = pd.to_numeric(getattr(old, f"{scope}_mean_ic"), errors="coerce")
            canonical = daily.loc[
                daily["factor"].eq(old.factor) & daily["datetime"].isin(set(dates)),
                "raw_rank_ic",
            ].dropna()
            signed = universe_index.loc[old.factor, "direction_status"] == "signed"
            metric_compatible = True
            semantics_compatible = True
            universe_comparable = len(canonical) >= min_valid_dates
            direction_comparable = bool(signed)
            if pd.isna(old_value):
                status = "not_comparable"
                reason = "missing_old_metric"
            elif not metric_compatible:
                status = "metric_definition_mismatch"
                reason = "metric_definition_mismatch"
            elif not semantics_compatible:
                status = "material_data_semantic_change"
                reason = "factor_semantics_mismatch"
            elif not universe_comparable:
                status = "insufficient_history"
                reason = "canonical_same_era_dates_below_minimum"
            else:
                difference = abs(float(canonical.mean()) - float(old_value))
                if difference <= consistent_tolerance:
                    status = "consistent"
                    reason = "absolute_difference_within_consistent_tolerance"
                elif difference <= minor_tolerance:
                    status = "minor_drift"
                    reason = "absolute_difference_within_minor_drift_tolerance"
                else:
                    status = "material_data_semantic_change"
                    reason = "absolute_difference_exceeds_minor_drift_tolerance"
            rows.append(
                {
                    "factor": old.factor,
                    "old_source": "rolling_window_metrics_v2",
                    "old_context": f"{old.outer_split_id}/{old.inner_split_id}/{scope}",
                    "old_metric_name": f"{scope}_mean_rank_ic",
                    "old_metric_value": old_value,
                    "old_signal_start": dates.min() if len(dates) else pd.NaT,
                    "old_signal_end": dates.max() if len(dates) else pd.NaT,
                    "canonical_same_era_value": float(canonical.mean()) if len(canonical) else np.nan,
                    "canonical_valid_date_count": len(canonical),
                    "metric_definition_compatible": metric_compatible,
                    "factor_semantics_compatible": semantics_compatible,
                    "universe_comparable": universe_comparable,
                    "direction_comparable": direction_comparable,
                    "same_era_reconciliation_status": status,
                    "reconciliation_reason": reason,
                    "reconciliation_note": "Exact factor name, daily Spearman Rank IC, and frozen fold dates; canonical practical historical universe replay.",
                }
            )
    covered = set(metrics["factor"].astype(str))
    for item in universe.loc[~universe["factor"].isin(covered)].itertuples(index=False):
        rows.append(
            {
                "factor": item.factor,
                "old_source": (
                    "economic_v1"
                    if bool(getattr(item, "mature_economic_member", False))
                    else "frozen_membership"
                ),
                "old_context": "no_comparable_factor_level_metric",
                "old_metric_name": "",
                "old_metric_value": np.nan,
                "old_signal_start": pd.NaT,
                "old_signal_end": pd.NaT,
                "canonical_same_era_value": np.nan,
                "canonical_valid_date_count": 0,
                "metric_definition_compatible": False,
                "factor_semantics_compatible": True,
                "universe_comparable": False,
                "direction_comparable": item.direction_status == "signed",
                "same_era_reconciliation_status": "not_comparable",
                "reconciliation_reason": "no_old_factor_level_metric",
                "reconciliation_note": "Old economic evidence was recorded at sleeve level; Phase 0 does not manufacture a factor-level historical metric.",
            }
        )
    result = pd.DataFrame(rows).sort_values(["factor", "old_context"]).reset_index(drop=True)
    if not set(result["same_era_reconciliation_status"]).issubset(RECONCILIATION_STATUSES):
        raise AssertionError("unexpected reconciliation status")
    return result


def classify_backward_portability(
    factor_metrics: pd.DataFrame,
    *,
    signed: bool,
    reconciliation_comparable: bool,
    material_threshold: float = 0.005,
) -> str:
    if not signed:
        return "unsigned_feature"
    if not reconciliation_comparable:
        return "not_comparable"
    values = factor_metrics.set_index("period_id")["frozen_direction_mean_rank_ic"]
    required = [
        "early_2010_2014",
        "mid_2015_2018",
        "preexisting_2019_2020",
        "legacy_2021_2026",
    ]
    if any(period not in values or pd.isna(values[period]) for period in required):
        return "insufficient_history"
    early = float(np.mean([values[required[0]], values[required[1]]]))
    recent = float(np.mean([values[required[2]], values[required[3]]]))
    if recent > 0 and (values[required[0]] <= 0 or values[required[1]] <= 0):
        return "recent_regime_concentrated"
    if sum(values[period] > 0 for period in required) <= 2:
        return "direction_conflict"
    if all(values[period] > 0 for period in required):
        if early > recent + material_threshold:
            return "stronger_early"
        if early + material_threshold < recent:
            return "weaker_early"
        return "persistent"
    return "direction_conflict"


def build_backward_portability(
    period_metrics: pd.DataFrame,
    universe: pd.DataFrame,
    reconciliation: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    reconciliation_priority = {
        "consistent": 0,
        "minor_drift": 1,
        "not_comparable": 2,
        "unsigned_feature": 2,
        "insufficient_history": 2,
        "universe_not_comparable": 2,
        "metric_definition_mismatch": 3,
        "material_data_semantic_change": 4,
    }
    for item in universe.itertuples(index=False):
        reconciled = reconciliation.loc[reconciliation["factor"].eq(item.factor)]
        reconciliation_completed = not reconciled.empty
        factor_reconciliation_status = (
            max(
                reconciled["same_era_reconciliation_status"],
                key=lambda value: reconciliation_priority[str(value)],
            )
            if reconciliation_completed
            else "not_comparable"
        )
        metrics = period_metrics.loc[period_metrics["factor"].eq(item.factor)]
        status = classify_backward_portability(
            metrics,
            signed=item.direction_status == "signed",
            reconciliation_comparable=reconciliation_completed,
        )
        rows.append(
            {
                "factor": item.factor,
                "direction_status": item.direction_status,
                "direction_authority": item.direction_authority,
                "old_direction": item.old_direction,
                "same_era_reconciliation_status": factor_reconciliation_status,
                "backward_portability_status": status,
                "interpretation_reason": f"fixed_rule:{status}",
            }
        )
    result = pd.DataFrame(rows).sort_values("factor").reset_index(drop=True)
    if not set(result["backward_portability_status"]).issubset(PORTABILITY_STATUSES):
        raise AssertionError("unexpected portability status")
    return result


def build_old_vs_new_comparison(
    inventory: pd.DataFrame,
    period_metrics: pd.DataFrame,
    portability: pd.DataFrame,
) -> pd.DataFrame:
    pivots = period_metrics.pivot(
        index="factor", columns="period_id", values="frozen_direction_mean_rank_ic"
    ).add_prefix("directional_rank_ic_")
    result = (
        inventory.loc[inventory["computation_included"]]
        .merge(portability, on="factor", how="left", suffixes=("", "_factor"))
        .merge(pivots.reset_index(), on="factor", how="left")
    )
    return result.sort_values(["factor", "old_source", "old_context"]).reset_index(drop=True)


def build_conflicts_and_gaps(
    universe: pd.DataFrame,
    reconciliation: pd.DataFrame,
    portability: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for item in universe.itertuples(index=False):
        if item.direction_status != "signed":
            rows.append({"factor": item.factor, "issue_code": "unsigned_feature", "severity": "info"})
    for factor, group in reconciliation.groupby("factor", sort=True):
        statuses = set(group["same_era_reconciliation_status"])
        if "material_data_semantic_change" in statuses:
            rows.append(
                {"factor": factor, "issue_code": "same_era_material_drift", "severity": "review"}
            )
        if statuses.issubset({"not_comparable", "insufficient_history"}):
            rows.append(
                {"factor": factor, "issue_code": "same_era_not_comparable", "severity": "limitation"}
            )
    for row in portability.itertuples(index=False):
        if row.backward_portability_status in {
            "direction_conflict",
            "recent_regime_concentrated",
            "insufficient_history",
            "not_comparable",
        }:
            rows.append(
                {
                    "factor": row.factor,
                    "issue_code": f"portability_{row.backward_portability_status}",
                    "severity": "review",
                }
            )
    return pd.DataFrame(rows, columns=["factor", "issue_code", "severity"]).sort_values(
        ["factor", "issue_code"]
    ).reset_index(drop=True)


def write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8", date_format="%Y-%m-%d")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
