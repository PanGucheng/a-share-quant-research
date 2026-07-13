from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import freeze_support
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.purged_split import WalkForwardConfig, build_purged_walk_forward, leakage_audit  # noqa: E402
from research_validation.lineage import capture_code_state, content_reference_id, write_stage_artifact_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build date-level purged walk-forward splits.")
    parser.add_argument("--config", type=Path, default=Path("configs/purged_walk_forward_v1.yaml"))
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    import qlib
    from qlib.config import REG_CN
    from qlib.data import D
    qlib.init(provider_uri=config["provider_uri"], region=REG_CN)
    calendar = pd.DatetimeIndex(D.calendar(start_time=config["start_date"], end_time=config["end_date"], freq="day"))
    fields = {field: config[field] for field in WalkForwardConfig.__dataclass_fields__}
    outputs = build_purged_walk_forward(calendar, WalkForwardConfig(**fields))
    contract = leakage_audit(outputs)
    output = PROJECT_ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    runtime = output / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    outputs["split_manifest"].to_csv(output / "split_manifest.csv", index=False, encoding="utf-8-sig")
    outputs["split_manifest"].to_csv(output / "split_date_ranges.csv", index=False, encoding="utf-8-sig")
    outputs["purged_dates"].to_csv(output / "purged_dates.csv", index=False, encoding="utf-8-sig")
    outputs["embargoed_dates"].to_csv(output / "embargoed_dates.csv", index=False, encoding="utf-8-sig")
    outputs["date_assignments"].groupby(["split_id", "fold"]).size().reset_index(name="sample_dates").to_csv(output / "sample_counts.csv", index=False, encoding="utf-8-sig")
    outputs["date_assignments"].to_csv(runtime / "date_assignments.csv", index=False, encoding="utf-8-sig")
    outputs["label_intervals"].to_csv(runtime / "label_intervals.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "leakage_audit.csv", index=False, encoding="utf-8-sig")
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "resolved_config.json").write_text(json.dumps(config, indent=2, default=str) + "\n", encoding="utf-8")
    (output / "purged_walk_forward_report.md").write_text(
        "# Purged Walk-Forward V1\n\n"
        + f"- Splits: `{len(outputs['split_manifest'])}`\n"
        + f"- Backend: `{config['backend']}`\n"
        + f"- Semantic reference: `{config['semantic_reference']}`\n"
        + "- mlfinpy repository dependency: `false`\n",
        encoding="utf-8",
    )
    compact_files = [
        output / "split_manifest.csv",
        output / "split_date_ranges.csv",
        output / "purged_dates.csv",
        output / "embargoed_dates.csv",
        output / "sample_counts.csv",
        output / "leakage_audit.csv",
        output / "contract_status.csv",
        output / "resolved_config.json",
        output / "purged_walk_forward_report.md",
    ]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT,
        stage_id="purged_walk_forward_v1",
        config=config,
        output_dir=output,
        output_files=compact_files,
        code_state=code_state,
        split_manifest_id=content_reference_id("split-manifest", [output / "split_manifest.csv"]),
        start_date=outputs["split_manifest"]["train_start"].min(),
        end_date=outputs["split_manifest"]["test_end"].max(),
        missing_lineage_fields=["universe_artifact_id", "pit_universe_integration"],
    )
    print(contract.to_string(index=False))
    return 1 if (contract["status"] == "fail").any() else 0


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(main())
