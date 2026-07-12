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
) -> pd.DataFrame:
    schema_frame = intervals.copy().assign(selection_reason=intervals["selection_reason"].fillna("top_median_amount"))
    try:
        validate_universe_intervals(schema_frame)
        invalid_intervals = 0
    except Exception:
        invalid_intervals = 1
    future_refs = int((pd.to_datetime(metrics["max_source_date"]) > pd.to_datetime(metrics["selection_date"])).sum())
    same_effective = int((pd.to_datetime(metrics["effective_date"]) <= pd.to_datetime(metrics["selection_date"])).sum())
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
        ("selected_snapshot_rows", "pass" if len(snapshots) > 0 else "fail", ">0", "At least one member snapshot is required."),
    ]
    observed = ["pass" if future_refs == 0 and invalid_intervals == 0 else "fail", future_refs, invalid_intervals, same_effective, "pass" if qlib_load else "fail", historical_mutation_count, len(snapshots)]
    return pd.DataFrame(
        [{"check_name": name, "status": status, "observed_value": value, "required_value": required, "severity": "critical", "reason": reason} for (name, status, required, reason), value in zip(checks, observed)]
    )
