from __future__ import annotations

from pathlib import Path
import shutil

import pandas as pd

from research_validation.schemas import validate_universe_intervals


def audit_universe(
    snapshots: pd.DataFrame,
    metrics: pd.DataFrame,
    intervals: pd.DataFrame,
    qlib_file: Path,
    historical_mutation_count: int = 0,
    source_intervals: pd.DataFrame | None = None,
    lifecycle_differences: pd.DataFrame | None = None,
    removed_keys: pd.DataFrame | None = None,
) -> pd.DataFrame:
    schema_frame = intervals.copy().assign(selection_reason=intervals["selection_reason"].fillna("top_median_amount"))
    try:
        validate_universe_intervals(schema_frame)
        invalid_intervals = 0
    except Exception:
        invalid_intervals = 1
    future_refs = int((pd.to_datetime(metrics["max_source_date"]) > pd.to_datetime(metrics["selection_date"])).sum())
    same_effective = int((pd.to_datetime(metrics["effective_date"]) <= pd.to_datetime(metrics["selection_date"])).sum())
    lifecycle_violation_count = 0
    overlapping_interval_count = 0
    removed_key_still_active_count = 0
    if source_intervals is not None:
        membership = intervals.copy()
        lifecycle = source_intervals[["instrument", "start", "end"]].copy()
        membership["instrument"] = membership["instrument"].astype(str).str.upper()
        lifecycle["instrument"] = lifecycle["instrument"].astype(str).str.upper()
        membership["start_date"] = pd.to_datetime(membership["start_date"]).dt.normalize()
        membership["end_date"] = pd.to_datetime(membership["end_date"]).dt.normalize()
        lifecycle["start"] = pd.to_datetime(lifecycle["start"]).dt.normalize()
        lifecycle["end"] = pd.to_datetime(lifecycle["end"]).dt.normalize()
        candidates = membership.reset_index(names="_membership_id").merge(
            lifecycle, on="instrument", how="left"
        )
        contained_ids = set(
            candidates.loc[
                candidates["start"].notna()
                & candidates["start"].le(candidates["start_date"])
                & candidates["end"].ge(candidates["end_date"]),
                "_membership_id",
            ]
        )
        lifecycle_violation_count = len(membership) - len(contained_ids)
        ordered = membership.sort_values(["instrument", "start_date", "end_date"])
        previous_end = ordered.groupby("instrument")["end_date"].shift()
        overlapping_interval_count = int(
            (previous_end.notna() & ordered["start_date"].le(previous_end)).sum()
        )
        if removed_keys is not None and not removed_keys.empty:
            removed = removed_keys[["datetime", "instrument"]].copy()
            removed["datetime"] = pd.to_datetime(removed["datetime"]).dt.normalize()
            active = removed.merge(membership, on="instrument", how="left")
            removed_key_still_active_count = int(
                (
                    active["start_date"].notna()
                    & active["start_date"].le(active["datetime"])
                    & active["end_date"].ge(active["datetime"])
                ).sum()
            )
    qlib_load = False
    try:
        import qlib
        from qlib.config import REG_CN
        from qlib.data.storage.file_storage import FileInstrumentStorage

        runtime_provider = qlib_file.parent / "runtime" / "qlib_provider"
        runtime_instruments = runtime_provider / "instruments"
        runtime_instruments.mkdir(parents=True, exist_ok=True)
        target = runtime_instruments / "point_in_time.txt"
        shutil.copyfile(qlib_file, target)
        qlib.init(provider_uri={"day": str(runtime_provider)}, region=REG_CN)
        loaded = FileInstrumentStorage("point_in_time", "day", provider_uri={"day": str(runtime_provider)}).data
        loaded_rows = sum(len(spans) for spans in loaded.values())
        qlib_load = loaded_rows == len(intervals) and bool(loaded)
    except Exception:
        qlib_load = False
    checks = [
        ("point_in_time_audit", "pass" if future_refs == 0 and invalid_intervals == 0 else "fail", "pass", "PIT lineage and intervals must be valid."),
        ("future_data_reference_count", "pass" if future_refs == 0 else "fail", 0, "No source date may exceed selection date."),
        ("invalid_interval_count", "pass" if invalid_intervals == 0 else "fail", 0, "Intervals must satisfy the universe schema."),
        ("same_selection_effective_date_count", "pass" if same_effective == 0 else "fail", 0, "Membership must take effect on a later trading day."),
        ("qlib_instruments_load", "pass" if qlib_load else "fail", "pass", "Generated TSV must round-trip through the Qlib instrument file format."),
        ("historical_membership_mutation_count", "pass" if historical_mutation_count == 0 else "fail", 0, "Adding later observations must not change an earlier snapshot."),
        ("lifecycle_intersection_applied", "pass" if source_intervals is not None else "fail", True, "Final membership must be the intersection of rolling-universe and source-lifecycle intervals."),
        ("lifecycle_violation_count", "pass" if lifecycle_violation_count == 0 else "fail", 0, "Every final membership interval must be contained in a source lifecycle interval."),
        ("overlapping_membership_interval_count", "pass" if overlapping_interval_count == 0 else "fail", 0, "Final intervals for an instrument must not overlap."),
        ("removed_key_still_active_count", "pass" if removed_key_still_active_count == 0 else "fail", 0, "Every key removed by lifecycle intersection must be absent from final membership."),
        ("lifecycle_correction_interval_count", "pass", ">=0", "Lifecycle corrections are evidence and do not fail an otherwise clean final universe."),
        ("removed_illegal_key_count", "pass", ">=0", "Removed lifecycle-illegal keys must be disclosed."),
        ("selected_snapshot_rows", "pass" if len(snapshots) > 0 else "fail", ">0", "At least one member snapshot is required."),
    ]
    observed = [
        "pass" if future_refs == 0 and invalid_intervals == 0 else "fail",
        future_refs,
        invalid_intervals,
        same_effective,
        "pass" if qlib_load else "fail",
        historical_mutation_count,
        source_intervals is not None,
        lifecycle_violation_count,
        overlapping_interval_count,
        removed_key_still_active_count,
        0 if lifecycle_differences is None else len(lifecycle_differences),
        0 if removed_keys is None else len(removed_keys),
        len(snapshots),
    ]
    return pd.DataFrame(
        [{"check_name": name, "status": status, "observed_value": value, "required_value": required, "severity": "critical", "reason": reason} for (name, status, required, reason), value in zip(checks, observed)]
    )
