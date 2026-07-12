from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.score_construction import construct_daily_scores


def build_method(frame: pd.DataFrame, factors: pd.DataFrame, splits: pd.DataFrame, method: str, config: dict) -> pd.DataFrame:
    weights = pd.DataFrame({"factor_column": factors.factor, "cluster_id": [f"legacy_{i:03d}" for i in range(len(factors))], "raw_weight": 1.0, "direction": factors.direction.astype(int)})
    scores = []
    for split in splits.itertuples(index=False):
        window = frame.loc[(frame.datetime >= split.test_start) & (frame.datetime <= split.test_end)]
        if window.empty: continue
        result, _ = construct_daily_scores(window, weights, method=method, min_components=min(int(config["minimum_components"]), len(weights)), clip=float(config["score_clip"])); result["split_id"] = split.split_id; scores.append(result)
    return pd.concat(scores, ignore_index=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build legacy candidate scores on common test windows.")
    parser.add_argument("--config", type=Path, default=Path("configs/legacy_common_scores_v1.yaml"))
    args = parser.parse_args(); path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}; splits = pd.read_csv(PROJECT_ROOT / config["split_manifest"], parse_dates=["test_start", "test_end"])
    alpha_candidates = pd.read_csv(PROJECT_ROOT / config["alpha158_candidates"]); alpha_candidates["direction"] = alpha_candidates.consensus_direction.map({"positive": 1, "negative": -1}).fillna(1)
    alpha_frame = pd.read_pickle(PROJECT_ROOT / config["alpha158_frame"]); alpha_frame.datetime = pd.to_datetime(alpha_frame.datetime)
    alpha_scores = build_method(alpha_frame, alpha_candidates[["factor", "direction"]], splits, "alpha158_equal", config)
    old = pd.read_csv(PROJECT_ROOT / config["old_candidate_pool"]); old = old.loc[old.role == "alpha_candidate"].copy(); old["direction"] = old.expected_direction.map({"positive": 1, "negative": -1}).fillna(1)
    basic = pd.read_pickle(PROJECT_ROOT / config["basic_frame"]); basic.datetime = pd.to_datetime(basic.datetime)
    old_scores = build_method(basic, old[["factor", "direction"]], splits, "old_candidate_equal", config)
    scores = pd.concat([alpha_scores, old_scores], ignore_index=True); output = PROJECT_ROOT / config["output_dir"]; runtime = output / "runtime"; runtime.mkdir(parents=True, exist_ok=True)
    scores.to_parquet(runtime / "legacy_common_scores.parquet", index=False)
    summary = scores.groupby("method").agg(rows=("composite_score", "size"), coverage=("composite_score", lambda values: values.notna().mean()), minimum_components=("component_count", "min")).reset_index(); summary.to_csv(output / "score_summary.csv", index=False, encoding="utf-8-sig")
    contract = pd.DataFrame([{"check_name": "legacy_common_score_methods", "status": "pass" if summary.method.nunique() == 2 else "fail", "observed_value": summary.method.nunique(), "required_value": 2, "severity": "critical", "reason": "Alpha158 and old candidate scores share frozen test windows."}, {"check_name": "score_coverage", "status": "pass" if (summary.coverage > 0.8).all() else "fail", "observed_value": summary.coverage.min(), "required_value": ">0.8", "severity": "critical", "reason": "Legacy scores require usable coverage."}])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig"); (output / "legacy_common_scores_report.md").write_text(f"# Legacy Common Scores V1\n\n- Alpha158 factors: `{len(alpha_candidates)}`\n- Old alpha candidates: `{len(old)}`\n", encoding="utf-8"); print(contract.to_string(index=False)); return 1 if (contract.status == "fail").any() else 0


if __name__ == "__main__": raise SystemExit(main())
