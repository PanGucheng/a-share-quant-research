from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
)


def _validate_stage(path: Path, stage_id: str) -> dict:
    manifest = load_artifact_manifest(path / "artifact_manifest.json")
    assert manifest["stage_id"] == stage_id
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    assert not validate_manifest_outputs(manifest, path)
    contracts = pd.read_csv(path / "contract_status.csv")
    assert contracts["status"].eq("pass").all()
    return manifest


def main() -> None:
    protocol = PROJECT_ROOT / "outputs/prospective_forward_protocol_v1/current"
    canary = PROJECT_ROOT / "outputs/prospective_forward_candidate_v1/canary"
    candidate = PROJECT_ROOT / "outputs/prospective_forward_candidate_v1/current"
    _validate_stage(protocol, "prospective_forward_protocol_v1")
    _validate_stage(canary, "prospective_forward_candidate_canary_v1")
    _validate_stage(candidate, "prospective_forward_candidate_v1")

    quarantine = pd.read_csv(protocol / "quarantined_date_inventory.csv")
    assert len(quarantine) == 79
    assert not quarantine["prospective_evidence_eligible"].any()
    canary_resource = pd.read_csv(canary / "resource_summary.csv").iloc[0]
    assert int(canary_resource["quarantine_label_read_count"]) == 0
    assert int(canary_resource["quarantine_prediction_row_count"]) == 40000

    receipt = pd.read_csv(candidate / "candidate_model_receipt.csv").iloc[0]
    assert int(receipt["factor_count"]) == 52
    assert int(receipt["fit_row_count"]) == 2538428
    assert int(receipt["training_date_count"]) == 1273
    freeze = json.loads(
        (candidate / "forward_candidate_freeze.json").read_text(
            encoding="utf-8"
        )
    )
    assert freeze["status"] == "frozen_waiting_for_new_data"
    assert freeze["forward_data_waiting"] is True
    assert freeze["production_model_selected"] is False
    assert freeze["live_trading_ready"] is False
    assert freeze["model_binary_sha256"] == receipt["model_binary_sha256"]

    readiness = pd.read_csv(candidate / "readiness_summary.csv").iloc[0]
    assert bool(readiness["forward_candidate_refit_complete"])
    assert bool(readiness["forward_candidate_freeze_ready"])
    assert bool(readiness["forward_data_waiting"])
    assert not bool(readiness["forward_prediction_confirmation_complete"])
    assert not bool(readiness["production_model_selected"])
    print("prospective forward candidate v1 validation passed")


if __name__ == "__main__":
    main()
