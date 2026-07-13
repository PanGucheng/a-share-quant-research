from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from portfolio.model_comparison import prerequisite_status, readiness_flags
from research_validation.lineage import capture_code_state, load_input_manifests, write_stage_artifact_manifest
from research_validation.profiles import Profile, ProfileType


def contract_pass(path: Path) -> bool:
    if not path.is_file():
        return False
    frame = pd.read_csv(path)
    blocking = frame.loc[frame.status.isin(["fail", "blocked"]) & frame.severity.isin(["critical", "downstream"])]
    return blocking.empty


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate model comparison on all required research contracts.")
    parser.add_argument("--config", type=Path, default=Path("configs/factor_model_comparison_v1.yaml"))
    args = parser.parse_args(); path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    code_state = capture_code_state(PROJECT_ROOT)
    contracts = {name: pd.read_csv(PROJECT_ROOT / contract_path) for name, contract_path in config["prerequisites"].items()}
    status = prerequisite_status(contracts)
    input_paths = [PROJECT_ROOT / item for item in config.get("input_manifests", [])]
    manifests, missing_manifests = load_input_manifests(input_paths)
    profiles = [Profile(str(item["profile_name"]), ProfileType(str(item["profile_type"]))) for item in manifests]
    lineage_status = "reference_only" if missing_manifests or any(item["lineage_status"] != "complete" for item in manifests) else "complete"
    flags = readiness_flags(
        status, profiles, lineage_status=lineage_status,
        full_research_contracts_pass=all(contract_pass(PROJECT_ROOT / item) for item in config.get("full_research_prerequisites", [])),
        liquidity_contract_pass=contract_pass(PROJECT_ROOT / config["capability_prerequisites"]["liquidity_residualized"]),
        historical_exposure_contract_pass=contract_pass(PROJECT_ROOT / config["capability_prerequisites"]["historical_exposure"]),
    )
    output = PROJECT_ROOT / config["output_dir"]; output.mkdir(parents=True, exist_ok=True); status.to_csv(output / "prerequisite_status.csv", index=False, encoding="utf-8-sig")
    reasons = {
        "reference_ready": "Reference contracts run under smoke/reference profiles; this is not a research result.",
        "full_research_ready": "Requires homogeneous full_research artifacts and complete lineage.",
        "core_model_ready": "Core training inherits the full-research and complete-lineage requirements.",
        "liquidity_residualized_model_ready": "Adds the liquidity residualization capability contract.",
        "historical_exposure_model_ready": "Adds genuine historical PIT industry and market-cap exposure data.",
        "model_training_started": "Training remains outside this infrastructure PR.",
    }
    contract = pd.DataFrame([
        {"check_name": name, "status": "pass" if value else ("pass" if name == "model_training_started" else "blocked"), "observed_value": value, "required_value": (False if name == "model_training_started" else True), "severity": "critical" if name in {"reference_ready", "model_training_started"} else "capability", "reason": reasons[name]}
        for name, value in flags.items()
    ])
    contract.to_csv(output / "contract_status.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([flags | {"lineage_status": lineage_status, "missing_manifest_count": len(missing_manifests)}]).to_csv(output / "readiness_summary.csv", index=False, encoding="utf-8-sig")
    (output / "model_comparison_report.md").write_text("# Factor Model Comparison V1\n\n" + "\n".join(f"- {name}: `{str(value).lower()}`" for name, value in flags.items()) + f"\n- Lineage status: `{lineage_status}`\n- Training remains outside this PR.\n", encoding="utf-8")
    output_files = [item for item in output.iterdir() if item.is_file() and item.name != "artifact_manifest.json"]
    write_stage_artifact_manifest(project_root=PROJECT_ROOT, stage_id="factor_model_comparison_v1", config=config, output_dir=output, output_files=output_files, code_state=code_state, input_manifest_paths=input_paths, missing_lineage_fields=[f"input_manifest:{item}" for item in missing_manifests], lineage_status=lineage_status)
    print(contract.to_string(index=False))
    return 0 if flags["reference_ready"] and not flags["model_training_started"] else 2


if __name__ == "__main__": raise SystemExit(main())
