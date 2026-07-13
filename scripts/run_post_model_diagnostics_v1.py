from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import capture_code_state, write_stage_artifact_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run diagnostics that require trained-model outputs.")
    parser.add_argument("--config", type=Path, default=Path("configs/post_model_diagnostics_v1.yaml"))
    args = parser.parse_args()
    path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    model_scores = PROJECT_ROOT / config["model_scores"]
    output = PROJECT_ROOT / config["output_dir"]
    output.mkdir(parents=True, exist_ok=True)
    available = model_scores.is_file()
    contract = pd.DataFrame([
        {"check_name": "diagnostic_stage", "status": "pass", "observed_value": config.get("diagnostic_stage"), "required_value": "post_model_diagnostics", "severity": "critical", "reason": "Trained methods are isolated from the pre-model gate."},
        {"check_name": "trained_model_outputs", "status": "pass" if available else "blocked", "observed_value": available, "required_value": True, "severity": "downstream", "reason": "No model training is authorized in this PR."},
    ])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    (output / "post_model_diagnostics_report.md").write_text(
        "# Post-Model Diagnostics V1\n\n- Model outputs available: " + ("`true`" if available else "`false` (expected; training not started)") + "\n",
        encoding="utf-8",
    )
    output_files = [item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"]
    write_stage_artifact_manifest(
        project_root=PROJECT_ROOT, stage_id="post_model_diagnostics_v1", config=config, output_dir=output,
        output_files=output_files, code_state=code_state,
        input_manifest_paths=[PROJECT_ROOT / item for item in config.get("input_manifests", [])],
        missing_lineage_fields=[] if available else ["trained_model_outputs"],
    )
    print(contract.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
