from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qlib_integration.reconciliation import unknown_difference_count  # noqa: E402
from research_validation.lineage import load_artifact_manifest, validate_manifest_outputs  # noqa: E402


def main() -> int:
    config = yaml.safe_load((PROJECT_ROOT / "configs/execution_reconciliation_v1.yaml").read_text(encoding="utf-8")) or {}
    output_dir = PROJECT_ROOT / config["output_dir"]
    inventory = pd.read_csv(output_dir / "semantic_difference_inventory.csv")
    contract = pd.read_csv(output_dir / "contract_status.csv")
    assert unknown_difference_count(inventory) == 0
    assert contract.loc[contract["severity"].eq("critical"), "status"].eq("pass").all()
    manifest = load_artifact_manifest(output_dir / "artifact_manifest.json")
    assert not validate_manifest_outputs(manifest, output_dir, config=config)
    print("Execution reconciliation has exact synthetic parity and zero unknown differences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
