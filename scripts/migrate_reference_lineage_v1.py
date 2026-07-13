from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402


STAGES = (
    ("factor_clustering_v1", "configs/factor_clustering_v1.yaml"),
    ("factor_score_construction_v1", "configs/factor_score_construction_v1.yaml"),
    ("a_share_execution_v1", "configs/a_share_execution_v1.yaml"),
)


def artifact_dates(stage_id: str, output: Path) -> tuple[object, object]:
    if stage_id == "factor_clustering_v1":
        metrics = pd.read_csv(PROJECT_ROOT / "outputs/factor_rolling_stability_v1/local_reference/factor_window_metrics.csv")
        splits = pd.read_csv(PROJECT_ROOT / "outputs/purged_walk_forward_v1/local_reference/split_manifest.csv")
        used = splits.loc[splits.split_id.isin(metrics.split_id.unique())]
        return used.train_start.min(), used.test_end.max()
    if stage_id == "factor_score_construction_v1":
        frame = pd.read_parquet(output / "runtime/composite_scores.parquet", columns=["datetime"])
    else:
        frame = pd.read_csv(output / "daily_turnover.csv", usecols=["datetime"])
    dates = pd.to_datetime(frame["datetime"])
    return dates.min(), dates.max()


def main() -> int:
    code_state = capture_code_state(PROJECT_ROOT)
    for stage_id, config_name in STAGES:
        config = yaml.safe_load((PROJECT_ROOT / config_name).read_text(encoding="utf-8")) or {}
        output = PROJECT_ROOT / config["output_dir"]
        start_date, end_date = artifact_dates(stage_id, output)
        output_files = [item for item in output.rglob("*") if item.is_file() and item.name != "artifact_manifest.json"]
        write_stage_artifact_manifest(
            project_root=PROJECT_ROOT, stage_id=stage_id, config=config, output_dir=output,
            output_files=output_files, code_state=code_state,
            input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
            start_date=start_date, end_date=end_date,
            missing_lineage_fields=["legacy_output_pre_lineage", "universe_artifact_id"],
            lineage_status="reference_only",
        )
        print(f"attached reference-only lineage: {stage_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
