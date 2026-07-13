from __future__ import annotations

import argparse
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.score_construction import capped_normalize, construct_daily_scores, filter_eligible_representatives  # noqa: E402
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402


CONTROLLED_OUTPUTS = (
    "factor_weights_by_window.csv", "score_method_manifest.csv", "score_availability.csv",
    "excluded_score_factors.csv", "daily_factor_component_count.csv", "score_diagnostics.csv",
    "contract_status.csv", "score_construction_report.md", "runtime/composite_scores.parquet",
    "artifact_manifest.json",
)
WEIGHT_COLUMNS = ["split_id", "method", "factor", "factor_column", "cluster_id", "direction", "raw_weight", "weight"]


def _write_common(publisher: StageOutputPublisher, config: dict, weights: pd.DataFrame, availability: pd.DataFrame, excluded: pd.DataFrame) -> None:
    weights.reindex(columns=WEIGHT_COLUMNS).to_csv(publisher.path("factor_weights_by_window.csv"), index=False, encoding="utf-8-sig")
    descriptions = {
        "equal_directional_zscore": "equal frozen-direction z-scores",
        "cluster_equal": "one equal vote per representative cluster",
        "stability_weight": "historical selection/FDR weighted",
    }
    pd.DataFrame([{"method": method, "description": descriptions[method]} for method in config["methods"]]).to_csv(publisher.path("score_method_manifest.csv"), index=False, encoding="utf-8-sig")
    availability.reindex(columns=["split_id", "method", "valid_component_count", "status", "reason"]).to_csv(publisher.path("score_availability.csv"), index=False, encoding="utf-8-sig")
    excluded.reindex(columns=["split_id", "factor", "reason"]).to_csv(publisher.path("excluded_score_factors.csv"), index=False, encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description="Construct transparent cluster-deduplicated factor scores.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_score_construction_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    representatives = pd.read_csv(PROJECT_ROOT / config["representatives"])
    history = pd.read_csv(PROJECT_ROOT / config["selection_history"])
    required_history = {"factor", "split_id", "selected", "selection_eligible", "eligible", "frozen_direction", "fdr_bh_q_value"}
    missing_history = required_history - set(history.columns)
    if missing_history:
        raise ValueError(f"selection history missing eligibility fields: {sorted(missing_history)}")
    splits = pd.read_csv(PROJECT_ROOT / config["split_manifest"], parse_dates=["test_start", "test_end"])
    representatives["factor_column"] = representatives.get("factor", pd.Series(dtype=object)).str.split("|").str[0]

    all_scores: list[pd.DataFrame] = []
    all_diagnostics: list[pd.DataFrame] = []
    weight_rows: list[dict] = []
    availability_rows: list[dict] = []
    excluded_rows: list[dict] = []
    frame: pd.DataFrame | None = None
    minimum_components = int(config["minimum_components"])
    for split in splits.itertuples(index=False):
        current_history = history.loc[history.split_id == split.split_id].copy()
        current = representatives[["factor", "factor_column", "cluster_id"]].merge(current_history, on="factor", how="inner")
        if not current.empty:
            current, excluded_current = filter_eligible_representatives(current)
            excluded_rows.extend({"split_id": split.split_id, "factor": row.factor, "reason": row.reason} for row in excluded_current.itertuples())
        for method in config["methods"]:
            if len(current) < minimum_components:
                availability_rows.append({"split_id": split.split_id, "method": method, "valid_component_count": len(current), "status": "blocked", "reason": "blocked_insufficient_selected_components"})
                continue
            if frame is None:
                frame = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
                frame["datetime"] = pd.to_datetime(frame["datetime"])
            historical_ids = set(splits.loc[splits.test_start <= split.test_start, "split_id"])
            eligible_history = history.loc[
                history.split_id.isin(historical_ids)
                & history.selected.fillna(False).astype(bool)
                & history.selection_eligible.fillna(False).astype(bool)
                & history.eligible.fillna(False).astype(bool)
            ]
            cumulative = eligible_history.groupby("factor").agg(selection_frequency=("selected", "mean"), median_q=("fdr_bh_q_value", "median")).reset_index()
            weights = current.merge(cumulative, on="factor", how="left")
            if method in {"equal_directional_zscore", "cluster_equal"}:
                weights["raw_weight"] = 1.0
            elif method == "stability_weight":
                weights["raw_weight"] = weights.selection_frequency.clip(lower=0.05) * (1 - weights.median_q.fillna(1).clip(0, 1))
            else:
                raise ValueError(f"unknown score method: {method}")
            weights["direction"] = weights["frozen_direction"].astype(int)
            weights["weight"] = capped_normalize(weights["raw_weight"], float(config["maximum_factor_weight"]))
            weight_rows.extend(weights.assign(split_id=split.split_id, method=method)[WEIGHT_COLUMNS].to_dict("records"))
            window = frame.loc[(frame.datetime >= split.test_start) & (frame.datetime <= split.test_end)]
            scores, diagnostics = construct_daily_scores(window, weights, method=method, min_components=minimum_components, clip=float(config["score_clip"]))
            scores["split_id"] = split.split_id
            diagnostics["split_id"] = split.split_id
            all_scores.append(scores)
            all_diagnostics.append(diagnostics)
            availability_rows.append({"split_id": split.split_id, "method": method, "valid_component_count": len(current), "status": "pass", "reason": ""})

    weights_frame = pd.DataFrame(weight_rows, columns=WEIGHT_COLUMNS)
    availability = pd.DataFrame(availability_rows)
    excluded = pd.DataFrame(excluded_rows)
    output = PROJECT_ROOT / config["output_dir"]
    with StageOutputPublisher(output, CONTROLLED_OUTPUTS) as publisher:
        _write_common(publisher, config, weights_frame, availability, excluded)
        if not all_scores:
            pd.DataFrame(columns=["method", "datetime", "rows", "minimum_components", "median_components", "split_id"]).to_csv(publisher.path("daily_factor_component_count.csv"), index=False, encoding="utf-8-sig")
            pd.DataFrame(columns=["method", "rows", "coverage", "score_std"]).to_csv(publisher.path("score_diagnostics.csv"), index=False, encoding="utf-8-sig")
            contract = pd.DataFrame([
                {"check_name": "score_construction_status", "status": "blocked", "observed_value": "blocked_insufficient_selected_components", "required_value": "pass", "severity": "critical", "reason": "No split has enough selected eligible representatives."},
                {"check_name": "valid_score_window_count", "status": "blocked", "observed_value": 0, "required_value": ">0", "severity": "critical", "reason": "blocked_insufficient_selected_components"},
            ])
            contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
            publisher.path("score_construction_report.md").write_text("# Factor Score Construction V1\n\n- Status: `blocked_insufficient_selected_components`\n- Active runtime score parquet: `absent`\n", encoding="utf-8")
            output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
            write_stage_artifact_manifest(
                project_root=PROJECT_ROOT, stage_id="factor_score_construction_v1", config=config,
                output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
                input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
                missing_lineage_fields=["universe_artifact_id"], lineage_status="reference_only",
                artifact_status="blocked", blocked_reason="blocked_insufficient_selected_components",
            )
            publisher.publish()
            print(contract.to_string(index=False))
            return 2

        scores_frame = pd.concat(all_scores, ignore_index=True)
        diagnostics_frame = pd.concat(all_diagnostics, ignore_index=True)
        diagnostics_frame.to_csv(publisher.path("daily_factor_component_count.csv"), index=False, encoding="utf-8-sig")
        scores_frame.to_parquet(publisher.path("runtime/composite_scores.parquet"), index=False)
        scores_frame.groupby("method").agg(rows=("composite_score", "size"), coverage=("composite_score", lambda values: values.notna().mean()), score_std=("composite_score", "std")).reset_index().to_csv(publisher.path("score_diagnostics.csv"), index=False, encoding="utf-8-sig")
        contract = pd.DataFrame([
            {"check_name": "score_construction_status", "status": "pass", "observed_value": "pass", "required_value": "pass", "severity": "critical", "reason": "Current selected eligible representatives produced scores."},
            {"check_name": "zero_direction_weight_count", "status": "pass" if not weights_frame.direction.eq(0).any() else "fail", "observed_value": int(weights_frame.direction.eq(0).sum()), "required_value": 0, "severity": "critical", "reason": "Zero direction cannot be converted to positive."},
            {"check_name": "weight_sum_error", "status": "pass" if weights_frame.groupby(["split_id", "method"]).weight.sum().sub(1).abs().max() <= 1e-12 else "fail", "observed_value": weights_frame.groupby(["split_id", "method"]).weight.sum().sub(1).abs().max(), "required_value": "<=1e-12", "severity": "critical", "reason": "Weights normalize to one."},
        ])
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        publisher.path("score_construction_report.md").write_text(f"# Factor Score Construction V1\n\n- Status: `pass`\n- Score rows: `{len(scores_frame)}`\n", encoding="utf-8")
        output_files = [publisher.staging_dir / item for item in CONTROLLED_OUTPUTS if item != "artifact_manifest.json" and (publisher.staging_dir / item).is_file()]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id="factor_score_construction_v1", config=config,
            output_dir=publisher.staging_dir, output_files=output_files, code_state=code_state,
            input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
            start_date=scores_frame.datetime.min(), end_date=scores_frame.datetime.max(), missing_lineage_fields=["universe_artifact_id"],
        )
        publisher.publish()
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
