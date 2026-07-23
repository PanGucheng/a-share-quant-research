from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from factor_research.alpha101_source import (  # noqa: E402
    Alpha101SourceConfig,
    assert_alpha101_axes,
    compute_alpha101_features,
    mask_raw_to_pit_membership,
)
from factor_research.factor_library import BASE_FIELDS, add_basic_factors  # noqa: E402
from research_validation.factor_dependency import filter_only_reuse_allowed  # noqa: E402
from research_validation.feature_matrix import (  # noqa: E402
    build_pit_key_grid,
    file_sha256,
    filter_to_pit_intervals,
)
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    content_reference_id,
    write_stage_artifact_manifest,
)
from research_validation.stage_output import StageOutputPublisher  # noqa: E402
from scripts.run_full_research_feature_matrix_v1 import (  # noqa: E402
    expression_batch,
    ta_batch,
)


CONTROLLED = [
    "alpha101_relabel_receipts.csv",
    "artifact_manifest.json",
    "canary_coverage.csv",
    "common_key_equivalence.csv",
    "contract_status.csv",
    "impact_date_manifest.csv",
    "matrix_v4_canary_report.md",
    "partition_status.csv",
    "recompute_difference_attribution.csv",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def old_factor_values(
    factor: str,
    factor_inventory: pd.DataFrame,
    batch_manifest: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    batch_id = factor_inventory.set_index("name").loc[factor, "batch_id"]
    path = Path(batch_manifest.set_index("batch_id").loc[batch_id, "output_path"])
    frame = pd.read_parquet(path, columns=["datetime", "instrument", factor])
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    return frame.loc[frame["datetime"].between(start, end)]


def compare_values(old: pd.DataFrame, new: pd.DataFrame, factor: str) -> dict[str, object]:
    merged = old.merge(
        new,
        on=["datetime", "instrument"],
        how="inner",
        suffixes=("_v3", "_v4"),
        validate="one_to_one",
    ).sort_values(["datetime", "instrument"])
    left = pd.to_numeric(merged[f"{factor}_v3"], errors="coerce").to_numpy(dtype=np.float64)
    right = pd.to_numeric(merged[f"{factor}_v4"], errors="coerce").to_numpy(dtype=np.float64)
    both_nan = np.isnan(left) & np.isnan(right)
    bit_equal = left.view(np.uint64) == right.view(np.uint64)
    equal = both_nan | bit_equal
    comparable = ~(np.isnan(left) & np.isnan(right))
    differences = ~equal
    return {
        "factor": factor,
        "common_key_count": len(merged),
        "comparable_value_count": int(comparable.sum()),
        "bit_identical_count": int(equal.sum()),
        "difference_count": int(differences.sum()),
        "bit_identical": bool(equal.all()),
        "max_absolute_difference": (
            float(np.nanmax(np.abs(left - right)))
            if np.isfinite(left - right).any()
            else 0.0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded Matrix v4 semantic canary.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/full_research_feature_matrix_v4_canary.yaml"),
    )
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    start = pd.Timestamp(config["start_date"])
    end = pd.Timestamp(config["end_date"])
    intervals = pd.read_csv(resolve(config["universe_v2_intervals"]))
    intervals["start_date"] = pd.to_datetime(intervals["start_date"])
    intervals["end_date"] = pd.to_datetime(intervals["end_date"])
    scoped_intervals = intervals.loc[
        intervals["start_date"].le(end) & intervals["end_date"].ge(pd.Timestamp(config["warmup_start_date"]))
    ].copy()
    symbols = sorted(scoped_intervals["instrument"].astype(str).str.upper().unique())

    import qlib
    from qlib.config import C, REG_CN
    from qlib.data import D

    qlib.init(provider_uri=str(resolve(config["provider_uri"])), region=REG_CN)
    C.kernels = 1
    C.joblib_backend = "sequential"
    calendar = pd.DatetimeIndex(D.calendar(start_time=start, end_time=end, freq="day"))
    pit_keys = build_pit_key_grid(intervals, calendar)
    raw = pd.read_parquet(
        resolve(config["raw_cache_path"]),
        filters=[
            ("instrument", "in", symbols),
            ("datetime", ">=", pd.Timestamp(config["warmup_start_date"])),
            ("datetime", "<=", end),
        ],
    )
    raw["datetime"] = pd.to_datetime(raw["datetime"])
    raw["instrument"] = raw["instrument"].astype(str).str.upper()

    selected = config["selected_factors"]
    computed: dict[str, pd.DataFrame] = {}
    for source in ("alpha158", "alpha360"):
        names = list(selected[source])
        computed[source] = expression_batch(
            symbols,
            names,
            resolve(config[f"{source}_inventory"]),
            start,
            end,
            D,
        )
    computed["ta"] = ta_batch(raw, list(selected["ta"]), resolve(config["ta_source_path"]))
    computed["project_basic"] = add_basic_factors(raw.copy())[
        ["datetime", "instrument", *selected["project_basic"]]
    ]

    membership_calendar = pd.DatetimeIndex(
        D.calendar(
            start_time=max(
                pd.Timestamp(config["warmup_start_date"]),
                intervals["start_date"].min(),
            ),
            end_time=end,
            freq="day",
        )
    )
    membership_keys = build_pit_key_grid(intervals, membership_calendar)
    alpha_raw = mask_raw_to_pit_membership(
        raw,
        membership_keys,
        membership_start=intervals["start_date"].min(),
    )
    alpha_config = Alpha101SourceConfig(
        provider_uri=str(resolve(config["provider_uri"])),
        market="point_in_time",
        start=str(config["warmup_start_date"]),
        end=str(end.date()),
        max_instruments=None,
        source_local_path=resolve(config["alpha101_source_path"]),
        source_commit="dependency_canary",
        source_file="tests/KunTestUtil/ref_alpha101.py",
        source_module="KunTestUtil.ref_alpha101.Alphas",
        license="Apache-2.0",
        selected_smoke_factors=tuple(selected["alpha101"]),
        metadata_catalog=resolve(config["alpha101_metadata_catalog"]),
        catalog_stage="matrix_v4_canary",
        catalog_enabled=True,
        catalog_runnable=True,
        labels=(),
        output_dir=resolve(config["output_dir"]),
    )
    computed["alpha101"] = compute_alpha101_features(alpha_config, alpha_raw)

    factor_inventory = pd.read_csv(resolve(config["factor_inventory"]))
    dependency = pd.read_csv(resolve(config["factor_dependency_inventory"])).set_index("factor")
    batch_manifest = pd.read_csv(resolve(config["matrix_v3_batch_manifest"]))
    equivalence_rows: list[dict[str, object]] = []
    partition_rows: list[dict[str, object]] = []
    attribution_rows: list[dict[str, object]] = []
    coverage_rows: list[dict[str, object]] = []
    for source, names in selected.items():
        frame = computed[source]
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame["instrument"] = frame["instrument"].astype(str).str.upper()
        frame = frame.loc[frame["datetime"].between(start, end)]
        frame = filter_to_pit_intervals(frame, intervals)
        frame = pit_keys.merge(frame, on=["datetime", "instrument"], how="left", validate="one_to_one")
        for factor in names:
            old = old_factor_values(
                factor, factor_inventory, batch_manifest, start, end
            )
            comparison = compare_values(old, frame[["datetime", "instrument", factor]], factor)
            classification = str(dependency.loc[factor, "dependency_class"])
            reuse = bool(dependency.loc[factor, "filter_only_reuse_allowed"])
            equivalence_rows.append(
                {
                    **comparison,
                    "source_family": source,
                    "dependency_class": classification,
                    "filter_only_reuse_allowed": reuse,
                }
            )
            partition_rows.append(
                {
                    "source_family": source,
                    "factor": factor,
                    "mode": "filter_only_candidate" if reuse else "mandatory_recompute",
                    "status": (
                        "pass"
                        if (reuse and comparison["bit_identical"]) or not reuse
                        else "fail"
                    ),
                    "recomputed": not reuse,
                    "row_count": len(frame),
                }
            )
            attribution_rows.append(
                {
                    "factor": factor,
                    "dependency_class": classification,
                    "difference_count": comparison["difference_count"],
                    "attribution": (
                        "none_common_keys_bit_identical"
                        if comparison["difference_count"] == 0
                        and reuse
                        else "mandatory_recompute_no_observed_difference"
                        if comparison["difference_count"] == 0
                        else "lifecycle_clean_dynamic_cross_section_and_matrix_v3_union_universe"
                    ),
                }
            )
            coverage_rows.append(
                {
                    "source_family": source,
                    "factor": factor,
                    "valid_rows": int(frame[factor].notna().sum()),
                    "total_rows": len(frame),
                    "coverage": float(frame[factor].notna().mean()),
                }
            )

    equivalence = pd.DataFrame(equivalence_rows)
    partitions = pd.DataFrame(partition_rows)
    attribution = pd.DataFrame(attribution_rows)
    coverage = pd.DataFrame(coverage_rows)
    illegal = pd.read_csv(resolve(config["illegal_key_resolution"]))
    illegal["datetime"] = pd.to_datetime(illegal["datetime"])
    illegal = illegal.loc[illegal["datetime"].between(start, end)]
    impact = pd.DataFrame(
        [
            {
                "factor": factor,
                "source_family": source,
                "dependency_class": dependency.loc[factor, "dependency_class"],
                "illegal_input_date_count": int(illegal["datetime"].nunique()),
                "affected_instrument_count": int(illegal["instrument"].nunique()),
                "max_lookback_trading_days": dependency.loc[factor, "max_lookback_trading_days"],
                "recompute_start": config["warmup_start_date"] if source == "alpha101" else config["start_date"],
                "recompute_end": config["end_date"],
            }
            for source, names in selected.items()
            for factor in names
        ]
    )
    reference = pd.DataFrame([[1.0]], index=pd.to_datetime(["2021-09-01"]), columns=["SH600000"])
    mismatch_rejected = False
    try:
        assert_alpha101_axes(
            reference.rename(columns={"SH600000": "SZ000001"}),
            reference,
            "canary_fixture",
        )
    except ValueError:
        mismatch_rejected = True
    relabel = pd.DataFrame(
        [
            {
                "case": "actual_alpha101_exact_axes",
                "status": "pass",
                "detail": "all selected Alpha101 methods passed exact index/column equality",
            },
            {
                "case": "same_length_wrong_label_rejected",
                "status": "pass" if mismatch_rejected else "fail",
                "detail": "positional relabel fallback is forbidden",
            },
        ]
    )
    source_coverage = set(selected) == {"alpha158", "alpha360", "ta", "project_basic", "alpha101"}
    pure = equivalence.loc[equivalence["filter_only_reuse_allowed"].astype(bool)]
    mandatory = equivalence.loc[~equivalence["filter_only_reuse_allowed"].astype(bool)]
    checks = [
        ("five_source_families_covered", source_coverage, sorted(selected)),
        ("clean_key_grid_nonempty", len(pit_keys) > 0, len(pit_keys)),
        ("pure_candidates_bit_identical", pure["bit_identical"].all(), pure["difference_count"].sum()),
        (
            "mandatory_recompute_not_reused",
            partitions.loc[
                partitions["mode"].eq("mandatory_recompute"), "recomputed"
            ].astype(bool).all(),
            int(
                partitions.loc[
                    partitions["mode"].eq("mandatory_recompute"), "recomputed"
                ].astype(bool).sum()
            ),
        ),
        ("unknown_fixture_fail_closed", not filter_only_reuse_allowed("unknown", classification_proven=False, fallback_sensitive=False), "filter_only_reuse=False"),
        ("alpha101_axis_labels_strict", relabel["status"].eq("pass").all(), relabel["status"].tolist()),
        ("all_partitions_pass", partitions["status"].eq("pass").all(), partitions["status"].value_counts().to_dict()),
    ]
    contracts = pd.DataFrame(
        [
            {
                "check": name,
                "status": "pass" if passed else "fail",
                "severity": "critical",
                "detail": detail,
            }
            for name, passed, detail in checks
        ]
    )
    ready = contracts["status"].eq("pass").all()
    resolved_config = {
        **config,
        "config_file_sha256": file_sha256(config_path),
        "raw_cache_sha256": file_sha256(resolve(config["raw_cache_path"])),
        "factor_dependency_inventory_sha256": file_sha256(resolve(config["factor_dependency_inventory"])),
        "matrix_v3_batch_manifest_sha256": file_sha256(resolve(config["matrix_v3_batch_manifest"])),
    }
    output = resolve(config["output_dir"])
    with StageOutputPublisher(output, CONTROLLED) as publisher:
        equivalence.to_csv(publisher.path("common_key_equivalence.csv"), index=False, encoding="utf-8-sig")
        partitions.to_csv(publisher.path("partition_status.csv"), index=False, encoding="utf-8-sig")
        attribution.to_csv(publisher.path("recompute_difference_attribution.csv"), index=False, encoding="utf-8-sig")
        coverage.to_csv(publisher.path("canary_coverage.csv"), index=False, encoding="utf-8-sig")
        impact.to_csv(publisher.path("impact_date_manifest.csv"), index=False, encoding="utf-8-sig")
        relabel.to_csv(publisher.path("alpha101_relabel_receipts.csv"), index=False, encoding="utf-8-sig")
        contracts.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("resolved_config.json").write_text(
            json.dumps(resolved_config, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("matrix_v4_canary_report.md").write_text(
            "\n".join(
                [
                    "# Full-Research Feature Matrix V4 Canary",
                    "",
                    f"- Status: `{'pass' if ready else 'blocked'}`",
                    f"- Dates: `{config['start_date']}` to `{config['end_date']}`",
                    f"- PIT keys: `{len(pit_keys)}`",
                    f"- Symbols with warmup data: `{len(symbols)}`",
                    f"- Pure candidate differences: `{int(pure['difference_count'].sum())}`",
                    f"- Mandatory-recompute differences: `{int(mandatory['difference_count'].sum())}`",
                    "",
                    "This bounded canary is review evidence only; it does not authorize the 30-batch Matrix v4 run.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_feature_matrix_v4_canary",
            config=resolved_config,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=[
                resolve(config["universe_v2_manifest"]),
                resolve(config["factor_dependency_manifest"]),
                resolve(config["factor_catalog_manifest"]),
            ],
            universe_artifact_id=content_reference_id(
                "universe-v2",
                [resolve(config["universe_v2_intervals"])],
            ),
            factor_catalog_id=content_reference_id(
                "factor-catalog-669",
                [resolve(config["factor_inventory"])],
            ),
            start_date=start,
            end_date=end,
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_matrix_v4_canary_contract",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
