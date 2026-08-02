from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from model_research.forward_hardening import (  # noqa: E402
    verify_durable_candidate,
)
from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


def main() -> None:
    output = PROJECT_ROOT / "outputs/prospective_forward_hardening_v1/current"
    manifest = load_artifact_manifest(output / "artifact_manifest.json")
    assert manifest["stage_id"] == "prospective_forward_hardening_v1"
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    assert not validate_manifest_outputs(manifest, output)
    contracts = pd.read_csv(output / "contract_status.csv")
    assert contracts["status"].eq("pass").all()
    freeze = json.loads(
        (output / "forward_candidate_freeze.json").read_text(encoding="utf-8")
    )
    model, preprocessing = verify_durable_candidate(freeze)
    assert model.stat().st_size == 688235
    assert preprocessing.stat().st_size == 5639
    assert freeze["candidate_freeze_effective_date_asia_shanghai"] == (
        "2026-08-02"
    )
    assert freeze["rebind_only_no_retraining"] is True
    assert freeze["backup_verified"] is True
    assert freeze["forward_data_waiting"] is True
    assert freeze["production_model_selected"] is False
    assert freeze["live_trading_ready"] is False
    schema = json.loads(
        (output / "prediction_freeze_schema.json").read_text(encoding="utf-8")
    )
    assert schema["contracts"]["prediction_created_before_label_start_cutoff"]
    assert schema["contracts"]["prediction_commit_before_label_start_cutoff"]
    readiness = pd.read_csv(output / "readiness_summary.csv").iloc[0]
    assert bool(readiness["prospective_time_boundary_hardened"])
    assert bool(readiness["forward_candidate_durable_storage_ready"])
    assert bool(readiness["forward_data_waiting"])
    assert not bool(readiness["production_model_selected"])
    print("prospective forward hardening v1 validation passed")


if __name__ == "__main__":
    main()
