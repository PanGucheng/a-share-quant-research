from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research_validation.lineage import (  # noqa: E402
    load_artifact_manifest,
    validate_manifest_outputs,
    validate_transitive_lineage,
)


def resolve(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def main() -> int:
    config = yaml.safe_load(
        resolve("configs/execution_unit_semantics_correction_v1_2.yaml").read_text(
            encoding="utf-8"
        )
    ) or {}
    governance_dir = resolve(config["governance_output"])
    manifest_path = governance_dir / "artifact_manifest.json"
    manifest = load_artifact_manifest(manifest_path)
    assert manifest["artifact_status"] == "pass"
    assert manifest["lineage_status"] == "complete"
    assert not bool(manifest["code_dirty"])
    assert not validate_manifest_outputs(manifest, governance_dir)

    contracts = pd.read_csv(governance_dir / "contract_status.csv")
    assert contracts.loc[contracts["severity"].eq("critical"), "status"].eq("pass").all()
    readiness = pd.read_csv(governance_dir / "readiness_summary.csv").iloc[0]
    for field in [
        "data_source_audit_v2_ready",
        "execution_unit_semantics_ready",
        "market_cache_volume_unit_ready",
        "market_cache_amount_unit_ready",
        "execution_semantics_accuracy_ready",
        "market_cache_v3_ready",
        "matrix_v4_artifact_unchanged",
        "selection_artifact_unchanged",
        "score_business_payload_unchanged",
        "model_entry_hard_stop_active",
    ]:
        assert bool(readiness[field]), field
    for field in [
        "market_cache_v2_ready",
        "authoritative_oos_execution_ready",
        "core_model_ready",
        "pr5_model_training_ready",
        "model_training_started",
        "unbiased_final_estimate",
        "historical_oos_comparison_complete",
        "production_model_selected",
    ]:
        assert not bool(readiness[field]), field
    assert int(readiness["execution_comparison_scenario_count"]) == 6
    assert int(readiness["unknown_semantic_difference_count"]) == 0

    instrument = pd.read_csv(governance_dir / "instrument_unit_attribution.csv")
    focus = instrument.loc[instrument["instrument"].eq("SZ302132")]
    assert len(focus) == 1
    assert bool(focus.iloc[0]["is_focus_instrument"])

    central = pd.read_csv(resolve(config["central_readiness"])).iloc[0]
    assert (
        central["accuracy_correction_status"]
        == "execution_unit_semantics_corrected_authoritative_state_blocked"
    )
    assert bool(central["execution_unit_semantics_ready"])
    assert bool(central["market_cache_v3_ready"])
    assert not bool(central["market_cache_v2_ready"])
    assert bool(central["model_entry_hard_stop_active"])
    assert not bool(central["core_model_ready"])
    assert not bool(central["pr5_model_training_ready"])
    assert not bool(central["model_training_started"])

    semantics = yaml.safe_load(resolve(config["lineage_semantics"]).read_text(encoding="utf-8"))
    _, _, issues = validate_transitive_lineage(
        outputs_root=PROJECT_ROOT / "outputs",
        start_manifest_paths=[manifest_path],
        semantics=semantics,
    )
    assert not issues, pd.DataFrame([issue.__dict__ for issue in issues]).to_string(index=False)
    print(
        "Execution Unit Semantics V1.2 passes; authoritative state and all model entry remain blocked."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
