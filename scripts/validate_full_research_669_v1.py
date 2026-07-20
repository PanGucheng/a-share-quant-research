from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import load_artifact_manifest, validate_manifest_outputs  # noqa: E402


def main() -> int:
    config_path = PROJECT_ROOT / "configs/full_research_669_readiness_v1.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    output_dir = PROJECT_ROOT / config["output_dir"]
    manifest = load_artifact_manifest(output_dir / "artifact_manifest.json")
    assert not validate_manifest_outputs(manifest, output_dir, config=config)
    assert pd.read_csv(output_dir / "lineage_issues.csv").empty
    flags = pd.read_csv(output_dir / "readiness_summary.csv").iloc[0]
    assert bool(flags["full_research_669_infrastructure_ready"])
    assert bool(flags["full_research_669_validation_chain_ready"])
    assert bool(flags["full_research_669_qlib_execution_operational"])
    assert not bool(flags["full_research_authoritative_tradability_ready"])
    assert bool(flags["feature_allowlist_frozen"])
    assert bool(flags["core_model_ready"])
    assert bool(flags["pr5_model_training_ready"])
    assert not bool(flags["model_training_started"])
    print("All compact full-research 669-factor evidence validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
