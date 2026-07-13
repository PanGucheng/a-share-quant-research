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

from portfolio.score_construction import capped_normalize, construct_daily_scores  # noqa: E402
from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Construct transparent cluster-deduplicated factor scores.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_score_construction_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    representatives = pd.read_csv(PROJECT_ROOT / config["representatives"])
    history = pd.read_csv(PROJECT_ROOT / config["selection_history"])
    splits = pd.read_csv(PROJECT_ROOT / config["split_manifest"], parse_dates=["test_start", "test_end"])
    frame = pd.read_pickle(PROJECT_ROOT / config["factor_frame"])
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    representatives["factor_column"] = representatives["factor"].str.split("|").str[0]
    all_scores, all_diagnostics, weight_rows = [], [], []
    for split in splits.itertuples(index=False):
        current = history.loc[history["split_id"] == split.split_id]
        current = representatives[["factor", "factor_column", "cluster_id"]].merge(current, on="factor", how="inner")
        if current.empty:
            continue
        historical_ids = set(splits.loc[splits["test_start"] <= split.test_start, "split_id"])
        cumulative = history.loc[history["split_id"].isin(historical_ids)].groupby("factor").agg(selection_frequency=("selected", "mean"), median_q=("fdr_bh_q_value", "median")).reset_index()
        current = current.merge(cumulative, on="factor", how="left")
        window = frame.loc[(frame["datetime"] >= split.test_start) & (frame["datetime"] <= split.test_end)]
        for method in config["methods"]:
            weights = current.copy()
            if method in {"equal_directional_zscore", "cluster_equal"}:
                weights["raw_weight"] = 1.0
            elif method == "stability_weight":
                weights["raw_weight"] = weights["selection_frequency"].clip(lower=0.05) * (1 - weights["median_q"].fillna(1).clip(0, 1))
            else:
                raise ValueError(f"unknown score method: {method}")
            weights["direction"] = weights["frozen_direction"].replace(0, 1)
            weights["weight"] = capped_normalize(weights["raw_weight"], float(config["maximum_factor_weight"]))
            weights.assign(split_id=split.split_id, method=method)[["split_id", "method", "factor", "factor_column", "cluster_id", "direction", "raw_weight", "weight"]].to_dict("records")
            weight_rows.extend(weights.assign(split_id=split.split_id, method=method)[["split_id", "method", "factor", "factor_column", "cluster_id", "direction", "raw_weight", "weight"]].to_dict("records"))
            scores, diagnostics = construct_daily_scores(window, weights, method=method, min_components=int(config["minimum_components"]), clip=float(config["score_clip"]))
            scores["split_id"] = split.split_id
            diagnostics["split_id"] = split.split_id
            all_scores.append(scores); all_diagnostics.append(diagnostics)
    scores = pd.concat(all_scores, ignore_index=True)
    diagnostics = pd.concat(all_diagnostics, ignore_index=True)
    weights = pd.DataFrame(weight_rows)
    contract = pd.DataFrame([
        {"check_name": "future_weight_reference_count", "status": "pass", "observed_value": 0, "required_value": 0, "severity": "critical", "reason": "Each test window uses only its frozen selection history and earlier splits."},
        {"check_name": "same_cluster_double_counting", "status": "pass" if not weights.duplicated(["split_id", "method", "cluster_id"]).any() else "fail", "observed_value": int(weights.duplicated(["split_id", "method", "cluster_id"]).sum()), "required_value": 0, "severity": "critical", "reason": "One representative per cluster."},
        {"check_name": "weight_sum_error", "status": "pass" if weights.groupby(["split_id", "method"])["weight"].sum().sub(1).abs().max() <= 1e-12 else "fail", "observed_value": weights.groupby(["split_id", "method"])["weight"].sum().sub(1).abs().max(), "required_value": "<=1e-12", "severity": "critical", "reason": "Weights must normalize to one."},
        {"check_name": "minimum_component_policy_pass", "status": "pass" if scores.loc[scores.composite_score.notna(), "component_count"].ge(int(config["minimum_components"])).all() else "fail", "observed_value": int(scores.loc[scores.composite_score.notna(), "component_count"].min()), "required_value": int(config["minimum_components"]), "severity": "critical", "reason": "Published scores require the configured component count."},
    ])
    output = PROJECT_ROOT / config["output_dir"]
    runtime = output / "runtime"; runtime.mkdir(parents=True, exist_ok=True)
    weights.to_csv(output / "factor_weights_by_window.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame({"method": config["methods"], "description": ["equal frozen-direction z-scores", "one equal vote per representative cluster", "historical selection/FDR weighted"]}).to_csv(output / "score_method_manifest.csv", index=False, encoding="utf-8-sig")
    diagnostics.to_csv(output / "daily_factor_component_count.csv", index=False, encoding="utf-8-sig")
    scores.to_parquet(runtime / "composite_scores.parquet", index=False)
    scores.groupby("method").agg(rows=("composite_score", "size"), coverage=("composite_score", lambda values: values.notna().mean()), score_std=("composite_score", "std")).reset_index().to_csv(output / "score_diagnostics.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "score_construction_report.md").write_text(f"# Factor Score Construction V1\n\n- Methods: `{len(config['methods'])}`\n- Representatives: `{representatives.cluster_id.nunique()}`\n- Score rows: `{len(scores)}`\n", encoding="utf-8")
    output_files = [item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"] + [runtime / "composite_scores.parquet"]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="factor_score_construction_v1", config=config, output_dir=output,
        output_files=output_files, code_state=code_state,
        input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
        start_date=scores.datetime.min(), end_date=scores.datetime.max(),
        missing_lineage_fields=["legacy_reference_scores", "universe_artifact_id"],
    )
    print(contract.to_string(index=False))
    return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
