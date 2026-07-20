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

from qlib_integration.contracts import contract_row  # noqa: E402
from research_validation.feature_matrix import atomic_parquet, canonical_hash, file_sha256, forward_return_label  # noqa: E402
from research_validation.lineage import capture_code_state, load_artifact_manifest, write_stage_artifact_manifest  # noqa: E402
from research_validation.stage_output import StageOutputPublisher  # noqa: E402

CONTROLLED = ["artifact_manifest.json", "contract_status.csv", "label_report.md", "label_sample.csv", "label_summary.csv", "schema.json"]


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build full-research t+1 labels aligned to the PIT feature key grid.")
    parser.add_argument("--config", type=Path, default=Path("configs/full_research_labels_v1.yaml"))
    args = parser.parse_args()
    config = yaml.safe_load(resolve(args.config).read_text(encoding="utf-8")) or {}
    matrix_manifest = load_artifact_manifest(resolve(config["feature_matrix_manifest"]))
    raw = pd.read_parquet(resolve(config["raw_cache"]), columns=["datetime", "instrument", "$close"])
    raw = raw.sort_values(["instrument", "datetime"], kind="stable")
    raw[str(config["label_name"])] = forward_return_label(
        raw, "$close", int(config["entry_lag"]), int(config["holding_days"])
    )
    keys = pd.read_parquet(resolve(config["key_partition"]), columns=["datetime", "instrument"])
    labels = keys.merge(raw[["datetime", "instrument", str(config["label_name"])]], on=["datetime", "instrument"], how="left", validate="one_to_one")
    label = str(config["label_name"])
    labels[label] = pd.to_numeric(labels[label], errors="coerce").replace([np.inf, -np.inf], np.nan)
    runtime = resolve(config["runtime_label"])
    atomic_parquet(labels, runtime)
    valid = int(labels[label].notna().sum())
    summary = pd.DataFrame([{"label": label, "row_count": len(labels), "valid_rows": valid, "coverage": valid / len(labels), "output_path": runtime.as_posix(), "output_sha256": file_sha256(runtime), "input_hash": canonical_hash({"factor_frame_id": matrix_manifest["factor_frame_id"], "entry_lag": config["entry_lag"], "holding_days": config["holding_days"]})}])
    contract = pd.DataFrame([
        contract_row("label_key_grid_aligned", len(labels) == 2_588_000 and not labels.duplicated(["datetime", "instrument"]).any(), len(labels), 2_588_000),
        contract_row("label_t_plus_one", int(config["entry_lag"]) == 1, config["entry_lag"], 1),
        contract_row("label_horizon", int(config["holding_days"]) == 20, config["holding_days"], 20),
        contract_row("label_coverage", valid / len(labels) >= 0.90, valid / len(labels), ">=0.90"),
        contract_row("label_output_hash", len(summary.iloc[0]["output_sha256"]) == 64, summary.iloc[0]["output_sha256"], "sha256"),
    ])
    ready = contract["status"].eq("pass").all()
    output_dir = resolve(config["output_dir"])
    with StageOutputPublisher(output_dir, CONTROLLED) as publisher:
        contract.to_csv(publisher.path("contract_status.csv"), index=False, encoding="utf-8-sig")
        summary.to_csv(publisher.path("label_summary.csv"), index=False, encoding="utf-8-sig")
        labels.head(100).to_csv(publisher.path("label_sample.csv"), index=False, encoding="utf-8-sig")
        publisher.path("schema.json").write_text(json.dumps({"keys": ["datetime", "instrument"], "label": label, "definition": "close[t+21]/close[t+1]-1"}, indent=2) + "\n", encoding="utf-8")
        publisher.path("label_report.md").write_text(f"# Full-Research Labels V1\n\n- Status: `{'pass' if ready else 'blocked'}`\n- Label: `{label}`\n- Rows / valid: `{len(labels)}` / `{valid}`\n- Runtime label parquet is hash-addressed and excluded from Git.\n", encoding="utf-8")
        files = [publisher.path(name) for name in CONTROLLED if name != "artifact_manifest.json"]
        write_stage_artifact_manifest(project_root=PROJECT_ROOT, stage_id="full_research_labels_v1", config=config, output_dir=publisher.staging_dir, output_files=files, code_state=capture_code_state(PROJECT_ROOT), input_manifest_paths=[resolve(config["feature_matrix_manifest"]), resolve(config["universe_manifest"])], factor_frame_id=matrix_manifest["factor_frame_id"], start_date=labels["datetime"].min(), end_date=labels["datetime"].max(), lineage_status="complete", artifact_status="pass" if ready else "blocked", blocked_reason="" if ready else "blocked_full_research_label_contract")
        publisher.publish()
    print(contract.to_string(index=False))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
