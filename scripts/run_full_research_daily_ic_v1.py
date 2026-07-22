from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import file_sha256  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, validate_manifest_outputs, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = ["artifact_manifest.json", "contract_status.csv", "daily_rank_ic.csv", "daily_ic_report.md", "factor_ic_summary.csv"]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Calculate daily PIT cross-sectional Rank IC for the 80-factor trial.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_daily_ic_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    matrix_manifest_path = resolve(config["feature_matrix_manifest"])
    label_manifest_path = resolve(config["label_manifest"])
    matrix_manifest = load_artifact_manifest(matrix_manifest_path)
    label_manifest = load_artifact_manifest(label_manifest_path)
    manifest_issues = [
        *validate_manifest_outputs(matrix_manifest, matrix_manifest_path.parent),
        *validate_manifest_outputs(label_manifest, label_manifest_path.parent),
    ]
    if manifest_issues or matrix_manifest["artifact_status"] != "pass" or label_manifest["artifact_status"] != "pass":
        raise ValueError("daily IC upstream manifest is stale or blocked")
    if str(matrix_manifest["artifact_id"]) not in set(map(str, label_manifest["input_artifact_ids"])):
        raise ValueError("current label artifact does not reference the current matrix")
    label_runtime = resolve(config["label_runtime"])
    label_summary = pd.read_csv(label_manifest_path.parent / "label_summary.csv")
    if len(label_summary) != 1 or file_sha256(label_runtime) != str(label_summary.iloc[0]["output_sha256"]):
        raise ValueError("label runtime hash differs from the current label receipt")
    labels = pd.read_parquet(label_runtime)
    label_name = str(config["label_name"])
    batches = pd.read_csv(resolve(config["feature_batch_manifest"]))
    selected_batch_ids = {str(value) for value in config.get("selected_batch_ids", [])}
    if selected_batch_ids:
        batches = batches.loc[batches["batch_id"].astype(str).isin(selected_batch_ids)].copy()
        if set(batches["batch_id"].astype(str)) != selected_batch_ids:
            raise ValueError("daily IC selected_batch_ids contains an unknown batch")
    expected_factor_count = int(config.get("expected_factor_count", 80))
    rows: list[dict[str, object]] = []
    for batch in batches.itertuples(index=False):
        frame = pd.read_parquet(resolve(batch.output_path))
        if not frame[["datetime", "instrument"]].equals(labels[["datetime", "instrument"]]):
            raise ValueError(f"key grid mismatch for batch {batch.batch_id}")
        factors = [column for column in frame.columns if column not in {"datetime", "instrument"}]
        work = frame.copy()
        work[label_name] = labels[label_name].to_numpy()
        for date, group in work.groupby("datetime", sort=True):
            label_valid = group[label_name].notna()
            label_rank = group[label_name].rank(method="average")
            factor_ranks = group[factors].where(label_valid, axis=0).rank(method="average")
            counts = group[factors].notna().mul(label_valid, axis=0).sum().astype(int)
            correlations = factor_ranks.corrwith(label_rank)
            for factor in factors:
                count = int(counts[factor])
                ic = float(correlations[factor]) if count >= int(config["minimum_cross_section"]) else np.nan
                rows.append({"datetime": date, "batch_id": batch.batch_id, "factor": factor, "rank_ic": ic, "cross_section_count": count})
    daily = pd.DataFrame(rows)
    summary = daily.groupby(["batch_id", "factor"], as_index=False).agg(ic_days=("rank_ic", "count"), mean_rank_ic=("rank_ic", "mean"), std_rank_ic=("rank_ic", "std"), min_cross_section=("cross_section_count", "min"), median_cross_section=("cross_section_count", "median"))
    summary["rank_ic_ir"] = summary["mean_rank_ic"] / summary["std_rank_ic"]
    valid_daily = daily.loc[daily["rank_ic"].notna()]
    minimum_valid_cross_section = int(valid_daily["cross_section_count"].min()) if not valid_daily.empty else 0
    contract = pd.DataFrame([
        contract_row("factor_count", summary["factor"].nunique() == expected_factor_count, summary["factor"].nunique(), expected_factor_count),
        contract_row("daily_ic_unique", not daily.duplicated(["datetime", "factor"]).any(), int(daily.duplicated(["datetime", "factor"]).sum()), 0),
        contract_row("minimum_ic_days", bool(summary["ic_days"].ge(int(config["minimum_ic_days"])).all()), int(summary["ic_days"].min()), config["minimum_ic_days"]),
        contract_row("minimum_cross_section_on_ic_days", minimum_valid_cross_section >= int(config["minimum_cross_section"]), minimum_valid_cross_section, config["minimum_cross_section"]),
        contract_row("factor_frame_lineage", bool(matrix_manifest["factor_frame_id"]), matrix_manifest["factor_frame_id"], "nonempty"),
        contract_row("label_current_matrix_parent", str(matrix_manifest["artifact_id"]) in set(map(str, label_manifest["input_artifact_ids"])), matrix_manifest["artifact_id"], "direct label parent"),
        contract_row("label_runtime_hash_bound", file_sha256(label_runtime) == str(label_summary.iloc[0]["output_sha256"]), file_sha256(label_runtime), label_summary.iloc[0]["output_sha256"]),
    ])
    ready = contract["status"].eq("pass").all()
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        daily.to_csv(publisher.path("daily_rank_ic.csv"), index=False, encoding="utf-8-sig")
        summary.to_csv(publisher.path("factor_ic_summary.csv"), index=False, encoding="utf-8-sig")
        publisher.path("daily_ic_report.md").write_text(f"# Full-Research Daily Rank IC V1\n\n- Status: `{'pass' if ready else 'blocked'}`\n- Factors: `{len(summary)}`\n- Daily rows: `{len(daily)}`\n- IC is descriptive input to purged/FDR stages, not an eligibility decision.\n", encoding="utf-8")
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(project_root=PROJECT_ROOT, stage_id="full_research_daily_ic_v1", config=config, output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT), input_manifest_paths=[matrix_manifest_path, label_manifest_path], factor_frame_id=matrix_manifest["factor_frame_id"], start_date=daily["datetime"].min(), end_date=daily["datetime"].max(), lineage_status="complete", artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_daily_ic_contract")
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
