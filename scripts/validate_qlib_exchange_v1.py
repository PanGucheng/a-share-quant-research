from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.readiness import validate_execution_evidence  # noqa: E402
from research_validation.lineage import load_artifact_manifest, validate_manifest_outputs  # noqa: E402


def main() -> int:
    config_path = PROJECT_ROOT / "configs/qlib_exchange_readiness_v1.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    _, issues = validate_execution_evidence(PROJECT_ROOT, config["evidence"])
    assert not issues, "\n".join(f"{item.check_name}: {item.reason}" for item in issues)
    output_dir = PROJECT_ROOT / config["output_dir"]
    manifest = load_artifact_manifest(output_dir / "artifact_manifest.json")
    assert not validate_manifest_outputs(manifest, output_dir, config=config)
    flags = pd.read_csv(output_dir / "readiness_summary.csv").iloc[0]
    assert bool(flags["qlib_exchange_infrastructure_ready"])
    assert bool(flags["qlib_exchange_synthetic_ready"])
    assert bool(flags["execution_reconciliation_ready"])
    assert not bool(flags["qlib_exchange_reference_ready"])
    assert not bool(flags["model_training_started"])
    print("All Qlib Exchange V1 evidence and readiness validations passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
