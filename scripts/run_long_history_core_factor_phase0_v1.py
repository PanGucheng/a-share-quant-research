from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factor_research.backward_replication import (  # noqa: E402
    aggregate_period_metrics,
    build_backward_portability,
    build_conflicts_and_gaps,
    build_old_vs_new_comparison,
    build_period_calendar,
    compute_union_daily_ic,
    file_sha256,
    load_canonical_labels,
    load_phase0_config,
    preflight_phase0,
    reconcile_same_era,
    write_csv,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Long-History Core Factor Phase 0")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "long_history_core_factor_phase0_v1.yaml",
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--smoke-only", action="store_true")
    parser.add_argument("--refresh-cache", action="store_true")
    return parser.parse_args()


def _summary_base(inputs, elapsed: float) -> dict:
    universe = inputs.computation_universe
    strategy = universe["strategy_v1_member"]
    mature = universe["mature_economic_member"]
    return {
        "stage_id": "long_history_core_factor_phase0_v1",
        "phase": 0,
        "artifact_status": "preflight_pass",
        "canonical_dataset_id": inputs.config["canonical_dataset_id"],
        "provenance_row_count": len(inputs.inventory),
        "provenance_unique_factor_count": inputs.inventory["factor"].nunique(),
        "computation_factor_count": len(universe),
        "strategy_v1_only_count": int((strategy & ~mature).sum()),
        "mature_only_count": int((mature & ~strategy).sum()),
        "overlap_count": int((strategy & mature).sum()),
        "explicit_extra_count": int(universe["explicit_extra"].sum()),
        "signed_factor_count": int(universe["direction_status"].eq("signed").sum()),
        "unsigned_factor_count": int(universe["direction_status"].ne("signed").sum()),
        "source_hashes": inputs.source_hashes,
        "preflight_runtime_seconds": round(elapsed, 3),
        "strategy_v1_changed": False,
        "forward_track_changed": False,
        "strategy_v2_authorized": False,
        "phase_1_started": False,
    }


def _write_preflight(output: Path, inputs, summary: dict) -> None:
    write_csv(output / "old_conclusion_inventory.csv", inputs.inventory)
    write_csv(output / "actual_computation_universe.csv", inputs.computation_universe)
    write_csv(output / "computation_universe.csv", inputs.computation_universe)
    resolved = dict(inputs.config)
    resolved["verified_source_hashes"] = inputs.source_hashes
    write_json(output / "resolved_config.json", resolved)
    write_json(output / "run_summary.json", summary)


def _cache_identity(inputs, factors: list[str]) -> dict:
    return {
        "canonical_dataset_id": inputs.config["canonical_dataset_id"],
        "factor_list": factors,
        "factor_list_sha256": inputs.config["computation"]["expected_union_sha256"]
        if len(factors) == len(inputs.computation_universe)
        else factors[0],
        "label": inputs.config["label"]["name"],
    }


def _load_or_compute_daily(output: Path, inputs, labels, factors, refresh):
    suffix = "smoke" if len(factors) == 1 else "fixed_union"
    cache_path = output / f"daily_rank_ic_cache_{suffix}.parquet"
    identity_path = output / f"daily_rank_ic_cache_{suffix}.json"
    cold_summary_path = output / f"daily_rank_ic_cold_compute_{suffix}.json"
    identity = _cache_identity(inputs, factors)
    if not refresh and cache_path.is_file() and identity_path.is_file():
        observed = json.loads(identity_path.read_text(encoding="utf-8"))
        if observed == identity:
            daily = pd.read_parquet(cache_path)
            metadata = {
                "computed_factor_count": len(factors),
                "partition_read_count": 0,
                "daily_ic_row_count": len(daily),
                "cache_hit_count": 1,
                "peak_factor_frame_bytes": 0,
                "metric_runtime_seconds": 0.0,
            }
            if cold_summary_path.is_file():
                cold = json.loads(cold_summary_path.read_text(encoding="utf-8"))
                metadata.update({f"cold_{key}": value for key, value in cold.items()})
            return daily, metadata
    daily, metadata = compute_union_daily_ic(inputs, labels, root=ROOT, factors=factors)
    daily.to_parquet(cache_path, index=False)
    write_json(identity_path, identity)
    write_json(cold_summary_path, metadata)
    return daily, metadata


def _load_or_compute_labels(output: Path, inputs, refresh: bool):
    cache_path = output / "label_20d_t1_cache.parquet"
    identity_path = output / "label_20d_t1_cache.json"
    identity = json.loads(json.dumps({
        "canonical_dataset_id": inputs.config["canonical_dataset_id"],
        "provider_uri": inputs.config["provider_uri"],
        "label": inputs.config["label"]["name"],
        "periods": inputs.config["periods"],
    }, default=str))
    if not refresh and cache_path.is_file() and identity_path.is_file():
        if json.loads(identity_path.read_text(encoding="utf-8")) == identity:
            return pd.read_parquet(cache_path), 1
    labels = load_canonical_labels(inputs.config, root=ROOT)
    labels.to_parquet(cache_path, index=False)
    write_json(identity_path, identity)
    return labels, 0


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    config = load_phase0_config(args.config)
    inputs = preflight_phase0(config, root=ROOT)
    output = ROOT / config["outputs"]["runtime_dir"]
    summary = _summary_base(inputs, time.perf_counter() - started)
    _write_preflight(output, inputs, summary)
    print(
        "Preflight PASS: "
        f"strategy={summary['strategy_v1_only_count']} mature={summary['mature_only_count']} "
        f"overlap={summary['overlap_count']} union={summary['computation_factor_count']} "
        f"signed={summary['signed_factor_count']} unsigned={summary['unsigned_factor_count']}",
        flush=True,
    )
    if args.preflight_only:
        return 0

    parent_hashes_before = {
        name: file_sha256(ROOT / path)
        for name, path in {
            "strategy_freeze": config["strategy_v1"]["freeze"],
            "strategy_preprocessing": config["strategy_v1"]["preprocessing"],
            "economic_map": config["economic"]["map"],
            "economic_manifest": config["economic"]["manifest"],
        }.items()
    }
    period_calendar = build_period_calendar(config, root=ROOT)
    write_csv(output / "period_calendar.csv", period_calendar)
    labels, label_cache_hits = _load_or_compute_labels(output, inputs, args.refresh_cache)
    factors = (
        [str(config["computation"]["smoke_factor"])]
        if args.smoke_only
        else inputs.computation_universe["factor"].tolist()
    )
    daily, compute_metadata = _load_or_compute_daily(
        output, inputs, labels, factors, args.refresh_cache
    )
    active_universe = inputs.computation_universe.loc[
        inputs.computation_universe["factor"].isin(factors)
    ].copy()
    period_metrics = aggregate_period_metrics(
        daily,
        active_universe,
        period_calendar,
        min_valid_dates=int(config["computation"]["min_valid_dates"]),
    )
    write_csv(output / "factor_period_metrics.csv", period_metrics)

    window_metrics = pd.read_csv(ROOT / config["stability"]["window_metrics"])
    date_assignments = pd.read_csv(ROOT / config["stability"]["date_assignments"])
    reconciliation = reconcile_same_era(
        daily,
        active_universe,
        window_metrics,
        date_assignments,
        consistent_tolerance=float(
            config["reconciliation"]["consistent_absolute_tolerance"]
        ),
        minor_tolerance=float(config["reconciliation"]["minor_drift_absolute_tolerance"]),
        min_valid_dates=int(config["computation"]["min_valid_dates"]),
    )
    write_csv(output / "same_era_reconciliation.csv", reconciliation)
    portability = build_backward_portability(period_metrics, active_universe, reconciliation)
    write_csv(output / "backward_portability.csv", portability)
    old_vs_new = build_old_vs_new_comparison(
        inputs.inventory.loc[inputs.inventory["factor"].isin(factors)],
        period_metrics,
        portability,
    )
    write_csv(output / "old_vs_new_comparison.csv", old_vs_new)
    conflicts = build_conflicts_and_gaps(active_universe, reconciliation, portability)
    write_csv(output / "conflicts_and_gaps.csv", conflicts)

    parent_hashes_after = {
        name: file_sha256(ROOT / path)
        for name, path in {
            "strategy_freeze": config["strategy_v1"]["freeze"],
            "strategy_preprocessing": config["strategy_v1"]["preprocessing"],
            "economic_map": config["economic"]["map"],
            "economic_manifest": config["economic"]["manifest"],
        }.items()
    }
    if parent_hashes_before != parent_hashes_after:
        raise RuntimeError("immutable parent evidence changed during Phase 0")
    verified_after = preflight_phase0(config, root=ROOT)
    if verified_after.source_hashes != inputs.source_hashes:
        raise RuntimeError("a Phase 0 provenance parent changed during the run")
    summary.update(compute_metadata)
    summary["label_cache_hit_count"] = label_cache_hits
    summary.update(
        {
            "artifact_status": "smoke_pass" if args.smoke_only else "phase_0_completed",
            "smoke_only": bool(args.smoke_only),
            "reconciliation_status_counts": reconciliation[
                "same_era_reconciliation_status"
            ].value_counts().sort_index().to_dict(),
            "backward_portability_status_counts": portability[
                "backward_portability_status"
            ].value_counts().sort_index().to_dict(),
            "conflict_and_gap_count": len(conflicts),
            "label_row_count": len(labels),
            "parent_files_byte_identical": True,
            "total_runtime_seconds": round(time.perf_counter() - started, 3),
        }
    )
    write_json(output / "run_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
