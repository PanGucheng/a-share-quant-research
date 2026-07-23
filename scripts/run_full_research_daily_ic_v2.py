from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy.stats import spearmanr


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.feature_matrix import (  # noqa: E402
    canonical_hash,
    file_sha256,
)
from research_validation.lineage import (  # noqa: E402
    capture_code_state,
    load_artifact_manifest,
    validate_manifest_outputs,
    write_stage_artifact_manifest,
)
from research_validation.pairwise_ic import pairwise_daily_spearman  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED = [
    "artifact_manifest.json",
    "contract_status.csv",
    "daily_ic_report.md",
    "daily_rank_ic.csv",
    "factor_ic_summary.csv",
    "formula_validation.csv",
    "ic_v1_v2_difference_summary.csv",
    "partition_status.csv",
    "resolved_config.json",
]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def formula_validation() -> pd.DataFrame:
    fixture = pd.DataFrame(
        {
            "factor_a": [1.0, 2.0, np.nan, 4.0, 4.0],
            "factor_b": [5.0, np.nan, 3.0, 2.0, 1.0],
            "label": [5.0, 1.0, 4.0, np.nan, 2.0],
        }
    )
    actual = pairwise_daily_spearman(
        fixture,
        ["factor_a", "factor_b"],
        label_column="label",
        minimum_cross_section=2,
    ).set_index("factor")
    rows = []
    for factor in ("factor_a", "factor_b"):
        pair = fixture[[factor, "label"]].dropna()
        expected = float(spearmanr(pair[factor], pair["label"]).statistic)
        observed = float(actual.loc[factor, "rank_ic"])
        rows.append(
            {
                "case": factor,
                "pair_count": len(pair),
                "observed_rank_ic": observed,
                "scipy_rank_ic": expected,
                "absolute_difference": abs(observed - expected),
                "status": "pass" if abs(observed - expected) <= 1e-12 else "fail",
            }
        )
    reordered = pairwise_daily_spearman(
        fixture.iloc[::-1],
        ["factor_a", "factor_b"],
        label_column="label",
        minimum_cross_section=2,
    ).set_index("factor")
    rows.append(
        {
            "case": "row_order_invariance",
            "pair_count": int(actual["pair_count"].sum()),
            "observed_rank_ic": float(actual["rank_ic"].sum()),
            "scipy_rank_ic": float(reordered["rank_ic"].sum()),
            "absolute_difference": float(
                (actual["rank_ic"] - reordered["rank_ic"]).abs().max()
            ),
            "status": (
                "pass"
                if np.allclose(
                    actual["rank_ic"],
                    reordered["rank_ic"],
                    equal_nan=True,
                    atol=1e-12,
                )
                else "fail"
            ),
        }
    )
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute pairwise-valid Daily Spearman IC v2.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/full_research_daily_ic_v2.yaml"),
    )
    args = parser.parse_args()
    config_path = resolve(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    matrix_path = resolve(config["feature_matrix_manifest"])
    label_path = resolve(config["label_manifest"])
    matrix = load_artifact_manifest(matrix_path)
    label_manifest = load_artifact_manifest(label_path)
    for name, manifest, path in (
        ("matrix", matrix, matrix_path),
        ("labels", label_manifest, label_path),
    ):
        if (
            validate_manifest_outputs(manifest, path.parent)
            or manifest["artifact_status"] != "pass"
            or manifest["lineage_status"] != "complete"
            or bool(manifest["code_dirty"])
        ):
            raise ValueError(f"{name} input is stale, blocked, or non-authoritative")
    if matrix["artifact_id"] not in set(map(str, label_manifest["input_artifact_ids"])):
        raise ValueError("Labels v2 does not directly reference Matrix v4")
    if matrix["factor_frame_id"] != label_manifest["factor_frame_id"]:
        raise ValueError("Matrix v4 and Labels v2 factor frame IDs differ")
    input_manifest_paths = [matrix_path, label_path]
    if config.get("canary_manifest"):
        canary_path = resolve(config["canary_manifest"])
        canary_manifest = load_artifact_manifest(canary_path)
        canary_contract = pd.read_csv(resolve(config["canary_contract"]))
        if (
            validate_manifest_outputs(canary_manifest, canary_path.parent)
            or canary_manifest["artifact_status"] != "pass"
            or canary_manifest["lineage_status"] != "complete"
            or bool(canary_manifest["code_dirty"])
            or not canary_contract["status"].eq("pass").all()
        ):
            raise ValueError("Pairwise IC v2 canary is stale, blocked, or non-authoritative")
        input_manifest_paths.append(canary_path)
    label_summary = pd.read_csv(resolve(config["label_summary"]))
    label_runtime = resolve(config["label_runtime"])
    if (
        len(label_summary) != 1
        or file_sha256(label_runtime) != str(label_summary.iloc[0]["output_sha256"])
    ):
        raise ValueError("Labels v2 runtime hash mismatch")
    labels = pd.read_parquet(label_runtime)
    labels["datetime"] = pd.to_datetime(labels["datetime"])
    labels["instrument"] = labels["instrument"].astype(str).str.upper()
    label_name = str(config["label_name"])
    partitions = pd.read_csv(resolve(config["feature_partition_status"]))
    selected_batch_ids = {
        str(value) for value in config.get("selected_batch_ids", [])
    }
    if selected_batch_ids:
        partitions = partitions.loc[
            partitions["batch_id"].astype(str).isin(selected_batch_ids)
        ].copy()
        if set(partitions["batch_id"].astype(str)) != selected_batch_ids:
            raise ValueError("selected_batch_ids contains an unknown Matrix v4 partition")
    if len(partitions) != int(config["expected_batch_count"]):
        raise ValueError("unexpected Matrix v4 partition count")

    runtime = resolve(config["runtime_dir"])
    runtime.mkdir(parents=True, exist_ok=True)
    daily_frames: list[pd.DataFrame] = []
    partition_rows: list[dict[str, object]] = []
    for batch in partitions.itertuples(index=False):
        started = time.perf_counter()
        path = Path(str(batch.output_path))
        if file_sha256(path) != str(batch.output_sha256):
            raise ValueError(f"Matrix v4 partition hash mismatch: {batch.batch_id}")
        frame = pd.read_parquet(path)
        frame["datetime"] = pd.to_datetime(frame["datetime"])
        frame["instrument"] = frame["instrument"].astype(str).str.upper()
        if not frame[["datetime", "instrument"]].equals(
            labels[["datetime", "instrument"]]
        ):
            raise ValueError(f"key grid mismatch for batch {batch.batch_id}")
        factors = [
            column for column in frame.columns if column not in {"datetime", "instrument"}
        ]
        if config.get("maximum_factors_per_batch") is not None:
            factors = factors[: int(config["maximum_factors_per_batch"])]
        work = frame.copy()
        work[label_name] = labels[label_name].to_numpy()
        rows = []
        for date, group in work.groupby("datetime", sort=True):
            result = pairwise_daily_spearman(
                group,
                factors,
                label_column=label_name,
                minimum_cross_section=int(config["minimum_cross_section"]),
                tie_method=str(config["tie_method"]),
            )
            result.insert(0, "datetime", date)
            result.insert(1, "batch_id", str(batch.batch_id))
            rows.append(result)
        daily_batch = pd.concat(rows, ignore_index=True)
        batch_runtime = runtime / f"{batch.batch_id}.parquet"
        daily_batch.to_parquet(batch_runtime, index=False)
        daily_frames.append(daily_batch)
        partition_rows.append(
            {
                "batch_id": batch.batch_id,
                "factor_count": len(factors),
                "daily_row_count": len(daily_batch),
                "runtime_seconds": time.perf_counter() - started,
                "output_path": batch_runtime.as_posix(),
                "output_sha256": file_sha256(batch_runtime),
                "status": "pass",
            }
        )
        print(
            f"{batch.batch_id}: pairwise IC pass "
            f"({len(factors)} factors, {partition_rows[-1]['runtime_seconds']:.1f}s)",
            flush=True,
        )
    daily = pd.concat(daily_frames, ignore_index=True)
    daily = daily.sort_values(["datetime", "factor"]).reset_index(drop=True)
    summary = (
        daily.groupby(["batch_id", "factor"], as_index=False)
        .agg(
            ic_days=("rank_ic", "count"),
            mean_rank_ic=("rank_ic", "mean"),
            std_rank_ic=("rank_ic", "std"),
            min_pair_count=("pair_count", "min"),
            median_pair_count=("pair_count", "median"),
            max_factor_missing_count=("factor_missing_count", "max"),
            max_label_missing_count=("label_missing_count", "max"),
        )
    )
    summary["rank_ic_ir"] = summary["mean_rank_ic"] / summary["std_rank_ic"]
    legacy = pd.read_csv(resolve(config["legacy_daily_ic"]))
    legacy["datetime"] = pd.to_datetime(legacy["datetime"])
    comparison = legacy[["datetime", "factor", "rank_ic"]].merge(
        daily[["datetime", "factor", "rank_ic"]],
        on=["datetime", "factor"],
        how="outer",
        suffixes=("_v1", "_v2"),
        validate="one_to_one",
        indicator=True,
    )
    comparison["absolute_difference"] = (
        comparison["rank_ic_v1"] - comparison["rank_ic_v2"]
    ).abs()
    comparison["v1_missing_v2_present"] = (
        comparison["rank_ic_v1"].isna() & comparison["rank_ic_v2"].notna()
    )
    comparison["v1_present_v2_missing"] = (
        comparison["rank_ic_v1"].notna() & comparison["rank_ic_v2"].isna()
    )
    difference = (
        comparison.groupby("factor", as_index=False)
        .agg(
            compared_rows=("absolute_difference", "count"),
            changed_rows=("absolute_difference", lambda value: int(value.gt(1e-12).sum())),
            max_absolute_difference=("absolute_difference", "max"),
            mean_absolute_difference=("absolute_difference", "mean"),
            v1_missing_v2_present=("v1_missing_v2_present", "sum"),
            v1_present_v2_missing=("v1_present_v2_missing", "sum"),
        )
    )
    difference["v1_missing_v2_present"] = difference[
        "v1_missing_v2_present"
    ].astype(int)
    difference["v1_present_v2_missing"] = difference[
        "v1_present_v2_missing"
    ].astype(int)
    validation = formula_validation()
    valid_daily = daily.loc[daily["rank_ic"].notna()]
    min_pair = int(valid_daily["pair_count"].min()) if not valid_daily.empty else 0
    checks = [
        ("factor_count_expected", summary["factor"].nunique() == int(config["expected_factor_count"]), summary["factor"].nunique()),
        ("daily_ic_unique", not daily.duplicated(["datetime", "factor"]).any(), int(daily.duplicated(["datetime", "factor"]).sum())),
        ("pairwise_formula_scipy_match", validation["status"].eq("pass").all(), validation["absolute_difference"].max()),
        ("row_order_invariant", validation.loc[validation["case"].eq("row_order_invariance"), "status"].eq("pass").all(), "fixture"),
        ("minimum_ic_days", summary["ic_days"].ge(int(config["minimum_ic_days"])).all(), int(summary["ic_days"].min())),
        ("minimum_pair_count_on_ic_days", min_pair >= int(config["minimum_cross_section"]), min_pair),
        ("pair_counts_bounded", daily["pair_count"].le(len(labels["instrument"].unique())).all(), int(daily["pair_count"].max())),
        ("tie_policy_frozen", daily["tie_method"].eq(config["tie_method"]).all(), config["tie_method"]),
        ("matrix_label_lineage_match", matrix["factor_frame_id"] == label_manifest["factor_frame_id"], matrix["factor_frame_id"]),
        ("label_runtime_hash_bound", file_sha256(label_runtime) == label_summary.iloc[0]["output_sha256"], file_sha256(label_runtime)),
        ("legacy_difference_audited", difference["compared_rows"].sum() > 0, int(difference["changed_rows"].sum())),
        ("outer_test_not_used_for_decision", True, "descriptive daily IC only"),
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
    resolved = {
        **config,
        "config_file_sha256": file_sha256(config_path),
        "label_runtime_sha256": file_sha256(label_runtime),
        "daily_runtime_partition_digest": canonical_hash(partition_rows),
    }
    output = resolve(config["output_dir"])
    with StageOutputPublisher(output, CONTROLLED) as publisher:
        daily.to_csv(
            publisher.path("daily_rank_ic.csv"), index=False, encoding="utf-8-sig"
        )
        summary.to_csv(
            publisher.path("factor_ic_summary.csv"), index=False, encoding="utf-8-sig"
        )
        difference.to_csv(
            publisher.path("ic_v1_v2_difference_summary.csv"),
            index=False,
            encoding="utf-8-sig",
        )
        validation.to_csv(
            publisher.path("formula_validation.csv"), index=False, encoding="utf-8-sig"
        )
        pd.DataFrame(partition_rows).to_csv(
            publisher.path("partition_status.csv"), index=False, encoding="utf-8-sig"
        )
        contracts.to_csv(
            publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig"
        )
        publisher.path("resolved_config.json").write_text(
            json.dumps(resolved, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        publisher.path("daily_ic_report.md").write_text(
            "\n".join(
                [
                    "# Full-Research Pairwise Daily Rank IC V2",
                    "",
                    f"- Status: `{'pass' if ready else 'blocked'}`",
                    f"- Factors / daily rows: `{len(summary)}` / `{len(daily)}`",
                    f"- Changed v1 rows (>1e-12): `{int(difference['changed_rows'].sum())}`",
                    f"- Tie policy / minimum pair count: `{config['tie_method']}` / `{config['minimum_cross_section']}`",
                    "- Every factor and label is ranked on that factor's pairwise-valid date cross-section.",
                    "- This is descriptive input to development-only FDR/stability; no eligibility decision occurs here.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT,
            stage_id="full_research_daily_ic_v2",
            config=resolved,
            output_dir=publisher.staging_dir,
            output_files=files,
            code_state=capture_code_state(PROJECT_ROOT),
            input_manifest_paths=input_manifest_paths,
            universe_artifact_id=matrix["universe_artifact_id"],
            factor_catalog_id=matrix["factor_catalog_id"],
            factor_frame_id=matrix["factor_frame_id"],
            start_date=daily["datetime"].min(),
            end_date=daily["datetime"].max(),
            artifact_status="pass" if ready else "blocked",
            blocked_reason="" if ready else "blocked_pairwise_ic_v2_contract",
        )
        publisher.publish()
    print(contracts.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
